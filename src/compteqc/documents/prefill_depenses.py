"""Recommandations de pre-remplissage AP pour documents de depense.

Centralise les suggestions deterministes derivees d'un recu televerse:
- categorie de depense suggeree
- montant HT a pre-remplir
- taux ITC / ITR
- note de contexte pour allocations partielles

Le but est d'eviter que la logique fiscale d'appoint vive dans les templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from compteqc.documents.extraction import DonneesRecu

QUANTIZE_CENT = Decimal("0.01")
FOURNISSEURS_TELECOM = (
    "fizz",
    "bell",
    "videotron",
    "vidéotron",
    "rogers",
    "telus",
    "fido",
    "koodo",
    "virgin",
    "freedom",
)
MOTS_TELECOM = (
    "internet",
    "telecom",
    "télécom",
    "telephone",
    "téléphone",
    "phone",
    "mobile",
    "cell",
    "cellulaire",
)
COMPTE_DEPENSE_TELECOM = "Depenses:Bureau:Internet-Telecom"


@dataclass(frozen=True)
class PrefillAPDepense:
    """Suggestion de pre-remplissage AP pour un document de depense."""

    categorie_depense: str | None
    montant_ht: Decimal
    tps_applicable: bool
    tvq_applicable: bool
    taux_itc: Decimal
    taux_itr: Decimal
    note: str | None
    allocation_ratio: Decimal
    justification: str | None


def _q(valeur: Decimal) -> Decimal:
    return valeur.quantize(QUANTIZE_CENT, rounding=ROUND_HALF_UP)


def _texte_recherche(donnees: DonneesRecu) -> str:
    return " ".join(
        morceau.strip().lower()
        for morceau in (
            donnees.fournisseur or "",
            donnees.description or "",
        )
        if morceau and morceau.strip()
    )


def est_depense_telecom(donnees: DonneesRecu) -> bool:
    """Retourne True si le document ressemble a un service internet/mobile."""
    texte = _texte_recherche(donnees)
    if not texte:
        return False
    return any(mot in texte for mot in FOURNISSEURS_TELECOM + MOTS_TELECOM)


def suggerer_prefill_ap_depense(donnees: DonneesRecu) -> PrefillAPDepense:
    """Construit une suggestion AP coherente pour un recu fournisseur.

    Pour les services telecom, le prefill suggere la categorie mais ne
    reduit pas automatiquement le montant HT. Le ratio d'usage d'affaires
    doit rester une decision explicite de l'operateur.
    """
    if est_depense_telecom(donnees):
        note = (
            "Service telecom detecte. Confirmez manuellement le ratio "
            "d'usage d'affaires avant de creer la facture fournisseur."
        )
        justification = (
            "Service internet/mobile detecte; la categorie est suggeree "
            "sans reduction automatique du montant."
        )
        return PrefillAPDepense(
            categorie_depense=COMPTE_DEPENSE_TELECOM,
            montant_ht=_q(donnees.sous_total),
            tps_applicable=donnees.montant_tps is not None,
            tvq_applicable=donnees.montant_tvq is not None,
            taux_itc=Decimal("1.0"),
            taux_itr=Decimal("1.0"),
            note=note,
            allocation_ratio=Decimal("1.0"),
            justification=justification,
        )

    return PrefillAPDepense(
        categorie_depense=None,
        montant_ht=_q(donnees.sous_total),
        tps_applicable=donnees.montant_tps is not None,
        tvq_applicable=donnees.montant_tvq is not None,
        taux_itc=Decimal("1.0"),
        taux_itr=Decimal("1.0"),
        note=None,
        allocation_ratio=Decimal("1.0"),
        justification=None,
    )
