"""Suivi des remises de paie (retenues et cotisations employeur).

Lit les postings Beancount pour calculer les montants dus et remis
par mois, afin de reperer les periodes avec un solde impaye.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import BaseModel

from beancount.core import data

from compteqc.echeances.calendrier import (
    Echeance,
    TypeEcheance,
    _ajuster_jour_ouvrable,
)


# ---------------------------------------------------------------------------
# Modele
# ---------------------------------------------------------------------------


class RemisePaie(BaseModel):
    """Etat des remises de paie pour un mois donne."""

    mois: int
    annee: int
    retenues_dues: Decimal = Decimal("0.00")
    cotisations_dues: Decimal = Decimal("0.00")
    total_du: Decimal = Decimal("0.00")
    total_remis: Decimal = Decimal("0.00")
    solde: Decimal = Decimal("0.00")


# ---------------------------------------------------------------------------
# Comptes cibles
# ---------------------------------------------------------------------------

PREFIXES_RETENUES = "Passifs:Retenues"
PREFIXES_COTISATIONS = "Passifs:Cotisations-Employeur"
PREFIXES_BANQUE = "Actifs:Banque"


# ---------------------------------------------------------------------------
# Fonctions
# ---------------------------------------------------------------------------


def suivi_remises(entries: list, annee: int) -> list[RemisePaie]:
    """Calcule le suivi des remises de paie mois par mois.

    Pour chaque mois, on regarde:
    - Les postings credit sur Passifs:Retenues:* et Passifs:Cotisations-Employeur:*
      (montants dus -- en Beancount, un credit sur un passif est negatif).
    - Les transactions qui debitent ces comptes (remise) et creditent la banque.

    Convention: un posting credit (negatif) sur Passifs:Retenues augmente
    le montant du (on doit plus au fisc). Un posting debit (positif)
    sur Passifs:Retenues diminue le passif (on a remis).

    Args:
        entries: Liste d'entrees Beancount.
        annee: Annee a analyser.

    Returns:
        Liste de 12 RemisePaie (janvier a decembre).
    """
    # Accumulateurs par mois (1-12)
    retenues_dues: dict[int, Decimal] = {m: Decimal("0.00") for m in range(1, 13)}
    cotisations_dues: dict[int, Decimal] = {m: Decimal("0.00") for m in range(1, 13)}
    retenues_remises: dict[int, Decimal] = {m: Decimal("0.00") for m in range(1, 13)}
    cotisations_remises: dict[int, Decimal] = {m: Decimal("0.00") for m in range(1, 13)}

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.date.year != annee:
            continue

        mois = entry.date.month

        # Identifier si c'est une remise (paiement au fisc):
        # une remise debite Passifs:Retenues (positif) et credite Actifs:Banque
        comptes_debites = set()
        comptes_credites = set()
        for posting in entry.postings:
            if posting.units.number > 0:
                comptes_debites.add(posting.account)
            elif posting.units.number < 0:
                comptes_credites.add(posting.account)

        est_remise = any(
            c.startswith(PREFIXES_BANQUE) for c in comptes_credites
        ) and any(
            c.startswith(PREFIXES_RETENUES) or c.startswith(PREFIXES_COTISATIONS)
            for c in comptes_debites
        )

        for posting in entry.postings:
            montant = posting.units.number

            if posting.account.startswith(PREFIXES_RETENUES):
                if est_remise and montant > 0:
                    retenues_remises[mois] += montant
                elif montant < 0:
                    retenues_dues[mois] += abs(montant)

            elif posting.account.startswith(PREFIXES_COTISATIONS):
                if est_remise and montant > 0:
                    cotisations_remises[mois] += montant
                elif montant < 0:
                    cotisations_dues[mois] += abs(montant)

    # Construire les resultats
    resultats: list[RemisePaie] = []
    for m in range(1, 13):
        total_du = retenues_dues[m] + cotisations_dues[m]
        total_remis = retenues_remises[m] + cotisations_remises[m]
        resultats.append(
            RemisePaie(
                mois=m,
                annee=annee,
                retenues_dues=retenues_dues[m],
                cotisations_dues=cotisations_dues[m],
                total_du=total_du,
                total_remis=total_remis,
                solde=total_du - total_remis,
            )
        )

    return resultats


def prochaine_remise(
    remises: list[RemisePaie],
    aujourd_hui: datetime.date | None = None,
) -> Echeance | None:
    """Trouve la prochaine echeance de remise de paie avec solde impaye.

    Args:
        remises: Liste de RemisePaie (typiquement 12 mois).
        aujourd_hui: Date de reference (defaut: aujourd'hui).

    Returns:
        Echeance pour la prochaine remise due, ou None si tout est paye.
    """
    if aujourd_hui is None:
        aujourd_hui = datetime.date.today()

    for r in remises:
        if r.solde <= 0:
            continue

        # Deadline: 15e du mois suivant
        if r.mois == 12:
            date_remise = datetime.date(r.annee + 1, 1, 15)
        else:
            date_remise = datetime.date(r.annee, r.mois + 1, 15)

        date_remise = _ajuster_jour_ouvrable(date_remise)

        if date_remise >= aujourd_hui:
            return Echeance(
                type=TypeEcheance.REMISE_PAIE,
                date_limite=date_remise,
                description=(
                    f"Remise retenues sur la paie - "
                    f"{datetime.date(r.annee, r.mois, 1):%B %Y} "
                    f"(solde: {r.solde} $)"
                ),
                jours_alerte=[14, 7, 3],
            )

    return None
