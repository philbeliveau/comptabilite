"""Fonctions de calcul de cotisations de paie pour le Quebec.

Toutes les fonctions sont pures (pas d'effets de bord), prennent des Decimal
en entree et retournent des Decimal. Aucun float n'est utilise.

Source des formules: Retraite Quebec, Revenu Quebec, CRA (T4127 122e ed.).
"""

from decimal import ROUND_HALF_UP, Decimal

from compteqc.quebec.rates import TauxAE, TauxFSS, TauxQPP, TauxRQAP

DEUX_DECIMALES = Decimal("0.01")


def _arrondir(montant: Decimal) -> Decimal:
    """Arrondit au cent pres (ROUND_HALF_UP)."""
    return montant.quantize(DEUX_DECIMALES, rounding=ROUND_HALF_UP)


# =============================================================================
# QPP Base (5.3%)
# =============================================================================
def calculer_qpp_base_employe(
    salaire_brut_periode: Decimal,
    cumul_annuel: Decimal,
    taux: TauxQPP,
    nb_periodes: int,
) -> Decimal:
    """Calcule la cotisation QPP de base pour une periode de paie.

    Gains cotisables = min(salaire, MGA/P) - exemption/P
    Cotisation = gains_cotisables * taux_base
    Cap au maximum annuel moins le cumul YTD.
    """
    exemption_periode = _arrondir(taux.exemption / nb_periodes)
    mga_periode = _arrondir(taux.mga / nb_periodes)

    gains_cotisables = max(
        Decimal("0"),
        min(salaire_brut_periode, mga_periode) - exemption_periode,
    )
    cotisation = _arrondir(gains_cotisables * taux.taux_base)

    reste = max(Decimal("0"), taux.max_base - cumul_annuel)
    return min(cotisation, reste)


# =============================================================================
# QPP Supplementaire 1 (1.0%) -- meme plage que base, SANS exemption
# =============================================================================
def calculer_qpp_supp1_employe(
    salaire_brut_periode: Decimal,
    cumul_annuel: Decimal,
    taux: TauxQPP,
    nb_periodes: int,
) -> Decimal:
    """Calcule la cotisation QPP supplementaire 1 pour une periode.

    Meme plage de gains que la base (jusqu'au MGA), mais SANS exemption.
    Taux: 1.0%, maximum separe de $711.
    """
    mga_periode = _arrondir(taux.mga / nb_periodes)

    gains_cotisables = max(
        Decimal("0"),
        min(salaire_brut_periode, mga_periode),
    )
    cotisation = _arrondir(gains_cotisables * taux.taux_supplementaire_1)

    reste = max(Decimal("0"), taux.max_supp1 - cumul_annuel)
    return min(cotisation, reste)


# =============================================================================
# QPP Supplementaire 2 (4.0%) -- seulement sur gains MGA-MGAP
# =============================================================================
def calculer_qpp_supp2_employe(
    salaire_brut_periode: Decimal,
    cumul_annuel: Decimal,
    taux: TauxQPP,
    nb_periodes: int,
) -> Decimal:
    """Calcule la cotisation QPP supplementaire 2 pour une periode.

    Seulement sur les gains entre MGA ($74,600) et MGAP ($85,000).
    Taux: 4.0%, maximum $416.
    """
    mga_periode = _arrondir(taux.mga / nb_periodes)
    mgap_periode = _arrondir(taux.mgap / nb_periodes)

    gains_cotisables = max(
        Decimal("0"),
        min(salaire_brut_periode, mgap_periode) - mga_periode,
    )
    cotisation = _arrondir(gains_cotisables * taux.taux_supplementaire_2)

    reste = max(Decimal("0"), taux.max_supp2 - cumul_annuel)
    return min(cotisation, reste)


# =============================================================================
# RQAP Employe (0.430%)
# =============================================================================
def calculer_rqap_employe(
    salaire_brut_periode: Decimal,
    cumul_annuel: Decimal,
    taux: TauxRQAP,
    nb_periodes: int,
) -> Decimal:
    """Calcule la cotisation RQAP employe pour une periode.

    Taux: 0.430% sur gains assurables, max MRA $103,000.
    """
    mra_periode = _arrondir(taux.mra / nb_periodes)

    gains_assurables = min(salaire_brut_periode, mra_periode)
    cotisation = _arrondir(gains_assurables * taux.taux_employe)

    reste = max(Decimal("0"), taux.max_employe - cumul_annuel)
    return min(cotisation, reste)


