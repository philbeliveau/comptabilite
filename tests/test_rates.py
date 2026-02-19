"""Tests pour le module de taux annuels (rates.py)."""

from decimal import Decimal

import pytest

from compteqc.quebec.rates import (
    TauxAnnuels,
    TrancheFederale,
    TrancheQuebec,
    obtenir_taux,
)


class TestObtenirTaux:
    """Tests pour la fonction obtenir_taux."""

    def test_obtenir_taux_2026_retourne_taux_annuels(self) -> None:
        taux = obtenir_taux(2026)
        assert isinstance(taux, TauxAnnuels)
        assert taux.annee == 2026

    def test_obtenir_taux_annee_non_disponible_leve_erreur(self) -> None:
        with pytest.raises(ValueError, match="Taux non disponibles pour l'annee 2025"):
            obtenir_taux(2025)

    def test_obtenir_taux_annee_future_leve_erreur(self) -> None:
        with pytest.raises(ValueError):
            obtenir_taux(2099)


class TestTauxQPP:
    """Tests des taux QPP 2026."""

    def test_qpp_taux_base(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.qpp.taux_base == Decimal("0.053")

    def test_qpp_taux_supplementaire_1(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.qpp.taux_supplementaire_1 == Decimal("0.01")

    def test_qpp_taux_supplementaire_2(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.qpp.taux_supplementaire_2 == Decimal("0.04")

    def test_qpp_exemption(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.qpp.exemption == Decimal("3500")

    def test_qpp_mga(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.qpp.mga == Decimal("74600")

    def test_qpp_mgap(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.qpp.mgap == Decimal("85000")

    def test_qpp_max_base(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.qpp.max_base == Decimal("3768.30")

    def test_qpp_max_supp1(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.qpp.max_supp1 == Decimal("711.00")

    def test_qpp_max_supp2(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.qpp.max_supp2 == Decimal("416.00")


class TestTauxRQAP:
    """Tests des taux RQAP 2026."""

    def test_rqap_taux_employe(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.rqap.taux_employe == Decimal("0.00430")

    def test_rqap_taux_employeur(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.rqap.taux_employeur == Decimal("0.00602")

    def test_rqap_mra(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.rqap.mra == Decimal("103000")


class TestTauxAE:
    """Tests des taux AE 2026 (taux Quebec)."""

    def test_ae_taux_employe(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.ae.taux_employe == Decimal("0.0130")

    def test_ae_taux_employeur(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.ae.taux_employeur == Decimal("0.0182")

    def test_ae_mra(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.ae.mra == Decimal("68900")

    def test_ae_max_employe(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.ae.max_employe == Decimal("895.70")

    def test_ae_max_employeur(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.ae.max_employeur == Decimal("1253.98")


class TestTranchesFederales:
    """Tests des tranches d'imposition federale 2026."""

    def test_cinq_tranches_federales(self) -> None:
        taux = obtenir_taux(2026)
        assert len(taux.tranches_federales) == 5

    def test_premiere_tranche_federale_taux_14_pourcent(self) -> None:
        """Le taux le plus bas est 14% en 2026, PAS 15%."""
        taux = obtenir_taux(2026)
        assert taux.tranches_federales[0].taux == Decimal("0.14")
        assert taux.tranches_federales[0].constante_k == Decimal("0")

    def test_tranches_federales_ordonnees(self) -> None:
        taux = obtenir_taux(2026)
        seuils = [t.seuil for t in taux.tranches_federales]
        assert seuils == sorted(seuils)

    def test_tranches_federales_sont_tuples(self) -> None:
        taux = obtenir_taux(2026)
        for tranche in taux.tranches_federales:
            assert isinstance(tranche, TrancheFederale)

    def test_deuxieme_tranche_federale(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.tranches_federales[1].taux == Decimal("0.205")
        assert taux.tranches_federales[1].constante_k == Decimal("3804")


class TestTranchesQuebec:
    """Tests des tranches d'imposition Quebec 2026."""

    def test_quatre_tranches_quebec(self) -> None:
        taux = obtenir_taux(2026)
        assert len(taux.tranches_quebec) == 4

    def test_premiere_tranche_quebec(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.tranches_quebec[0].taux == Decimal("0.14")
        assert taux.tranches_quebec[0].constante == Decimal("0")

    def test_tranches_quebec_ordonnees(self) -> None:
        taux = obtenir_taux(2026)
        seuils = [t.seuil for t in taux.tranches_quebec]
        assert seuils == sorted(seuils)

    def test_tranches_quebec_sont_tuples(self) -> None:
        taux = obtenir_taux(2026)
        for tranche in taux.tranches_quebec:
            assert isinstance(tranche, TrancheQuebec)


class TestMontantsPersonnels:
    """Tests des montants personnels et autres taux generaux."""

    def test_montant_personnel_federal(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.montant_personnel_federal == Decimal("16452")

    def test_montant_personnel_quebec(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.montant_personnel_quebec == Decimal("18952")

    def test_abattement_quebec(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.abattement_quebec == Decimal("0.165")

    def test_tps_taux(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.tps_taux == Decimal("0.05")

    def test_tvq_taux(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.tvq_taux == Decimal("0.09975")


class TestFSS:
    """Tests des taux FSS 2026."""

    def test_fss_taux(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.fss.taux_service_petite == Decimal("0.0165")

    def test_fss_seuil(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.fss.seuil_masse_salariale == Decimal("1000000")


class TestNormesTravail:
    """Tests des taux normes du travail 2026."""

    def test_normes_travail_taux(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.normes_travail_taux == Decimal("0.0006")

    def test_normes_travail_max_gains(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.normes_travail_max_gains == Decimal("103000")


class TestCNESST:
    """Tests du taux CNESST par defaut."""

    def test_cnesst_taux_defaut(self) -> None:
        taux = obtenir_taux(2026)
        assert taux.cnesst_taux == Decimal("0.0080")


class TestImmutabilite:
    """Tests que les dataclasses sont immuables (frozen)."""

    def test_taux_annuels_immutable(self) -> None:
        taux = obtenir_taux(2026)
        with pytest.raises(AttributeError):
            taux.annee = 2025  # type: ignore[misc]

    def test_qpp_immutable(self) -> None:
        taux = obtenir_taux(2026)
        with pytest.raises(AttributeError):
            taux.qpp.taux_base = Decimal("0.06")  # type: ignore[misc]


class TestAucunFloat:
    """Verifie qu'aucune valeur n'est un float."""

    def test_tous_les_taux_sont_decimal(self) -> None:
        taux = obtenir_taux(2026)
        # Verifie les champs numeriques de TauxAnnuels
        for field_name in [
            "cnesst_taux",
            "normes_travail_taux",
            "normes_travail_max_gains",
            "montant_personnel_federal",
            "montant_personnel_quebec",
            "abattement_quebec",
            "tps_taux",
            "tvq_taux",
        ]:
            val = getattr(taux, field_name)
            assert isinstance(val, Decimal), f"{field_name} devrait etre Decimal, est {type(val)}"

    def test_qpp_taux_sont_decimal(self) -> None:
        taux = obtenir_taux(2026)
        for field_name in [
            "taux_base",
            "taux_supplementaire_1",
            "taux_supplementaire_2",
            "exemption",
            "mga",
            "mgap",
            "max_base",
            "max_supp1",
            "max_supp2",
        ]:
            val = getattr(taux.qpp, field_name)
            assert isinstance(val, Decimal), f"qpp.{field_name} devrait etre Decimal"
