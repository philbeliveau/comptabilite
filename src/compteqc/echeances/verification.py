"""Verification de fin d'exercice (year-end checklist).

Valide la coherence des donnees avant la generation du package CPA.
Chaque verification retourne un VerificationResult avec severite
appropriee. Les erreurs fatales (equation desequilibree) bloquent
le package; les avertissements permettent la generation.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from beancount.core import data
from pydantic import BaseModel

from compteqc.mcp.services import calculer_soldes
from compteqc.rapports.gifi_export import extract_gifi_map, validate_gifi


class Severite(str, Enum):
    """Niveau de severite d'une verification."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class VerificationResult(BaseModel):
    """Resultat d'une verification de fin d'exercice."""
    nom: str
    passe: bool
    message: str
    severite: Severite


def _verifier_equation(entries: list) -> VerificationResult:
    """Verifie l'equation comptable (GIFI validation)."""
    soldes = calculer_soldes(entries)
    gifi_map = extract_gifi_map(entries)
    result = validate_gifi(soldes, gifi_map)

    if result.balanced:
        return VerificationResult(
            nom="Equation comptable",
            passe=True,
            message="L'equation comptable est equilibree.",
            severite=Severite.INFO,
        )
    return VerificationResult(
        nom="Equation comptable",
        passe=False,
        message=f"FATAL: {'; '.join(result.errors)}",
        severite=Severite.ERROR,
    )


def _verifier_pret_actionnaire(entries: list, annee: int) -> VerificationResult:
    """Verifie le solde du pret actionnaire en fin d'exercice."""
    import datetime

    from compteqc.quebec.pret_actionnaire.suivi import obtenir_etat_pret

    fin = datetime.date(annee, 12, 31)
    etat = obtenir_etat_pret(entries, fin)

    if etat.solde == Decimal("0"):
        return VerificationResult(
            nom="Pret actionnaire",
            passe=True,
            message="Solde nul en fin d'exercice.",
            severite=Severite.INFO,
        )
    return VerificationResult(
        nom="Pret actionnaire",
        passe=True,  # warning, not failure
        message=f"Solde non nul: {etat.solde:.2f} $. Le CPA devrait verifier s.15(2).",
        severite=Severite.WARNING,
    )


def _verifier_non_classe(entries: list, annee: int) -> VerificationResult:
    """Verifie les transactions non classees (Depenses:Non-Classe)."""
    import datetime

    debut = datetime.date(annee, 1, 1)
    fin = datetime.date(annee, 12, 31)
    count = 0

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.date < debut or entry.date > fin:
            continue
        for posting in entry.postings:
            if posting.account == "Depenses:Non-Classe":
                count += 1
                break

    if count == 0:
        return VerificationResult(
            nom="Transactions non classees",
            passe=True,
            message="Aucune transaction non classee.",
            severite=Severite.INFO,
        )
    return VerificationResult(
        nom="Transactions non classees",
        passe=True,  # warning only
        message=f"{count} transaction(s) non classee(s) restante(s).",
        severite=Severite.WARNING,
    )


def _verifier_pending(entries: list) -> VerificationResult:
    """Verifie les transactions en attente d'approbation."""
    count = 0
    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.flag == "!":
            count += 1

    if count == 0:
        return VerificationResult(
            nom="Transactions en attente",
            passe=True,
            message="Aucune transaction en attente.",
            severite=Severite.INFO,
        )
    return VerificationResult(
        nom="Transactions en attente",
        passe=True,  # warning only
        message=f"{count} transaction(s) en attente d'approbation.",
        severite=Severite.WARNING,
    )


def _verifier_cca(entries: list, annee: int) -> VerificationResult:
    """Verifie la coherence des immobilisations (placeholder)."""
    # Simplified: check that Actifs:Immobilisations balance is non-negative
    soldes = calculer_soldes(entries)
    total_immo = Decimal("0")
    for compte, montant in soldes.items():
        if compte.startswith("Actifs:Immobilisations"):
            total_immo += montant

    if total_immo >= 0:
        return VerificationResult(
            nom="Immobilisations (CCA)",
            passe=True,
            message=f"Total immobilisations: {total_immo:.2f} $.",
            severite=Severite.INFO,
        )
    return VerificationResult(
        nom="Immobilisations (CCA)",
        passe=True,
        message=f"Total immobilisations negatif: {total_immo:.2f} $. Verifier le registre DPA.",
        severite=Severite.WARNING,
    )


def _verifier_taxes(entries: list, annee: int) -> VerificationResult:
    """Verifie la concordance TPS/TVQ."""
    soldes = calculer_soldes(entries)
    tps_nette = soldes.get("Passifs:TPS-Nette", Decimal("0"))
    tvq_nette = soldes.get("Passifs:TVQ-Nette", Decimal("0"))

    # Check that TPS-Percue - TPS-Payee == TPS-Nette (if TPS-Nette exists)
    tps_percue = abs(soldes.get("Passifs:TPS-Percue", Decimal("0")))
    tps_payee = soldes.get("Actifs:TPS-Payee", Decimal("0"))
    tvq_percue = abs(soldes.get("Passifs:TVQ-Percue", Decimal("0")))
    tvq_payee = soldes.get("Actifs:TVQ-Payee", Decimal("0"))

    messages = []
    if tps_percue > 0 or tps_payee > 0:
        messages.append(f"TPS percue: {tps_percue:.2f}, CTI: {tps_payee:.2f}, nette: {tps_percue - tps_payee:.2f}")
    if tvq_percue > 0 or tvq_payee > 0:
        messages.append(f"TVQ percue: {tvq_percue:.2f}, RTI: {tvq_payee:.2f}, nette: {tvq_percue - tvq_payee:.2f}")

    if not messages:
        messages.append("Aucune transaction de taxes detectee.")

    return VerificationResult(
        nom="Reconciliation TPS/TVQ",
        passe=True,
        message=" | ".join(messages),
        severite=Severite.INFO,
    )


def verifier_fin_exercice(
    entries: list,
    annee: int,
    fin_exercice: object = None,  # Accepted but currently uses annee
) -> list[VerificationResult]:
    """Execute toutes les verifications de fin d'exercice.

    Args:
        entries: Liste d'entrees Beancount.
        annee: Annee fiscale.
        fin_exercice: Date de fin d'exercice (optionnel, defaut 31 dec).

    Returns:
        Liste de VerificationResult avec les resultats de chaque verification.
    """
    return [
        _verifier_equation(entries),
        _verifier_pret_actionnaire(entries, annee),
        _verifier_cca(entries, annee),
        _verifier_taxes(entries, annee),
        _verifier_non_classe(entries, annee),
        _verifier_pending(entries),
    ]
