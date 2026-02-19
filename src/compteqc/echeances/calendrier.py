"""Calendrier de production fiscale et alertes.

Calcule les echeances de production (T2, CO-17, T4/RL-1, TPS/TVQ, remises
de paie, pret actionnaire s.15(2)) a partir de la date de fin d'exercice.

Toutes les dates sont derivees de la fin d'exercice -- aucune date n'est
codee en dur a Dec 31.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Literal

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Types & modeles
# ---------------------------------------------------------------------------


class TypeEcheance(str, Enum):
    """Types d'echeances fiscales suivies."""

    T4_RL1 = "T4_RL1"
    TPS_TVQ = "TPS_TVQ"
    T2 = "T2"
    CO17 = "CO17"
    PRET_ACTIONNAIRE = "PRET_ACTIONNAIRE"
    REMISE_PAIE = "REMISE_PAIE"


class Echeance(BaseModel):
    """Une echeance fiscale avec sa date limite et ses seuils d'alerte."""

    type: TypeEcheance
    date_limite: datetime.date
    description: str
    jours_alerte: list[int] = [90, 60, 30, 14, 7]
    completed: bool = False


class AlerteEcheance(BaseModel):
    """Alerte active pour une echeance approchante."""

    echeance: Echeance
    jours_restants: int
    urgence: Literal["critique", "urgent", "normal", "info"]


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------


def _ajuster_jour_ouvrable(d: datetime.date) -> datetime.date:
    """Pousse une date tombant un samedi ou dimanche au lundi suivant."""
    if d.weekday() == 5:  # samedi
        return d + datetime.timedelta(days=2)
    if d.weekday() == 6:  # dimanche
        return d + datetime.timedelta(days=1)
    return d


# ---------------------------------------------------------------------------
# Calcul des echeances
# ---------------------------------------------------------------------------


def calculer_echeances(fin_exercice: datetime.date) -> list[Echeance]:
    """Calcule toutes les echeances fiscales pour un exercice donne.

    Args:
        fin_exercice: Date de fin d'exercice fiscal (ex: 2025-12-31).

    Returns:
        Liste d'echeances triees par date_limite.
    """
    echeances: list[Echeance] = []
    annee = fin_exercice.year

    # 1. T4/RL-1: Feb 28 de l'annee suivante (annee civile)
    date_t4 = datetime.date(annee + 1, 2, 28)
    echeances.append(
        Echeance(
            type=TypeEcheance.T4_RL1,
            date_limite=_ajuster_jour_ouvrable(date_t4),
            description=f"T4/RL-1 pour l'annee civile {annee}",
            jours_alerte=[90, 60, 30, 14, 7],
        )
    )

    # 2. T2: 6 mois apres la fin d'exercice
    date_t2 = fin_exercice + relativedelta(months=6)
    echeances.append(
        Echeance(
            type=TypeEcheance.T2,
            date_limite=_ajuster_jour_ouvrable(date_t2),
            description=f"Declaration T2 (exercice terminant {fin_exercice})",
            jours_alerte=[90, 60, 30, 14, 7],
        )
    )

    # 3. CO-17: Meme date que T2
    echeances.append(
        Echeance(
            type=TypeEcheance.CO17,
            date_limite=_ajuster_jour_ouvrable(date_t2),
            description=f"Declaration CO-17 (exercice terminant {fin_exercice})",
            jours_alerte=[90, 60, 30, 14, 7],
        )
    )

    # 4. TPS/TVQ trimestrielle: fin de trimestre + 1 mois
    trimestres = [
        (datetime.date(annee, 3, 31), "Q1"),
        (datetime.date(annee, 6, 30), "Q2"),
        (datetime.date(annee, 9, 30), "Q3"),
        (datetime.date(annee, 12, 31), "Q4"),
    ]
    for fin_trimestre, label in trimestres:
        date_due = fin_trimestre + relativedelta(months=1)
        echeances.append(
            Echeance(
                type=TypeEcheance.TPS_TVQ,
                date_limite=_ajuster_jour_ouvrable(date_due),
                description=f"Remise TPS/TVQ {label} {annee}",
                jours_alerte=[30, 14, 7],
            )
        )

    # 5. Remises de paie: 15e du mois suivant, pour chaque mois
    for mois in range(1, 13):
        date_remise = datetime.date(
            annee if mois < 12 else annee + 1,
            mois + 1 if mois < 12 else 1,
            15,
        )
        echeances.append(
            Echeance(
                type=TypeEcheance.REMISE_PAIE,
                date_limite=_ajuster_jour_ouvrable(date_remise),
                description=f"Remise retenues sur la paie - {datetime.date(annee, mois, 1):%B %Y}",
                jours_alerte=[14, 7, 3],
            )
        )

    return sorted(echeances, key=lambda e: e.date_limite)


