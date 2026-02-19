"""Tests pour les calculs d'impot federal et Quebec sur la paie.

TDD RED: Tests ecrits AVANT l'implementation.
Source formules: T4127 122e ed. (federal), TP-1015.F-V (Quebec).
"""

from decimal import Decimal

import pytest

from compteqc.quebec.rates import obtenir_taux


TAUX = obtenir_taux(2026)
NB_PERIODES = 26  # Bi-hebdomadaire


def _cotisations_annuelles_type(brut_periode: Decimal) -> dict[str, Decimal]:
    """Calcule des cotisations annuelles approximatives pour les credits d'impot.

    Utilise les fonctions de cotisations.py pour des valeurs coherentes.
    """
    from compteqc.quebec.paie.cotisations import (
        calculer_ae_employe,
        calculer_qpp_base_employe,
        calculer_qpp_supp1_employe,
        calculer_rqap_employe,
    )

    qpp_base = calculer_qpp_base_employe(brut_periode, Decimal("0"), TAUX.qpp, NB_PERIODES)
    qpp_supp1 = calculer_qpp_supp1_employe(brut_periode, Decimal("0"), TAUX.qpp, NB_PERIODES)
    rqap = calculer_rqap_employe(brut_periode, Decimal("0"), TAUX.rqap, NB_PERIODES)
    ae = calculer_ae_employe(brut_periode, Decimal("0"), TAUX.ae, NB_PERIODES)

    return {
        "qpp_base": qpp_base * NB_PERIODES,
        "qpp_supp1": qpp_supp1 * NB_PERIODES,
        "qpp_total": (qpp_base + qpp_supp1) * NB_PERIODES,
        "rqap": rqap * NB_PERIODES,
        "ae": ae * NB_PERIODES,
    }


# =============================================================================
# Tests impot federal (T4127)
# =============================================================================
class TestImpotFederal:
    """Tests pour calculer_impot_federal_periode."""

    def test_revenu_60k_premiere_tranche(self):
        """$60,000 annualise: tranche 14%, K=0.

        T3 = 0.14 * 60000 - 0 - K1 - K2Q - K4
        K1 = 0.14 * 16452 = 2303.28
        K4 = 0.14 * 1428 = 199.92
        K2Q = 0.14 * (qpp_base_credit + ae + rqap)
        T1 = T3 * (1 - 0.165)  -- abattement Quebec
        Per-period = T1 / 26
        """
        from compteqc.quebec.paie.impot_federal import calculer_impot_federal_periode

        brut_periode = Decimal("60000") / NB_PERIODES  # ~2307.69
        cotisations = _cotisations_annuelles_type(brut_periode)

        resultat = calculer_impot_federal_periode(
            brut_periode, NB_PERIODES, TAUX, cotisations
        )

        assert isinstance(resultat, Decimal)
        # After abatement, annual tax should be roughly $4,000-5,500
        # Per period: ~$150-210
        assert Decimal("100") < resultat < Decimal("250"), f"Got {resultat}"

    def test_revenu_120k_deuxieme_tranche(self):
        """$120,000 annualise: tranche 20.5%, K=$3,804."""
        from compteqc.quebec.paie.impot_federal import calculer_impot_federal_periode

        brut_periode = Decimal("120000") / NB_PERIODES
        cotisations = _cotisations_annuelles_type(brut_periode)

        resultat = calculer_impot_federal_periode(
            brut_periode, NB_PERIODES, TAUX, cotisations
        )

        assert isinstance(resultat, Decimal)
        # Higher bracket, annual ~$12,000-16,000 after abatement
        # Per period: ~$460-620
        assert Decimal("400") < resultat < Decimal("700"), f"Got {resultat}"

    def test_revenu_zero_retourne_zero(self):
        """Revenu zero donne zero d'impot."""
        from compteqc.quebec.paie.impot_federal import calculer_impot_federal_periode

        cotisations = {
            "qpp_base": Decimal("0"),
            "qpp_supp1": Decimal("0"),
            "qpp_total": Decimal("0"),
            "rqap": Decimal("0"),
            "ae": Decimal("0"),
        }

        resultat = calculer_impot_federal_periode(
            Decimal("0"), NB_PERIODES, TAUX, cotisations
        )

        assert resultat == Decimal("0")

    def test_impot_jamais_negatif(self):
        """L'impot ne peut jamais etre negatif (plancher a zero)."""
        from compteqc.quebec.paie.impot_federal import calculer_impot_federal_periode

        # Very small salary where credits exceed tax
        brut_periode = Decimal("200")
        cotisations = _cotisations_annuelles_type(brut_periode)

        resultat = calculer_impot_federal_periode(
            brut_periode, NB_PERIODES, TAUX, cotisations
        )

        assert resultat >= Decimal("0")

    def test_retourne_decimal_deux_decimales(self):
        """Le resultat est arrondi a 2 decimales."""
        from compteqc.quebec.paie.impot_federal import calculer_impot_federal_periode

        brut_periode = Decimal("60000") / NB_PERIODES
        cotisations = _cotisations_annuelles_type(brut_periode)

        resultat = calculer_impot_federal_periode(
            brut_periode, NB_PERIODES, TAUX, cotisations
        )

        # Check it has at most 2 decimal places
        assert resultat == resultat.quantize(Decimal("0.01"))


