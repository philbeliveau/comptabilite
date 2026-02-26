"""Calcul du vieillissement (aging) des comptes clients et fournisseurs.

Module pur (sans I/O) qui calcule les tranches d'age pour les factures AR et AP,
et produit un resume de position combine AR/AP.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from compteqc.factures.modeles import Facture
    from compteqc.fournisseurs.modeles import FactureFournisseur

BUCKETS = ["0-30", "31-60", "61-90", "91+"]


@dataclass
class LigneVieillissement:
    """Une entree dans un rapport de vieillissement."""

    identifiant: str  # Numero de facture
    nom: str  # Nom du client ou fournisseur
    date_document: datetime.date
    date_echeance: datetime.date
    total: Decimal
    paye: Decimal
    solde: Decimal
    jours_echus: int  # Jours en retard (negatif = pas encore du)
    tranche: str  # Bucket: "0-30", "31-60", "61-90", "91+"


@dataclass
class ResumeVieillissement:
    """Resume d'un rapport de vieillissement pour un cote (AR ou AP)."""

    lignes: list[LigneVieillissement] = field(default_factory=list)
    totaux_par_tranche: dict[str, Decimal] = field(default_factory=dict)
    nombre_par_tranche: dict[str, int] = field(default_factory=dict)
    total_impaye: Decimal = Decimal("0")
    nombre_total: int = 0

    def __post_init__(self) -> None:
        # Initialize all buckets to zero if not already set
        for bucket in BUCKETS:
            self.totaux_par_tranche.setdefault(bucket, Decimal("0"))
            self.nombre_par_tranche.setdefault(bucket, 0)


@dataclass
class PositionAPAR:
    """Position combinee AP/AR."""

    ar: ResumeVieillissement
    ap: ResumeVieillissement
    position_nette: Decimal  # AR total - AP total (positif = creance nette)
    encaissements_30j: Decimal  # Montants AR dans la tranche 0-30
    paiements_30j: Decimal  # Montants AP dans la tranche 0-30
    flux_net_30j: Decimal  # encaissements - paiements


def calculer_age_jours(
    date_echeance: datetime.date, date_reference: datetime.date | None = None
) -> int:
    """Calcule le nombre de jours echus depuis la date d'echeance.

    Retourne (date_reference - date_echeance).days.
    Positif = en retard, negatif = pas encore du, 0 = du aujourd'hui.
    """
    if date_reference is None:
        date_reference = datetime.date.today()
    return (date_reference - date_echeance).days


def classifier_age(jours: int) -> str:
    """Classe un nombre de jours echus dans une tranche de vieillissement.

    0-30 jours, 31-60, 61-90, 91+.
    Les jours negatifs (pas encore dus) tombent dans la tranche 0-30.
    """
    if jours <= 30:
        return "0-30"
    elif jours <= 60:
        return "31-60"
    elif jours <= 90:
        return "61-90"
    else:
        return "91+"


def calculer_vieillissement_ar(
    factures: list[Facture],
    date_reference: datetime.date | None = None,
) -> ResumeVieillissement:
    """Calcule le vieillissement des comptes clients (AR).

    Filtre les factures impayees (solde > 0), calcule l'age et classe en tranches.
    """
    if date_reference is None:
        date_reference = datetime.date.today()

    resume = ResumeVieillissement()

    for f in factures:
        if f.solde <= 0:
            continue

        jours = calculer_age_jours(f.date_echeance, date_reference)
        tranche = classifier_age(jours)

        ligne = LigneVieillissement(
            identifiant=f.numero,
            nom=f.nom_client,
            date_document=f.date,
            date_echeance=f.date_echeance,
            total=f.total,
            paye=f.montant_paye,
            solde=f.solde,
            jours_echus=jours,
            tranche=tranche,
        )
        resume.lignes.append(ligne)
        resume.totaux_par_tranche[tranche] += f.solde
        resume.nombre_par_tranche[tranche] += 1
        resume.total_impaye += f.solde
        resume.nombre_total += 1

    return resume


def calculer_vieillissement_ap(
    factures: list[FactureFournisseur],
    date_reference: datetime.date | None = None,
) -> ResumeVieillissement:
    """Calcule le vieillissement des comptes fournisseurs (AP).

    Filtre les factures impayees (solde > 0), calcule l'age et classe en tranches.
    """
    if date_reference is None:
        date_reference = datetime.date.today()

    resume = ResumeVieillissement()

    for f in factures:
        if f.solde <= 0:
            continue

        jours = calculer_age_jours(f.date_echeance, date_reference)
        tranche = classifier_age(jours)

        ligne = LigneVieillissement(
            identifiant=f.numero_interne,
            nom=f.fournisseur,
            date_document=f.date_facture,
            date_echeance=f.date_echeance,
            total=f.total,
            paye=f.montant_paye,
            solde=f.solde,
            jours_echus=jours,
            tranche=tranche,
        )
        resume.lignes.append(ligne)
        resume.totaux_par_tranche[tranche] += f.solde
        resume.nombre_par_tranche[tranche] += 1
        resume.total_impaye += f.solde
        resume.nombre_total += 1

    return resume


def rapport_position_apar(
    ar: ResumeVieillissement, ap: ResumeVieillissement
) -> PositionAPAR:
    """Combine les rapports AR et AP en une position nette.

    position_nette = AR total impaye - AP total impaye (positif = creance nette)
    flux_net_30j = encaissements prevus 30j - paiements prevus 30j
    """
    encaissements_30j = ar.totaux_par_tranche["0-30"]
    paiements_30j = ap.totaux_par_tranche["0-30"]

    return PositionAPAR(
        ar=ar,
        ap=ap,
        position_nette=ar.total_impaye - ap.total_impaye,
        encaissements_30j=encaissements_30j,
        paiements_30j=paiements_30j,
        flux_net_30j=encaissements_30j - paiements_30j,
    )
