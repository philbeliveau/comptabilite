"""Calcul de la retenue d'impot Quebec per-periode selon TP-1015.F-V.

Formule simplifiee pour un employe regulier:
1. Annualiser le salaire brut
2. Appliquer la deduction pour travailleur (6% du revenu, max $1,450)
3. Trouver la tranche (T, K) applicable sur le revenu imposable
4. Calculer les credits: K1 (personnel), E (cotisations)
5. Y = max(0, T * revenu_imposable - K - K1 - E)
6. Per-period = Y / nb_periodes

Toutes les valeurs sont en Decimal -- jamais de float.
"""

from decimal import ROUND_HALF_UP, Decimal

from compteqc.quebec.rates import TauxAnnuels

DEUX_DECIMALES = Decimal("0.01")
TAUX_CREDITS_QUEBEC = Decimal("0.14")  # Taux le plus bas Quebec pour credits


def _arrondir(montant: Decimal) -> Decimal:
    """Arrondit au cent pres (ROUND_HALF_UP)."""
    return montant.quantize(DEUX_DECIMALES, rounding=ROUND_HALF_UP)


def calculer_impot_quebec_periode(
    salaire_brut_periode: Decimal,
    nb_periodes: int,
    taux: TauxAnnuels,
    cotisations_annuelles: dict[str, Decimal],
) -> Decimal:
    """Calcule la retenue d'impot Quebec pour une periode de paie.

    Args:
        salaire_brut_periode: Salaire brut pour cette periode.
        nb_periodes: Nombre de periodes de paie par annee (ex: 26 bi-hebdo).
        taux: Taux annuels (contient tranches Quebec, montant personnel).
        cotisations_annuelles: Dict avec cles 'qpp_total', 'rqap'
            contenant les cotisations annualisees.

    Returns:
        Montant d'impot Quebec a retenir pour cette periode (>= 0).
    """
    if salaire_brut_periode <= Decimal("0"):
        return Decimal("0")

    # 1. Annualiser le revenu
    revenu_annuel = salaire_brut_periode * nb_periodes

    # 2. Deduction pour travailleur (6% du revenu d'emploi, max $1,450)
    DEDUCTION_TRAVAILLEUR = Decimal("1450")
    deduction_travailleur = min(revenu_annuel * Decimal("0.06"), DEDUCTION_TRAVAILLEUR)
    revenu_imposable = revenu_annuel - deduction_travailleur

    # 3. Trouver la tranche applicable (T, K)
    taux_marginal = taux.tranches_quebec[-1].taux
    constante = taux.tranches_quebec[-1].constante
    for tranche in taux.tranches_quebec:
        if revenu_imposable <= tranche.seuil:
            taux_marginal = tranche.taux
            constante = tranche.constante
            break

    # 3. Credits non-remboursables
    # K1: credit personnel de base
    k1 = TAUX_CREDITS_QUEBEC * taux.montant_personnel_quebec

    # E: credits pour cotisations (Quebec utilise QPP total, pas seulement la base)
    qpp_total = cotisations_annuelles.get("qpp_total", Decimal("0"))
    rqap_annuel = cotisations_annuelles.get("rqap", Decimal("0"))
    e = TAUX_CREDITS_QUEBEC * (qpp_total + rqap_annuel)

    # 4. Impot provincial (Y) -- sur revenu imposable (apres deduction travailleur)
    y = max(Decimal("0"), taux_marginal * revenu_imposable - constante - k1 - e)

    # 5. Retenue par periode
    return _arrondir(y / nb_periodes)
