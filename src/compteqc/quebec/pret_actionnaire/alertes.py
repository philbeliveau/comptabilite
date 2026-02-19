"""Calcul des dates limites s.15(2) et alertes graduees.

Section 15(2) de la Loi de l'impot sur le revenu:
Un pret d'une societe a un actionnaire doit etre rembourse avant la fin
de l'exercice fiscal suivant celui ou le pret a ete consenti, sinon le
montant est inclus dans le revenu de l'actionnaire.

IMPORTANT: La date d'inclusion est relative a la fin d'exercice fiscal,
PAS a la date du pret. Pour un exercice se terminant le 31 decembre:
tout pret fait en 2026 a une date d'inclusion au 31 decembre 2027.

Alertes graduees:
- 9 mois avant l'inclusion (alerte precoce)
- 11 mois avant l'inclusion (alerte de planification)
- 30 jours avant l'inclusion (alerte urgente)
"""

import datetime
from dataclasses import dataclass
from decimal import Decimal

from dateutil.relativedelta import relativedelta


@dataclass
class AlertePret:
    """Alerte pour une avance au pret actionnaire."""

    date_avance: datetime.date
    montant: Decimal
    date_inclusion: datetime.date  # Fin exercice + 1 an
    alerte_9_mois: datetime.date  # Inclusion - 9 mois (alerte precoce)
    alerte_11_mois: datetime.date  # Inclusion - 11 mois (planification)
    alerte_30_jours: datetime.date  # Inclusion - 30 jours (urgente)
    solde_restant: Decimal  # Solde encore impaye de cette avance


def calculer_dates_alerte(
    date_avance: datetime.date,
    montant: Decimal,
    fin_exercice: datetime.date,
    solde_restant: Decimal | None = None,
) -> AlertePret:
    """Calcule les dates d'alerte s.15(2) pour une avance.

    La date d'inclusion = fin de l'exercice fiscal contenant l'avance + 1 an.
    Pour un exercice au 31 decembre: avance en 2026 -> inclusion 31 dec 2027.

    Args:
        date_avance: Date a laquelle l'avance a ete faite
        montant: Montant de l'avance
        fin_exercice: Date de fin d'exercice (ex: 31 decembre)
        solde_restant: Solde restant de l'avance (default = montant complet)

    Returns:
        AlertePret avec toutes les dates d'alerte
    """
    if solde_restant is None:
        solde_restant = montant

    # Trouver la fin d'exercice qui contient la date de l'avance
    # Si l'avance est apres la fin d'exercice dans l'annee, c'est l'exercice suivant
    fin_exercice_annee = datetime.date(
        date_avance.year, fin_exercice.month, fin_exercice.day
    )
    if date_avance > fin_exercice_annee:
        fin_exercice_annee = datetime.date(
            date_avance.year + 1, fin_exercice.month, fin_exercice.day
        )

    # Date d'inclusion = fin exercice + 1 an
    date_inclusion = fin_exercice_annee + relativedelta(years=1)

    # Alertes graduees
    alerte_9_mois = date_inclusion - relativedelta(months=9)
    alerte_11_mois = date_inclusion - relativedelta(months=11)
    alerte_30_jours = date_inclusion - relativedelta(days=30)

    return AlertePret(
        date_avance=date_avance,
        montant=montant,
        date_inclusion=date_inclusion,
        alerte_9_mois=alerte_9_mois,
        alerte_11_mois=alerte_11_mois,
        alerte_30_jours=alerte_30_jours,
        solde_restant=solde_restant,
    )


def obtenir_alertes_actives(
    avances_ouvertes: list[dict],
    fin_exercice: datetime.date,
    date_courante: datetime.date,
) -> list[dict]:
    """Retourne les alertes actives (dates d'alerte depassees, solde > 0).

    Args:
        avances_ouvertes: [{date, montant_initial, solde_restant}]
        fin_exercice: Date de fin d'exercice (ex: 31 decembre)
        date_courante: Date actuelle pour evaluer les alertes

    Returns:
        Liste de dicts: {avance_date, montant, deadline, urgence, solde_restant}
        urgence: '11_mois' | '9_mois' | '30_jours' | 'depasse'
    """
    alertes = []

    for avance in avances_ouvertes:
        if avance["solde_restant"] <= 0:
            continue

        alerte = calculer_dates_alerte(
            date_avance=avance["date"],
            montant=avance["montant_initial"],
            fin_exercice=fin_exercice,
            solde_restant=avance["solde_restant"],
        )

        # Determiner le niveau d'urgence le plus eleve atteint
        urgence = None
        if date_courante > alerte.date_inclusion:
            urgence = "depasse"
        elif date_courante >= alerte.alerte_30_jours:
            urgence = "30_jours"
        elif date_courante >= alerte.alerte_9_mois:
            urgence = "9_mois"
        elif date_courante >= alerte.alerte_11_mois:
            urgence = "11_mois"

        if urgence is not None:
            alertes.append({
                "avance_date": avance["date"],
                "montant": avance["montant_initial"],
                "deadline": alerte.date_inclusion,
                "urgence": urgence,
                "solde_restant": avance["solde_restant"],
            })

    return alertes
