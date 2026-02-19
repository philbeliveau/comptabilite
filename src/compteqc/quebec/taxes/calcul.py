"""Calcul TPS/TVQ: extraction de taxes d'un montant TTC et application sur montant HT.

Toute l'arithmetique utilise Decimal avec ROUND_HALF_UP. Les taux TPS et TVQ
ne sont jamais combines en un seul taux de 14.975%.
"""

from decimal import Decimal, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")


def extraire_taxes(
    total_ttc: Decimal,
    taux_tps: Decimal,
    taux_tvq: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Extrait TPS et TVQ d'un montant TTC (taxes incluses).

    TPS et TVQ sont arrondis independamment au cent pres.
    Le montant avant taxes est la valeur de bouclage (plug):
      avant_taxes = total_ttc - tps - tvq

    Cela garantit que la somme des trois composantes egale exactement le total.

    Args:
        total_ttc: Montant total taxes incluses.
        taux_tps: Taux de TPS (ex: Decimal("0.05")).
        taux_tvq: Taux de TVQ (ex: Decimal("0.09975")).

    Returns:
        (avant_taxes, tps, tvq)
    """
    if total_ttc == Decimal("0"):
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    taux_combine = Decimal("1") + taux_tps + taux_tvq
    base_estimee = total_ttc / taux_combine

    tps = (base_estimee * taux_tps).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    tvq = (base_estimee * taux_tvq).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    # Plug value: garantit que avant_taxes + tps + tvq == total_ttc
    avant_taxes = total_ttc - tps - tvq

    return avant_taxes, tps, tvq


def appliquer_taxes(
    montant_ht: Decimal,
    taux_tps: Decimal,
    taux_tvq: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Applique TPS et TVQ sur un montant HT (pour revenus).

    Args:
        montant_ht: Montant hors taxes.
        taux_tps: Taux de TPS (ex: Decimal("0.05")).
        taux_tvq: Taux de TVQ (ex: Decimal("0.09975")).

    Returns:
        (tps, tvq, total_ttc)
    """
    tps = (montant_ht * taux_tps).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    tvq = (montant_ht * taux_tvq).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    total_ttc = montant_ht + tps + tvq
    return tps, tvq, total_ttc


def extraire_taxes_selon_traitement(
    total: Decimal,
    traitement: str,
    taux_tps: Decimal,
    taux_tvq: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Route le calcul de taxes selon le type de traitement fiscal.

    Args:
        total: Montant total de la transaction.
        traitement: Type de traitement: 'taxable', 'exempt', 'zero',
                    'tps_seulement', 'tps_tvq', 'aucune_taxe'.
        taux_tps: Taux de TPS.
        taux_tvq: Taux de TVQ.

    Returns:
        (avant_taxes, tps, tvq)
        Pour exempt/zero/aucune_taxe: (total, 0, 0).
        Pour tps_seulement: TPS extraite, TVQ = 0.
    """
    if traitement in ("exempt", "zero", "aucune_taxe"):
        return total, Decimal("0.00"), Decimal("0.00")

    if traitement == "tps_seulement":
        taux_combine_tps = Decimal("1") + taux_tps
        base_estimee = total / taux_combine_tps
        tps = (base_estimee * taux_tps).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        avant_taxes = total - tps
        return avant_taxes, tps, Decimal("0.00")

    # taxable, tps_tvq: les deux taxes
    return extraire_taxes(total, taux_tps, taux_tvq)
