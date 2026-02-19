"""Tests pour les fonctions de calcul de cotisations (cotisations.py) et suivi cumul annuel (ytd.py).

Cas de test principal: salaire annuel de $60,000, bi-hebdomadaire (26 periodes).
Salaire brut par periode: $60,000 / 26 = $2,307.692307... arrondi a $2,307.69.
"""

from decimal import Decimal

import pytest

from compteqc.quebec.rates import obtenir_taux
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


@pytest.fixture
def taux_2026():
    return obtenir_taux(2026)


@pytest.fixture
def salaire_bihebd() -> Decimal:
    """Salaire brut bi-hebdomadaire pour $60,000 annuel."""
    return Decimal("2307.69")


@pytest.fixture
def salaire_bihebd_90k() -> Decimal:
    """Salaire brut bi-hebdomadaire pour $90,000 annuel."""
    return Decimal("3461.54")


NB_PERIODES = 26


# =============================================================================
# QPP Base (5.3%)
# =============================================================================
class TestQPPBaseEmploye:
    """QPP base: 5.3% sur gains cotisables ($3,500 exemption, max MGA $74,600)."""

    def test_calcul_normal(self, taux_2026, salaire_bihebd) -> None:
        """$2,307.69 - ($3,500/26 = $134.62) = $2,173.07 * 0.053 = $115.17."""
        result = calculer_qpp_base_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("0"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("115.17")

    def test_cap_annuel_partiel(self, taux_2026, salaire_bihebd) -> None:
        """Quand YTD = $3,700, reste = $3,768.30 - $3,700 = $68.30."""
        result = calculer_qpp_base_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("3700"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("68.30")

    def test_maximum_atteint_retourne_zero(self, taux_2026, salaire_bihebd) -> None:
        """Quand YTD >= max_base, retourne 0."""
        result = calculer_qpp_base_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("3768.30"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("0")

    def test_depasse_maximum_retourne_zero(self, taux_2026, salaire_bihebd) -> None:
        result = calculer_qpp_base_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("4000"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("0")

    def test_salaire_zero(self, taux_2026) -> None:
        result = calculer_qpp_base_employe(
            salaire_brut_periode=Decimal("0"),
            cumul_annuel=Decimal("0"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("0")


# =============================================================================
# QPP Supplementaire 1 (1.0%) -- meme plage que base, PAS d'exemption
# =============================================================================
class TestQPPSupp1Employe:
    """QPP supplementaire 1: 1.0% sur gains cotisables (meme plage, SANS exemption), max $711."""

    def test_calcul_normal(self, taux_2026, salaire_bihebd) -> None:
        """$2,307.69 (cap a MGA/26=$2,869.23) * 0.01 = $23.08."""
        result = calculer_qpp_supp1_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("0"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("23.08")

    def test_cap_annuel(self, taux_2026, salaire_bihebd) -> None:
        """Quand YTD = $700, reste = $711 - $700 = $11."""
        result = calculer_qpp_supp1_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("700"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("11.00")

    def test_maximum_atteint_retourne_zero(self, taux_2026, salaire_bihebd) -> None:
        result = calculer_qpp_supp1_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("711"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("0")


# =============================================================================
# QPP Supplementaire 2 (4.0%) -- seulement sur gains $74,600-$85,000
# =============================================================================
class TestQPPSupp2Employe:
    """QPP supplementaire 2: 4.0% sur gains entre MGA et MGAP ($74,600-$85,000)."""

    def test_salaire_sous_mga_retourne_zero(self, taux_2026, salaire_bihebd) -> None:
        """$60K annuel < $74,600 MGA: aucune cotisation supplementaire 2."""
        result = calculer_qpp_supp2_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("0"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("0")

    def test_salaire_entre_mga_et_mgap(self, taux_2026, salaire_bihebd_90k) -> None:
        """$90K annuel: gains = min($3,461.54, $85,000/26=$3,269.23) - $74,600/26=$2,869.23
        = $3,269.23 - $2,869.23 = $400.00 * 0.04 = $16.00."""
        result = calculer_qpp_supp2_employe(
            salaire_brut_periode=salaire_bihebd_90k,
            cumul_annuel=Decimal("0"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("16.00")

    def test_cap_annuel(self, taux_2026, salaire_bihebd_90k) -> None:
        """Quand YTD = $400, reste = $416 - $400 = $16."""
        result = calculer_qpp_supp2_employe(
            salaire_brut_periode=salaire_bihebd_90k,
            cumul_annuel=Decimal("400"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("16.00")

    def test_maximum_atteint_retourne_zero(self, taux_2026, salaire_bihebd_90k) -> None:
        result = calculer_qpp_supp2_employe(
            salaire_brut_periode=salaire_bihebd_90k,
            cumul_annuel=Decimal("416"),
            taux=taux_2026.qpp,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("0")


# =============================================================================
# RQAP Employe (0.430%) et Employeur (0.602%)
# =============================================================================
class TestRQAPEmploye:
    """RQAP employe: 0.430% sur gains, max MRA $103,000."""

    def test_calcul_normal(self, taux_2026, salaire_bihebd) -> None:
        """$2,307.69 * 0.00430 = $9.92."""
        result = calculer_rqap_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("0"),
            taux=taux_2026.rqap,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("9.92")

    def test_maximum_atteint_retourne_zero(self, taux_2026, salaire_bihebd) -> None:
        result = calculer_rqap_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("442.90"),
            taux=taux_2026.rqap,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("0")

    def test_cap_partiel(self, taux_2026, salaire_bihebd) -> None:
        """Quand YTD = $440, reste = $442.90 - $440 = $2.90."""
        result = calculer_rqap_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("440"),
            taux=taux_2026.rqap,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("2.90")


class TestRQAPEmployeur:
    """RQAP employeur: 0.602% sur gains, max MRA $103,000."""

    def test_calcul_normal(self, taux_2026, salaire_bihebd) -> None:
        """$2,307.69 * 0.00602 = $13.89."""
        result = calculer_rqap_employeur(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("0"),
            taux=taux_2026.rqap,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("13.89")

    def test_maximum_atteint_retourne_zero(self, taux_2026, salaire_bihebd) -> None:
        result = calculer_rqap_employeur(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("620.06"),
            taux=taux_2026.rqap,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("0")


# =============================================================================
# AE Employe (1.30%) et Employeur (1.82%)
# =============================================================================
class TestAEEmploye:
    """AE employe: 1.30% sur gains, max MRA $68,900."""

    def test_calcul_normal(self, taux_2026, salaire_bihebd) -> None:
        """$2,307.69 * 0.0130 = $30.00."""
        result = calculer_ae_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("0"),
            taux=taux_2026.ae,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("30.00")

    def test_maximum_atteint_retourne_zero(self, taux_2026, salaire_bihebd) -> None:
        result = calculer_ae_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("895.70"),
            taux=taux_2026.ae,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("0")

    def test_cap_partiel(self, taux_2026, salaire_bihebd) -> None:
        """Quand YTD = $880, reste = $895.70 - $880 = $15.70."""
        result = calculer_ae_employe(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("880"),
            taux=taux_2026.ae,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("15.70")


class TestAEEmployeur:
    """AE employeur: 1.82% sur gains, max MRA $68,900."""

    def test_calcul_normal(self, taux_2026, salaire_bihebd) -> None:
        """$2,307.69 * 0.0182 = $42.00."""
        result = calculer_ae_employeur(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("0"),
            taux=taux_2026.ae,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("42.00")

    def test_ytd_cap_employeur(self, taux_2026, salaire_bihebd) -> None:
        """Quand YTD employeur = $1,200, reste = $1,253.98 - $1,200 = $53.98."""
        result = calculer_ae_employeur(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("1200"),
            taux=taux_2026.ae,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("42.00") or result == Decimal("53.98")
        # Should be min(calculated=42.00, remaining=53.98) = 42.00
        assert result == Decimal("42.00")

    def test_maximum_atteint_retourne_zero(self, taux_2026, salaire_bihebd) -> None:
        result = calculer_ae_employeur(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("1253.98"),
            taux=taux_2026.ae,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("0")

    def test_cap_partiel_employeur(self, taux_2026, salaire_bihebd) -> None:
        """Quand YTD = $1,220, reste = $1,253.98 - $1,220 = $33.98."""
        result = calculer_ae_employeur(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel=Decimal("1220"),
            taux=taux_2026.ae,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("33.98")


# =============================================================================
# FSS (1.65% -- employeur seulement, annuel divise par periodes)
# =============================================================================
class TestFSS:
    """FSS: 1.65% sur masse salariale annuelle, divise par nb_periodes."""

    def test_calcul_normal(self, taux_2026) -> None:
        """$60,000 * 0.0165 = $990.00 / 26 = $38.08."""
        result = calculer_fss(
            masse_salariale_annuelle=Decimal("60000"),
            taux=taux_2026.fss,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("38.08")

    def test_masse_salariale_zero(self, taux_2026) -> None:
        result = calculer_fss(
            masse_salariale_annuelle=Decimal("0"),
            taux=taux_2026.fss,
            nb_periodes=NB_PERIODES,
        )
        assert result == Decimal("0")


# =============================================================================
# CNESST (pas de max annuel, taux * salaire)
# =============================================================================
class TestCNESST:
    """CNESST: taux configurable * salaire brut periode."""

    def test_calcul_normal(self, taux_2026, salaire_bihebd) -> None:
        """$2,307.69 * 0.0080 = $18.46."""
        result = calculer_cnesst(
            salaire_brut_periode=salaire_bihebd,
            taux_cnesst=taux_2026.cnesst_taux,
        )
        assert result == Decimal("18.46")

    def test_salaire_zero(self, taux_2026) -> None:
        result = calculer_cnesst(
            salaire_brut_periode=Decimal("0"),
            taux_cnesst=taux_2026.cnesst_taux,
        )
        assert result == Decimal("0")


# =============================================================================
# Normes du travail (0.06%, max gains $103,000)
# =============================================================================
class TestNormesTravail:
    """Normes du travail: 0.06% sur gains, max $103,000 annuel."""

    def test_calcul_normal(self, taux_2026, salaire_bihebd) -> None:
        """$2,307.69 * 0.0006 = $1.38."""
        result = calculer_normes_travail(
            salaire_brut_periode=salaire_bihebd,
            cumul_annuel_gains=Decimal("0"),
            taux=taux_2026.normes_travail_taux,
            max_gains=taux_2026.normes_travail_max_gains,
        )
        assert result == Decimal("1.38")

    def test_gains_au_maximum(self, taux_2026) -> None:
        """Quand cumul gains >= $103,000, retourne 0."""
        result = calculer_normes_travail(
            salaire_brut_periode=Decimal("2307.69"),
            cumul_annuel_gains=Decimal("103000"),
            taux=taux_2026.normes_travail_taux,
            max_gains=taux_2026.normes_travail_max_gains,
        )
        assert result == Decimal("0")

    def test_gains_partiels_au_max(self, taux_2026) -> None:
        """Quand cumul + salaire depasse $103,000, calcule seulement sur la portion restante."""
        result = calculer_normes_travail(
            salaire_brut_periode=Decimal("2307.69"),
            cumul_annuel_gains=Decimal("102000"),
            taux=taux_2026.normes_travail_taux,
            max_gains=taux_2026.normes_travail_max_gains,
        )
        # Gains restants: $103,000 - $102,000 = $1,000. $1,000 * 0.0006 = $0.60
        assert result == Decimal("0.60")


# =============================================================================
# Tests de retour Decimal (jamais float)
# =============================================================================
class TestRetourDecimal:
    """Verifie que toutes les fonctions retournent des Decimal."""

    def test_toutes_fonctions_retournent_decimal(self, taux_2026, salaire_bihebd) -> None:
        results = [
            calculer_qpp_base_employe(salaire_bihebd, Decimal("0"), taux_2026.qpp, NB_PERIODES),
            calculer_qpp_supp1_employe(salaire_bihebd, Decimal("0"), taux_2026.qpp, NB_PERIODES),
            calculer_qpp_supp2_employe(salaire_bihebd, Decimal("0"), taux_2026.qpp, NB_PERIODES),
            calculer_rqap_employe(salaire_bihebd, Decimal("0"), taux_2026.rqap, NB_PERIODES),
            calculer_rqap_employeur(salaire_bihebd, Decimal("0"), taux_2026.rqap, NB_PERIODES),
            calculer_ae_employe(salaire_bihebd, Decimal("0"), taux_2026.ae, NB_PERIODES),
            calculer_ae_employeur(salaire_bihebd, Decimal("0"), taux_2026.ae, NB_PERIODES),
            calculer_fss(Decimal("60000"), taux_2026.fss, NB_PERIODES),
            calculer_cnesst(salaire_bihebd, taux_2026.cnesst_taux),
            calculer_normes_travail(salaire_bihebd, Decimal("0"), taux_2026.normes_travail_taux, taux_2026.normes_travail_max_gains),
        ]
        for i, r in enumerate(results):
            assert isinstance(r, Decimal), f"Fonction {i} retourne {type(r)} au lieu de Decimal"
