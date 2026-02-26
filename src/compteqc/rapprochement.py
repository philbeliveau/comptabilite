"""Rapprochement automatique -- matching bank transactions to AR/AP entries.

Compares imported bank transactions against open invoices (AR) and vendor bills (AP)
to suggest matches. Each suggestion includes a confidence score (0.0-1.0) based on
amount proximity and name similarity.
"""

from __future__ import annotations

from decimal import Decimal
from difflib import SequenceMatcher
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from compteqc.models.transaction import TransactionNormalisee


TOLERANCE_MONTANT = Decimal("0.02")


@runtime_checkable
class FactureOuverte(Protocol):
    """Protocol for any open invoice/bill that can be matched."""

    @property
    def total(self) -> Decimal: ...


class SuggestionRapprochement(BaseModel):
    """A match suggestion between a bank transaction and an AR/AP entry."""

    type_match: str  # "ar" or "ap"
    reference: str  # invoice/bill number
    nom: str  # client/vendor name
    montant_attendu: Decimal  # expected amount (solde or total)
    montant_transaction: Decimal  # actual transaction amount (absolute)
    confiance: float  # 0.0-1.0 confidence score
    raison: str  # human-readable explanation


def calculer_similarite(a: str, b: str) -> float:
    """Calcule la similarite entre deux chaines (0.0-1.0).

    Normalise en minuscules et supprime les espaces superflus avant comparaison.
    """
    a_norm = a.lower().strip()
    b_norm = b.lower().strip()
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def _calculer_score(
    montant_transaction: Decimal,
    montant_attendu: Decimal,
    nom_reference: str,
    beneficiaire: str,
    description: str,
) -> tuple[float, str]:
    """Calcule le score de confiance et la raison du match.

    Returns:
        Tuple (score, raison) ou score est 0.0-1.0.
    """
    raisons = []

    # Amount score: 0.7 if within tolerance, else 0.0
    ecart = abs(montant_transaction - montant_attendu)
    if ecart <= TOLERANCE_MONTANT:
        score_montant = 0.7
        if ecart == 0:
            raisons.append("Montant exact")
        else:
            raisons.append(f"Montant proche (ecart: {ecart}$)")
    else:
        return 0.0, ""

    # Name score: max similarity of (beneficiaire, description) vs nom_reference * 0.3
    sim_beneficiaire = calculer_similarite(beneficiaire, nom_reference)
    sim_description = calculer_similarite(description, nom_reference)
    meilleure_sim = max(sim_beneficiaire, sim_description)
    score_nom = meilleure_sim * 0.3

    if meilleure_sim > 0.6:
        raisons.append(f"Nom similaire ({meilleure_sim:.0%})")
    elif meilleure_sim > 0.3:
        raisons.append(f"Nom partiellement similaire ({meilleure_sim:.0%})")

    score_total = score_montant + score_nom
    raison = "; ".join(raisons) if raisons else "Match par montant"

    return score_total, raison


def _est_paye(statut: object) -> bool:
    """Verifie si un statut indique que la facture est payee.

    Supporte InvoiceStatus.PAID et BillStatus.PAID via comparaison string.
    """
    if statut is None:
        return False
    statut_str = str(statut).lower()
    return "paid" in statut_str and "partial" not in statut_str


def _obtenir_solde(entry: object) -> Decimal | None:
    """Obtient le solde restant d'une facture/bill.

    Utilise .solde si disponible, sinon .total. Retourne None si <= 0.
    """
    montant = getattr(entry, "solde", None)
    if montant is None:
        montant = entry.total  # type: ignore[union-attr]
    return montant if montant > 0 else None


def suggerer_rapprochement_ar(
    transaction: TransactionNormalisee,
    factures: list,
) -> list[SuggestionRapprochement]:
    """Suggere des rapprochements entre un depot et des factures AR ouvertes.

    Seules les transactions positives (depots) sont traitees.
    Les factures payees (statut PAID) sont exclues.

    Args:
        transaction: Transaction bancaire normalisee.
        factures: Liste de Facture (AR) ouvertes.

    Returns:
        Liste de suggestions triees par confiance decroissante.
    """
    if transaction.montant <= 0:
        return []

    suggestions: list[SuggestionRapprochement] = []

    for facture in factures:
        if _est_paye(getattr(facture, "statut", None)):
            continue

        montant_attendu = _obtenir_solde(facture)
        if montant_attendu is None:
            continue

        score, raison = _calculer_score(
            montant_transaction=transaction.montant,
            montant_attendu=montant_attendu,
            nom_reference=facture.nom_client,
            beneficiaire=transaction.beneficiaire,
            description=transaction.description,
        )

        if score > 0.5:
            suggestions.append(
                SuggestionRapprochement(
                    type_match="ar",
                    reference=facture.numero,
                    nom=facture.nom_client,
                    montant_attendu=montant_attendu,
                    montant_transaction=transaction.montant,
                    confiance=round(score, 4),
                    raison=raison,
                )
            )

    suggestions.sort(key=lambda s: s.confiance, reverse=True)
    return suggestions


def suggerer_rapprochement_ap(
    transaction: TransactionNormalisee,
    factures_fournisseurs: list,
) -> list[SuggestionRapprochement]:
    """Suggere des rapprochements entre un retrait et des factures fournisseurs AP.

    Seules les transactions negatives (retraits) sont traitees.
    Les factures payees (statut PAID) sont exclues.

    Args:
        transaction: Transaction bancaire normalisee.
        factures_fournisseurs: Liste d'objets avec .fournisseur, .total/.solde, .statut.

    Returns:
        Liste de suggestions triees par confiance decroissante.
    """
    if transaction.montant >= 0:
        return []

    montant_abs = abs(transaction.montant)
    suggestions: list[SuggestionRapprochement] = []

    for bill in factures_fournisseurs:
        if _est_paye(getattr(bill, "statut", None)):
            continue

        montant_attendu = _obtenir_solde(bill)
        if montant_attendu is None:
            continue

        # Get the identifier and vendor name
        reference = getattr(bill, "numero_interne", getattr(bill, "numero", ""))
        nom_fournisseur = getattr(bill, "fournisseur", "")

        score, raison = _calculer_score(
            montant_transaction=montant_abs,
            montant_attendu=montant_attendu,
            nom_reference=nom_fournisseur,
            beneficiaire=transaction.beneficiaire,
            description=transaction.description,
        )

        if score > 0.5:
            suggestions.append(
                SuggestionRapprochement(
                    type_match="ap",
                    reference=reference,
                    nom=nom_fournisseur,
                    montant_attendu=montant_attendu,
                    montant_transaction=montant_abs,
                    confiance=round(score, 4),
                    raison=raison,
                )
            )

    suggestions.sort(key=lambda s: s.confiance, reverse=True)
    return suggestions
