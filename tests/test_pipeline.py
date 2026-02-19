"""Tests pour le pipeline de categorisation a trois niveaux."""

from __future__ import annotations

from decimal import Decimal

import pytest

from compteqc.categorisation.ml import PredicteurML, ResultatML


# --- ML Predictor Tests ---


class TestPredicteurML:
    """Tests pour le predicteur ML."""

    def test_cold_start_not_trained(self):
        """ML avec aucune donnee n'est pas entraine."""
        ml = PredicteurML()
        assert ml.est_entraine is False

    def test_cold_start_insufficient_data(self):
        """ML avec moins de MIN_TRAINING_SIZE entrees reste non-entraine."""
        ml = PredicteurML()
        # 5 entries, well below 20
        data = [
            ("Netflix", "streaming", "Depenses:Divertissement"),
            ("Spotify", "musique", "Depenses:Divertissement"),
            ("Amazon", "achat en ligne", "Depenses:Fournitures"),
            ("Tim Hortons", "cafe", "Depenses:Repas"),
            ("Shell", "essence", "Depenses:Transport"),
        ]
        ml.entrainer(data)
        assert ml.est_entraine is False

    def test_cold_start_single_account(self):
        """ML avec un seul compte distinct reste non-entraine."""
        ml = PredicteurML()
        data = [
            (f"Vendor {i}", f"achat {i}", "Depenses:Fournitures")
            for i in range(25)
        ]
        ml.entrainer(data)
        assert ml.est_entraine is False

    def test_prediction_with_sufficient_data(self):
        """ML avec assez de donnees retourne un compte et une confiance."""
        ml = PredicteurML()
        data = []
        # 15 entries for Depenses:Repas
        for i in range(15):
            data.append((f"Restaurant {i}", "repas au restaurant", "Depenses:Repas"))
        # 15 entries for Depenses:Transport
        for i in range(15):
            data.append((f"Station {i}", "essence carburant", "Depenses:Transport"))

        ml.entrainer(data)
        assert ml.est_entraine is True

        resultat = ml.predire("Restaurant Nouveau", "repas au restaurant", Decimal("25.00"))
        assert resultat is not None
        assert isinstance(resultat, ResultatML)
        assert resultat.compte in ("Depenses:Repas", "Depenses:Transport")

    def test_confidence_is_float_between_0_and_1(self):
        """La confiance ML est un float entre 0 et 1."""
        ml = PredicteurML()
        data = []
        for i in range(15):
            data.append((f"Restaurant {i}", "repas au restaurant", "Depenses:Repas"))
        for i in range(15):
            data.append((f"Station {i}", "essence carburant", "Depenses:Transport"))

        ml.entrainer(data)
        resultat = ml.predire("Restaurant Test", "repas", Decimal("30.00"))
        assert resultat is not None
        assert isinstance(resultat.confiance, float)
        assert 0.0 <= resultat.confiance <= 1.0

    def test_predire_when_not_trained_returns_none(self):
        """predire() retourne None quand le modele n'est pas entraine."""
        ml = PredicteurML()
        resultat = ml.predire("Test", "test", Decimal("10.00"))
        assert resultat is None
