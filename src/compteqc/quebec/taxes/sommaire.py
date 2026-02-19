"""Sommaires de periode de declaration TPS/TVQ et verification de concordance.

Genere des sommaires par periode de declaration (annuel ou trimestriel)
montrant TPS/TVQ percues, payees, et nettes. Verifie aussi la concordance
entre les ecritures TPS et TVQ pour chaque transaction.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal

from beancount.core import data

# Comptes de taxes dans le plan comptable
COMPTE_TPS_PERCUE = "Passifs:TPS-Percue"
COMPTE_TVQ_PERCUE = "Passifs:TVQ-Percue"
COMPTE_TPS_PAYEE = "Actifs:TPS-Payee"
COMPTE_TVQ_PAYEE = "Actifs:TVQ-Payee"

# Tous les comptes lies aux taxes (pour la concordance)
COMPTES_TPS = {COMPTE_TPS_PERCUE, COMPTE_TPS_PAYEE}
COMPTES_TVQ = {COMPTE_TVQ_PERCUE, COMPTE_TVQ_PAYEE}
COMPTES_TAXES = COMPTES_TPS | COMPTES_TVQ


@dataclass
class SommairePeriode:
    """Sommaire TPS/TVQ pour une periode de declaration."""

    debut: datetime.date
    fin: datetime.date
    tps_percue: Decimal  # TPS percue sur revenus (valeur absolue)
    tvq_percue: Decimal  # TVQ percue sur revenus (valeur absolue)
    tps_payee: Decimal  # TPS payee sur depenses (CTI)
    tvq_payee: Decimal  # TVQ payee sur depenses (RTI)
    tps_nette: Decimal  # tps_percue - tps_payee (positif = du a l'ARC)
    tvq_nette: Decimal  # tvq_percue - tvq_payee (positif = du a RQ)
    nb_transactions: int  # Nombre de transactions dans la periode


def _extraire_montant_posting(posting: data.Posting) -> Decimal:
    """Extrait le montant d'un posting comme Decimal."""
    if posting.units is None:
        return Decimal("0")
    return Decimal(str(posting.units.number))


def generer_sommaire_periode(
    entries: list,
    debut: datetime.date,
    fin: datetime.date,
) -> SommairePeriode:
    """Genere un sommaire TPS/TVQ pour une periode de declaration.

    Somme les ecritures aux comptes de taxes (percues et payees) pour
    toutes les transactions dans la plage de dates.

    Note sur les signes:
    - Passifs:TPS-Percue / TVQ-Percue: credits (negatifs en beancount).
      Le sommaire montre la valeur absolue.
    - Actifs:TPS-Payee / TVQ-Payee: debits (positifs en beancount).
    - Net = percue - payee. Positif = montant du au gouvernement.

    Args:
        entries: Liste d'entrees Beancount (toutes entrees, pas seulement transactions).
        debut: Date de debut de la periode (inclusive).
        fin: Date de fin de la periode (inclusive).

    Returns:
        SommairePeriode avec les totaux pour la periode.
    """
    tps_percue = Decimal("0")
    tvq_percue = Decimal("0")
    tps_payee = Decimal("0")
    tvq_payee = Decimal("0")
    nb_transactions = 0

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.date < debut or entry.date > fin:
            continue

        a_des_taxes = False
        for posting in entry.postings:
            montant = _extraire_montant_posting(posting)
            if posting.account == COMPTE_TPS_PERCUE:
                # Credit (negatif) -> valeur absolue pour le sommaire
                tps_percue += abs(montant)
                a_des_taxes = True
            elif posting.account == COMPTE_TVQ_PERCUE:
                tvq_percue += abs(montant)
                a_des_taxes = True
            elif posting.account == COMPTE_TPS_PAYEE:
                tps_payee += montant
                a_des_taxes = True
            elif posting.account == COMPTE_TVQ_PAYEE:
                tvq_payee += montant
                a_des_taxes = True

        if a_des_taxes:
            nb_transactions += 1

    tps_nette = tps_percue - tps_payee
    tvq_nette = tvq_percue - tvq_payee

    return SommairePeriode(
        debut=debut,
        fin=fin,
        tps_percue=tps_percue,
        tvq_percue=tvq_percue,
        tps_payee=tps_payee,
        tvq_payee=tvq_payee,
        tps_nette=tps_nette,
        tvq_nette=tvq_nette,
        nb_transactions=nb_transactions,
    )


def generer_sommaires_annuels(
    entries: list,
    annee: int,
    frequence: str = "annuel",
) -> list[SommairePeriode]:
    """Genere les sommaires pour toutes les periodes d'une annee.

    Args:
        entries: Liste d'entrees Beancount.
        annee: Annee fiscale.
        frequence: 'annuel' (une periode) ou 'trimestriel' (quatre periodes).

    Returns:
        Liste de SommairePeriode pour chaque periode de l'annee.
    """
    if frequence == "trimestriel":
        periodes = [
            (datetime.date(annee, 1, 1), datetime.date(annee, 3, 31)),
            (datetime.date(annee, 4, 1), datetime.date(annee, 6, 30)),
            (datetime.date(annee, 7, 1), datetime.date(annee, 9, 30)),
            (datetime.date(annee, 10, 1), datetime.date(annee, 12, 31)),
        ]
    else:
        periodes = [
            (datetime.date(annee, 1, 1), datetime.date(annee, 12, 31)),
        ]

    return [generer_sommaire_periode(entries, d, f) for d, f in periodes]


def verifier_concordance_tps_tvq(
    entries: list,
    annee: int,
) -> list[dict]:
    """Verifie la concordance entre TPS et TVQ pour chaque transaction.

    Chaque transaction qui a une ecriture TPS doit aussi avoir une ecriture TVQ
    (et vice versa), sauf pour les transactions exemptes ou a taux zero
    (qui n'ont aucune ecriture de taxe).

    Les transactions avec TPS seulement (fournisseurs hors Quebec) sont des
    divergences legitimement attendues mais quand meme signalees pour revue.

    Args:
        entries: Liste d'entrees Beancount.
        annee: Annee a verifier.

    Returns:
        Liste de divergences: [{'date', 'narration', 'has_tps', 'has_tvq', 'issue'}]
    """
    debut = datetime.date(annee, 1, 1)
    fin = datetime.date(annee, 12, 31)
    divergences: list[dict] = []

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.date < debut or entry.date > fin:
            continue

        comptes_dans_txn = {p.account for p in entry.postings}
        has_tps = bool(comptes_dans_txn & COMPTES_TPS)
        has_tvq = bool(comptes_dans_txn & COMPTES_TVQ)

        if has_tps and not has_tvq:
            divergences.append(
                {
                    "date": entry.date,
                    "narration": entry.narration,
                    "has_tps": True,
                    "has_tvq": False,
                    "issue": "TPS sans TVQ correspondante",
                }
            )
        elif has_tvq and not has_tps:
            divergences.append(
                {
                    "date": entry.date,
                    "narration": entry.narration,
                    "has_tps": False,
                    "has_tvq": True,
                    "issue": "TVQ sans TPS correspondante",
                }
            )

    return divergences