# ---------------------------------------------------------------------------
# Integration pret actionnaire
# ---------------------------------------------------------------------------


def integrer_echeances_pret(
    echeances: list[Echeance],
    etat_pret: object,
) -> list[Echeance]:
    """Ajoute les echeances s.15(2) du pret actionnaire au calendrier.

    Args:
        echeances: Echeances existantes.
        etat_pret: EtatPret de compteqc.quebec.pret_actionnaire.suivi.
            Doit avoir un attribut `avances_ouvertes` (list[dict]).

    Returns:
        Liste fusionnee triee par date_limite.
    """
    resultat = list(echeances)

    avances = getattr(etat_pret, "avances_ouvertes", [])
    for avance in avances:
        date_avance = avance.get("date")
        if date_avance is None:
            continue

        # s.15(2): inclusion au revenu si non rembourse a la fin de l'exercice
        # suivant celui ou le pret a ete consenti.
        # Deadline = fin de l'exercice + 1 an apres la date de l'avance.
        # Simplification: fin de l'annee civile suivant l'annee de l'avance.
        annee_avance = date_avance.year
        date_limite = datetime.date(annee_avance + 1, 12, 31)

        resultat.append(
            Echeance(
                type=TypeEcheance.PRET_ACTIONNAIRE,
                date_limite=date_limite,
                description=(
                    f"Remboursement pret actionnaire s.15(2) - "
                    f"avance du {date_avance} ({avance.get('solde_restant', '?')} $)"
                ),
                jours_alerte=[90, 60, 30, 14, 7],
            )
        )

    return sorted(resultat, key=lambda e: e.date_limite)


# ---------------------------------------------------------------------------
# Alertes
# ---------------------------------------------------------------------------


def obtenir_alertes(
    echeances: list[Echeance],
    aujourd_hui: datetime.date | None = None,
) -> list[AlerteEcheance]:
    """Retourne les alertes actives pour les echeances dans une fenetre d'alerte.

    Args:
        echeances: Liste d'echeances a verifier.
        aujourd_hui: Date de reference (defaut: aujourd'hui).

    Returns:
        Alertes actives triees par jours_restants (plus urgent d'abord).
    """
    if aujourd_hui is None:
        aujourd_hui = datetime.date.today()

    alertes: list[AlerteEcheance] = []

    for ech in echeances:
        if ech.completed:
            continue

        jours = (ech.date_limite - aujourd_hui).days
        if jours < 0:
            continue  # Deja passe

        # Verifier si on est dans au moins une fenetre d'alerte
        max_alerte = max(ech.jours_alerte) if ech.jours_alerte else 0
        if jours > max_alerte:
            continue

        # Determiner l'urgence
        if jours <= 7:
            urgence: Literal["critique", "urgent", "normal", "info"] = "critique"
        elif jours <= 14:
            urgence = "urgent"
        elif jours <= 30:
            urgence = "normal"
        else:
            urgence = "info"

        alertes.append(
            AlerteEcheance(
                echeance=ech,
                jours_restants=jours,
                urgence=urgence,
            )
        )

    return sorted(alertes, key=lambda a: a.jours_restants)


# ---------------------------------------------------------------------------
# Formatage CLI
# ---------------------------------------------------------------------------


def formater_rappels_cli(
    alertes: list[AlerteEcheance],
) -> str | None:
    """Formate les alertes actives dans les 30 prochains jours pour le CLI.

    Utilise le markup Rich pour la coloration.

    Args:
        alertes: Liste d'alertes (typiquement de obtenir_alertes()).

    Returns:
        Chaine formatee Rich ou None si aucune alerte dans les 30 jours.
    """
    within_30 = [a for a in alertes if a.jours_restants <= 30]
    if not within_30:
        return None

    couleur_map = {
        "critique": "red",
        "urgent": "yellow",
        "normal": "blue",
    }

    lignes: list[str] = []
    for alerte in within_30:
        couleur = couleur_map.get(alerte.urgence, "blue")
        icone = "[!]" if alerte.urgence in ("critique", "urgent") else "[i]"
        lignes.append(
            f"[{couleur}]{icone} Rappel: {alerte.echeance.description} "
            f"dans {alerte.jours_restants} jours ({alerte.echeance.date_limite})[/{couleur}]"
        )

    return "\n".join(lignes)
