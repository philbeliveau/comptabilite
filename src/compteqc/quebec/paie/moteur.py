"""Moteur de paie: orchestration de tous les calculs pour une periode de paie.

Combine les cotisations (cotisations.py), les impots (impot_federal.py,
impot_quebec.py) et le suivi YTD (ytd.py) pour produire un ResultatPaie complet.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from compteqc.quebec.paie.cotisations import (
    calculer_ae_employe,
    calculer_ae_employeur,
    calculer_cnesst,
    calculer_fss,
    calculer_normes_travail,
    calculer_qpp_base_employe,
    calculer_qpp_supp1_employe,
    calculer_qpp_supp2_employe,
    calculer_rqap_employe,
    calculer_rqap_employeur,
)
from compteqc.quebec.paie.impot_federal import calculer_impot_federal_periode
from compteqc.quebec.paie.impot_quebec import calculer_impot_quebec_periode
from compteqc.quebec.paie.ytd import obtenir_cumuls_annuels
from compteqc.quebec.rates import obtenir_taux

DEUX_DECIMALES = Decimal("0.01")


def _arrondir(montant: Decimal) -> Decimal:
    return montant.quantize(DEUX_DECIMALES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ResultatPaie:
    """Resultat complet d'un calcul de paie pour une periode."""

    brut: Decimal
    numero_periode: int
    nb_periodes: int

    # Retenues employe
    qpp_base: Decimal
    qpp_supp1: Decimal
    qpp_supp2: Decimal
    rqap: Decimal
    ae: Decimal
    impot_federal: Decimal
    impot_quebec: Decimal

    # Cotisations employeur
    qpp_base_employeur: Decimal
    qpp_supp1_employeur: Decimal
    qpp_supp2_employeur: Decimal
    rqap_employeur: Decimal
    ae_employeur: Decimal
    fss: Decimal
    cnesst: Decimal
    normes_travail: Decimal

    # Totaux
    total_retenues: Decimal
    total_cotisations_employeur: Decimal
    net: Decimal


def calculer_paie(
    brut: Decimal,
    numero_periode: int,
    chemin_ledger: str,
    annee: int = 2026,
    nb_periodes: int = 26,
) -> ResultatPaie:
    """Calcule une paie complete pour une periode donnee.

    Args:
        brut: Salaire brut pour cette periode.
        numero_periode: Numero de la periode de paie (1-26).
        chemin_ledger: Chemin vers le fichier principal beancount.
        annee: Annee fiscale.
        nb_periodes: Nombre de periodes par annee (defaut: 26 bi-hebdo).

    Returns:
        ResultatPaie avec toutes les retenues et cotisations calculees.
    """
    taux = obtenir_taux(annee)

    # Obtenir les cumuls YTD depuis le grand-livre
    cumuls = obtenir_cumuls_annuels(chemin_ledger, annee)

    # --- Retenues employe ---
    qpp_base = calculer_qpp_base_employe(
        brut, cumuls.get("qpp_base_employe", Decimal("0")),
        taux.qpp, nb_periodes,
    )
    qpp_supp1 = calculer_qpp_supp1_employe(
        brut, cumuls.get("qpp_supp1_employe", Decimal("0")),
        taux.qpp, nb_periodes,
    )
    qpp_supp2 = calculer_qpp_supp2_employe(
        brut, cumuls.get("qpp_supp2_employe", Decimal("0")),
        taux.qpp, nb_periodes,
    )
    rqap = calculer_rqap_employe(
        brut, cumuls.get("rqap_employe", Decimal("0")),
        taux.rqap, nb_periodes,
    )
    ae = calculer_ae_employe(
        brut, cumuls.get("ae_employe", Decimal("0")),
        taux.ae, nb_periodes,
    )

    # --- Cotisations employeur ---
    qpp_base_empl = calculer_qpp_base_employe(
        brut, cumuls.get("qpp_employeur", Decimal("0")),
        taux.qpp, nb_periodes,
    )
    qpp_supp1_empl = calculer_qpp_supp1_employe(
        brut, cumuls.get("qpp_employeur", Decimal("0")),
        taux.qpp, nb_periodes,
    )
    qpp_supp2_empl = calculer_qpp_supp2_employe(
        brut, cumuls.get("qpp_employeur", Decimal("0")),
        taux.qpp, nb_periodes,
    )
    rqap_empl = calculer_rqap_employeur(
        brut, cumuls.get("rqap_employeur", Decimal("0")),
        taux.rqap, nb_periodes,
    )
    ae_empl = calculer_ae_employeur(
        brut, cumuls.get("ae_employeur", Decimal("0")),
        taux.ae, nb_periodes,
    )

    # FSS: base sur la masse salariale annuelle estimee
    masse_salariale_annuelle = (
        cumuls.get("gains_bruts", Decimal("0")) + brut
    ) * nb_periodes / max(numero_periode, 1)
    fss = calculer_fss(masse_salariale_annuelle, taux.fss, nb_periodes)

    cnesst_montant = calculer_cnesst(brut, taux.cnesst_taux)

    normes = calculer_normes_travail(
        brut, cumuls.get("gains_bruts", Decimal("0")),
        taux.normes_travail_taux, taux.normes_travail_max_gains,
    )

    # --- Cotisations annualisees pour credits d'impot ---
    cotisations_annuelles = {
        "qpp_base": qpp_base * nb_periodes,
        "qpp_supp1": qpp_supp1 * nb_periodes,
        "qpp_total": (qpp_base + qpp_supp1) * nb_periodes,
        "rqap": rqap * nb_periodes,
        "ae": ae * nb_periodes,
    }

    # --- Impots ---
    impot_fed = calculer_impot_federal_periode(
        brut, nb_periodes, taux, cotisations_annuelles,
    )
    impot_qc = calculer_impot_quebec_periode(
        brut, nb_periodes, taux, cotisations_annuelles,
    )

    # --- Totaux ---
    total_retenues = _arrondir(
        qpp_base + qpp_supp1 + qpp_supp2 + rqap + ae
        + impot_fed + impot_qc
    )
    total_cotisations = _arrondir(
        qpp_base_empl + qpp_supp1_empl + qpp_supp2_empl
        + rqap_empl + ae_empl + fss + cnesst_montant + normes
    )
    net = _arrondir(brut - total_retenues)

    return ResultatPaie(
        brut=brut,
        numero_periode=numero_periode,
        nb_periodes=nb_periodes,
        qpp_base=qpp_base,
        qpp_supp1=qpp_supp1,
        qpp_supp2=qpp_supp2,
        rqap=rqap,
        ae=ae,
        impot_federal=impot_fed,
        impot_quebec=impot_qc,
        qpp_base_employeur=qpp_base_empl,
        qpp_supp1_employeur=qpp_supp1_empl,
        qpp_supp2_employeur=qpp_supp2_empl,
        rqap_employeur=rqap_empl,
        ae_employeur=ae_empl,
        fss=fss,
        cnesst=cnesst_montant,
        normes_travail=normes,
        total_retenues=total_retenues,
        total_cotisations_employeur=total_cotisations,
        net=net,
    )
