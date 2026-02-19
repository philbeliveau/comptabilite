"""Calcul de la retenue d'impot federal per-periode selon T4127 122e edition.

Formule simplifiee pour un employe regulier au Quebec:
1. Annualiser le salaire brut
2. Trouver la tranche (R, K) applicable
3. Calculer les credits: K1 (personnel), K2Q (cotisations), K4 (emploi)
4. T3 = max(0, R * A - K - K1 - K2Q - K4)
5. T1 = max(0, T3 * (1 - 0.165))  -- abattement Quebec 16.5%
6. Per-period = T1 / nb_periodes

Toutes les valeurs sont en Decimal -- jamais de float.
"""

from decimal import ROUND_HALF_UP, Decimal

from compteqc.quebec.rates import TauxAnnuels

DEUX_DECIMALES = Decimal("0.01")
TAUX_CREDITS_FEDERAL = Decimal("0.14")  # Taux le plus bas federal pour credits
CREDIT_EMPLOI_CANADA = Decimal("1428")  # Montant du credit d'emploi du Canada 2026


def _arrondir(montant: Decimal) -> Decimal:
    """Arrondit au cent pres (ROUND_HALF_UP)."""
    return montant.quantize(DEUX_DECIMALES, rounding=ROUND_HALF_UP)


def calculer_impot_federal_periode(
    salaire_brut_periode: Decimal,
    nb_periodes: int,
    taux: TauxAnnuels,
    cotisations_annuelles: dict[str, Decimal],
) -> Decimal:
    """Calcule la retenue d'impot federal pour une periode de paie.

    Args:
        salaire_brut_periode: Salaire brut pour cette periode.
        nb_periodes: Nombre de periodes de paie par annee (ex: 26 bi-hebdo).
        taux: Taux annuels (contient tranches, montant personnel, abattement).
        cotisations_annuelles: Dict avec cles 'qpp_base', 'qpp_supp1', 'ae', 'rqap'
            contenant les cotisations annualisees (periode * nb_periodes).

    Returns:
        Montant d'impot federal a retenir pour cette periode (>= 0).
    """
    if salaire_brut_periode <= Decimal("0"):
        return Decimal("0")

    # 1. Annualiser le revenu
    revenu_annuel = salaire_brut_periode * nb_periodes

    # 2. Trouver la tranche applicable (R, K)
    taux_marginal = taux.tranches_federales[-1].taux
    constante_k = taux.tranches_federales[-1].constante_k
    for tranche in taux.tranches_federales:
        if revenu_annuel <= tranche.seuil:
            taux_marginal = tranche.taux
            constante_k = tranche.constante_k
            break

    # 3. Credits non-remboursables
    # K1: credit personnel de base
    k1 = TAUX_CREDITS_FEDERAL * taux.montant_personnel_federal

    # K2Q: credits pour cotisations (specifique au Quebec)
    # Pour le credit QPP federal, on utilise la portion base seulement
    # ajustee au ratio base/total (5.3% / 6.3%)
    qpp_base_annuel = cotisations_annuelles.get("qpp_base", Decimal("0"))
    qpp_base_credit = qpp_base_annuel * Decimal("0.053") / Decimal("0.063")
    ae_annuel = cotisations_annuelles.get("ae", Decimal("0"))
    rqap_annuel = cotisations_annuelles.get("rqap", Decimal("0"))
    k2q = TAUX_CREDITS_FEDERAL * (qpp_base_credit + ae_annuel + rqap_annuel)

    # K4: credit canadien pour emploi
    k4 = TAUX_CREDITS_FEDERAL * CREDIT_EMPLOI_CANADA

    # 4. Impot de base (T3)
    t3 = max(Decimal("0"), taux_marginal * revenu_annuel - constante_k - k1 - k2q - k4)

    # 5. Abattement du Quebec (16.5%)
    t1 = max(Decimal("0"), t3 * (Decimal("1") - taux.abattement_quebec))

    # 6. Retenue par periode
    return _arrondir(t1 / nb_periodes)