# =============================================================================
# RQAP Employeur (0.602%)
# =============================================================================
def calculer_rqap_employeur(
    salaire_brut_periode: Decimal,
    cumul_annuel: Decimal,
    taux: TauxRQAP,
    nb_periodes: int,
) -> Decimal:
    """Calcule la cotisation RQAP employeur pour une periode.

    Taux: 0.602% sur gains assurables, max MRA $103,000.
    """
    mra_periode = _arrondir(taux.mra / nb_periodes)

    gains_assurables = min(salaire_brut_periode, mra_periode)
    cotisation = _arrondir(gains_assurables * taux.taux_employeur)

    reste = max(Decimal("0"), taux.max_employeur - cumul_annuel)
    return min(cotisation, reste)


# =============================================================================
# AE Employe (1.30% -- taux Quebec)
# =============================================================================
def calculer_ae_employe(
    salaire_brut_periode: Decimal,
    cumul_annuel: Decimal,
    taux: TauxAE,
    nb_periodes: int,
) -> Decimal:
    """Calcule la prime AE employe pour une periode.

    Taux Quebec: 1.30% sur remuneration assurable, max MRA $68,900.
    """
    mra_periode = _arrondir(taux.mra / nb_periodes)

    gains_assurables = min(salaire_brut_periode, mra_periode)
    cotisation = _arrondir(gains_assurables * taux.taux_employe)

    reste = max(Decimal("0"), taux.max_employe - cumul_annuel)
    return min(cotisation, reste)


# =============================================================================
# AE Employeur (1.82% -- 1.4x taux employe)
# =============================================================================
def calculer_ae_employeur(
    salaire_brut_periode: Decimal,
    cumul_annuel: Decimal,
    taux: TauxAE,
    nb_periodes: int,
) -> Decimal:
    """Calcule la prime AE employeur pour une periode.

    Taux Quebec: 1.82% (1.4x employe) sur remuneration assurable, max MRA $68,900.
    """
    mra_periode = _arrondir(taux.mra / nb_periodes)

    gains_assurables = min(salaire_brut_periode, mra_periode)
    cotisation = _arrondir(gains_assurables * taux.taux_employeur)

    reste = max(Decimal("0"), taux.max_employeur - cumul_annuel)
    return min(cotisation, reste)


# =============================================================================
# FSS (1.65% -- employeur seulement, base annuelle)
# =============================================================================
def calculer_fss(
    masse_salariale_annuelle: Decimal,
    taux: TauxFSS,
    nb_periodes: int,
) -> Decimal:
    """Calcule la cotisation FSS par periode.

    FSS est calcule sur la masse salariale annuelle totale, puis divise
    par le nombre de periodes pour la provision periodique.
    Taux: 1.65% (secteur services, masse salariale <= $1M).
    """
    cotisation_annuelle = _arrondir(masse_salariale_annuelle * taux.taux_service_petite)
    return _arrondir(cotisation_annuelle / nb_periodes)


# =============================================================================
# CNESST (pas de maximum annuel pour la cotisation)
# =============================================================================
def calculer_cnesst(
    salaire_brut_periode: Decimal,
    taux_cnesst: Decimal,
) -> Decimal:
    """Calcule la cotisation CNESST pour une periode.

    Taux configurable par employeur (defaut 0.80%).
    Pas de maximum annuel de cotisation (mais gains assurables plafonnes au MRA).
    """
    return _arrondir(salaire_brut_periode * taux_cnesst)


# =============================================================================
# Normes du travail (0.06%, max gains $103,000)
# =============================================================================
def calculer_normes_travail(
    salaire_brut_periode: Decimal,
    cumul_annuel_gains: Decimal,
    taux: Decimal,
    max_gains: Decimal,
) -> Decimal:
    """Calcule la cotisation normes du travail pour une periode.

    Taux: 0.06% sur gains jusqu'a un maximum de $103,000 annuel.
    Employeur seulement.
    """
    gains_restants = max(Decimal("0"), max_gains - cumul_annuel_gains)
    gains_assurables = min(salaire_brut_periode, gains_restants)
    return _arrondir(gains_assurables * taux)
