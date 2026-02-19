"""Suivi du pret actionnaire (shareholder loan tracking).

Convention de signe:
- Positif = l'actionnaire doit a la corporation
- Negatif = la corporation doit a l'actionnaire

Chaque mouvement est suivi individuellement pour permettre le calcul
des dates limites s.15(2) par avance.
"""

import datetime
from dataclasses import dataclass, field
from decimal import Decimal

from beancount.core import data


@dataclass
class MouvementPret:
    """Un mouvement sur le pret actionnaire."""

    date: datetime.date
    montant: Decimal  # Positif = actionnaire emprunte, negatif = remboursement
    description: str
    type: str  # "avance", "remboursement", "salaire_offset", "depot_personnel"


@dataclass
class EtatPret:
    """Etat courant du pret actionnaire."""

    solde: Decimal  # Positif = actionnaire doit, negatif = corp doit
    mouvements: list[MouvementPret] = field(default_factory=list)
    avances_ouvertes: list[dict] = field(default_factory=list)
    # avances_ouvertes: [{date, montant_initial, solde_restant}]


COMPTE_PRET_ACTIONNAIRE = "Passifs:Pret-Actionnaire"


def calculer_etat_pret(
    mouvements: list[MouvementPret],
) -> EtatPret:
    """Calcule l'etat du pret actionnaire a partir des mouvements.

    Les avances sont suivies individuellement (FIFO) pour les deadlines s.15(2).
    Les remboursements sont appliques aux avances les plus anciennes d'abord.

    Args:
        mouvements: Liste de mouvements tries par date

    Returns:
        EtatPret avec solde, mouvements, et avances ouvertes
    """
    solde = Decimal("0.00")
    avances_ouvertes: list[dict] = []

    for mouvement in sorted(mouvements, key=lambda m: m.date):
        solde += mouvement.montant

        if mouvement.montant > 0:
            # Nouvelle avance - l'actionnaire emprunte
            avances_ouvertes.append({
                "date": mouvement.date,
                "montant_initial": mouvement.montant,
                "solde_restant": mouvement.montant,
            })
        elif mouvement.montant < 0:
            # Remboursement - appliquer FIFO aux avances ouvertes
            remboursement_restant = abs(mouvement.montant)
            for avance in avances_ouvertes:
                if remboursement_restant <= 0:
                    break
                if avance["solde_restant"] <= 0:
                    continue
                reduction = min(avance["solde_restant"], remboursement_restant)
                avance["solde_restant"] -= reduction
                remboursement_restant -= reduction

    # Filtrer les avances completement remboursees
    avances_actives = [a for a in avances_ouvertes if a["solde_restant"] > 0]

    return EtatPret(
        solde=solde,
        mouvements=mouvements,
        avances_ouvertes=avances_actives,
    )


def obtenir_etat_pret(
    entries: list,
    fin_exercice: datetime.date,
) -> EtatPret:
    """Derive l'etat du pret actionnaire depuis les entrees Beancount.

    Lit les transactions du grand-livre, filtre par annee fiscale et par compte
    Passifs:Pret-Actionnaire, puis delegue a calculer_etat_pret.

    Convention de signe Beancount:
    - Debit (positif) sur un compte de passif = augmentation du pret (avance)
    - Credit (negatif) sur un compte de passif = diminution du pret (remboursement)

    Args:
        entries: Liste d'entrees Beancount (de loader.load_file ou autre source).
        fin_exercice: Date de fin d'exercice fiscal (ex: 2026-12-31).

    Returns:
        EtatPret derive des postings filtres.
    """
    annee = fin_exercice.year
    mouvements: list[MouvementPret] = []

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.date.year != annee:
            continue

        for posting in entry.postings:
            if posting.account != COMPTE_PRET_ACTIONNAIRE:
                continue

            montant = posting.units.number
            type_mouvement = "avance" if montant > 0 else "remboursement"

            mouvements.append(
                MouvementPret(
                    date=entry.date,
                    montant=montant,
                    description=entry.narration or "",
                    type=type_mouvement,
                )
            )

    return calculer_etat_pret(mouvements)