# =============================================================================
# Tests impot Quebec (TP-1015.F-V)
# =============================================================================
class TestImpotQuebec:
    """Tests pour calculer_impot_quebec_periode."""

    def test_revenu_60k_premiere_tranche(self):
        """$60,000 annualise: tranche 14%, K=0.

        Y = 0.14 * 60000 - 0 - K1 - E
        K1 = 0.14 * 18952 = 2653.28
        E = 0.14 * (qpp_total + rqap)
        Per-period = Y / 26
        """
        from compteqc.quebec.paie.impot_quebec import calculer_impot_quebec_periode

        brut_periode = Decimal("60000") / NB_PERIODES
        cotisations = _cotisations_annuelles_type(brut_periode)

        resultat = calculer_impot_quebec_periode(
            brut_periode, NB_PERIODES, TAUX, cotisations
        )

        assert isinstance(resultat, Decimal)
        # Quebec tax on $60K: ~$4,000-6,000 annual, ~$150-230 per period
        assert Decimal("100") < resultat < Decimal("280"), f"Got {resultat}"

    def test_revenu_120k_deuxieme_tranche(self):
        """$120,000 annualise: tranche 19%, K=$2,717."""
        from compteqc.quebec.paie.impot_quebec import calculer_impot_quebec_periode

        brut_periode = Decimal("120000") / NB_PERIODES
        cotisations = _cotisations_annuelles_type(brut_periode)

        resultat = calculer_impot_quebec_periode(
            brut_periode, NB_PERIODES, TAUX, cotisations
        )

        assert isinstance(resultat, Decimal)
        # Quebec tax on $120K: ~$14,000-18,000 annual, ~$540-700 per period
        assert Decimal("450") < resultat < Decimal("800"), f"Got {resultat}"

    def test_revenu_zero_retourne_zero(self):
        """Revenu zero donne zero d'impot."""
        from compteqc.quebec.paie.impot_quebec import calculer_impot_quebec_periode

        cotisations = {
            "qpp_base": Decimal("0"),
            "qpp_supp1": Decimal("0"),
            "qpp_total": Decimal("0"),
            "rqap": Decimal("0"),
            "ae": Decimal("0"),
        }

        resultat = calculer_impot_quebec_periode(
            Decimal("0"), NB_PERIODES, TAUX, cotisations
        )

        assert resultat == Decimal("0")

    def test_impot_jamais_negatif(self):
        """L'impot Quebec ne peut jamais etre negatif."""
        from compteqc.quebec.paie.impot_quebec import calculer_impot_quebec_periode

        brut_periode = Decimal("200")
        cotisations = _cotisations_annuelles_type(brut_periode)

        resultat = calculer_impot_quebec_periode(
            brut_periode, NB_PERIODES, TAUX, cotisations
        )

        assert resultat >= Decimal("0")

    def test_retourne_decimal_deux_decimales(self):
        """Le resultat est arrondi a 2 decimales."""
        from compteqc.quebec.paie.impot_quebec import calculer_impot_quebec_periode

        brut_periode = Decimal("60000") / NB_PERIODES
        cotisations = _cotisations_annuelles_type(brut_periode)

        resultat = calculer_impot_quebec_periode(
            brut_periode, NB_PERIODES, TAUX, cotisations
        )

        assert resultat == resultat.quantize(Decimal("0.01"))
