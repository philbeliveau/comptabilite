"""Tests pour le pipeline de categorisation a trois niveaux."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from compteqc.categorisation.capex import DetecteurCAPEX
from compteqc.categorisation.ml import PredicteurML, ResultatML
from compteqc.categorisation.moteur import MoteurRegles, ResultatCategorisation
from compteqc.categorisation.pipeline import PipelineCategorisation, ResultatPipeline


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


# --- Pipeline Orchestrator Tests ---


def _make_moteur_regle(compte: str | None = None) -> MagicMock:
    """Cree un mock MoteurRegles qui retourne un resultat specifique."""
    moteur = MagicMock(spec=MoteurRegles)
    if compte:
        moteur.categoriser.return_value = ResultatCategorisation(
            compte=compte, confiance=1.0, regle="test-rule", source="regle"
        )
    else:
        moteur.categoriser.return_value = ResultatCategorisation(
            compte="Depenses:Non-Classe", confiance=0.0, regle=None, source="non-classe"
        )
    return moteur


def _make_ml(compte: str | None = None, confiance: float = 0.9) -> MagicMock:
    """Cree un mock PredicteurML."""
    ml = MagicMock(spec=PredicteurML)
    if compte:
        ml.est_entraine = True
        ml.predire.return_value = ResultatML(compte=compte, confiance=confiance)
    else:
        ml.est_entraine = False
        ml.predire.return_value = None
    return ml


def _make_llm(compte: str | None = None, confiance: float = 0.85) -> MagicMock | None:
    """Cree un mock classificateur LLM."""
    if compte is None:
        return None
    llm = MagicMock()
    llm.classifier.return_value = MagicMock(compte=compte, confiance=confiance)
    return llm


class TestPipelineCategorisation:
    """Tests pour le pipeline de categorisation orchestrateur."""

    def test_rule_match_bypasses_ml_llm(self):
        """Une regle qui matche court-circuite ML et LLM, confiance=1.0."""
        moteur = _make_moteur_regle("Depenses:Repas")
        ml = _make_ml("Depenses:Transport", 0.9)
        capex = DetecteurCAPEX()

        pipeline = PipelineCategorisation(moteur, ml, None, capex)
        result = pipeline.categoriser("Tim Hortons", "cafe", Decimal("5.00"))

        assert result.compte == "Depenses:Repas"
        assert result.confiance == 1.0
        assert result.source == "regle"
        assert result.regle == "test-rule"
        # ML should NOT have been called
        ml.predire.assert_not_called()

    def test_ml_only_high_confidence_direct(self):
        """ML seul avec >95% -> destination 'direct'."""
        moteur = _make_moteur_regle()  # no match
        ml = _make_ml("Depenses:Repas", 0.97)
        capex = DetecteurCAPEX()

        pipeline = PipelineCategorisation(moteur, ml, None, capex)
        result = pipeline.categoriser("Restaurant", "repas", Decimal("25.00"))

        assert result.compte == "Depenses:Repas"
        assert result.confiance == 0.97
        assert result.source == "ml"
        assert pipeline.determiner_destination(result) == "direct"

    def test_ml_only_medium_confidence_pending(self):
        """ML seul avec 85% -> destination 'pending'."""
        moteur = _make_moteur_regle()
        ml = _make_ml("Depenses:Repas", 0.85)
        capex = DetecteurCAPEX()

        pipeline = PipelineCategorisation(moteur, ml, None, capex)
        result = pipeline.categoriser("Restaurant", "repas", Decimal("25.00"))

        assert result.confiance == 0.85
        assert pipeline.determiner_destination(result) == "pending"

    def test_ml_only_low_confidence_revue(self):
        """ML seul avec 70% -> destination 'revue'."""
        moteur = _make_moteur_regle()
        ml = _make_ml("Depenses:Repas", 0.70)
        capex = DetecteurCAPEX()

        pipeline = PipelineCategorisation(moteur, ml, None, capex)
        result = pipeline.categoriser("Restaurant", "repas", Decimal("25.00"))

        assert result.confiance == 0.70
        assert result.revue_obligatoire is True
        assert pipeline.determiner_destination(result) == "revue"

    def test_ml_llm_agreement_uses_higher_confidence(self):
        """ML et LLM d'accord -> utilise la confiance la plus haute."""
        moteur = _make_moteur_regle()
        ml = _make_ml("Depenses:Repas", 0.88)
        llm = _make_llm("Depenses:Repas", 0.92)
        capex = DetecteurCAPEX()

        pipeline = PipelineCategorisation(moteur, ml, llm, capex)
        result = pipeline.categoriser("Restaurant", "repas", Decimal("25.00"))

        assert result.compte == "Depenses:Repas"
        assert result.confiance == 0.92  # higher of the two

    def test_ml_llm_disagreement_forces_revue(self):
        """ML et LLM en desaccord -> revue_obligatoire, suggestions preservees."""
        moteur = _make_moteur_regle()
        ml = _make_ml("Depenses:Repas", 0.85)
        llm = _make_llm("Depenses:Divertissement", 0.80)
        capex = DetecteurCAPEX()

        pipeline = PipelineCategorisation(moteur, ml, llm, capex)
        result = pipeline.categoriser("Cinema", "film", Decimal("15.00"))

        assert result.revue_obligatoire is True
        assert result.suggestions is not None
        assert "ml" in result.suggestions
        assert "llm" in result.suggestions
        assert result.suggestions["ml"] == ("Depenses:Repas", 0.85)
        assert result.suggestions["llm"] == ("Depenses:Divertissement", 0.80)

    def test_no_ml_no_llm_non_classe(self):
        """Sans ML ni LLM, et pas de regle -> non-classe."""
        moteur = _make_moteur_regle()
        capex = DetecteurCAPEX()

        pipeline = PipelineCategorisation(moteur, None, None, capex)
        result = pipeline.categoriser("Inconnu", "transaction", Decimal("50.00"))

        assert result.source == "non-classe"
        assert result.confiance == 0.0

    def test_cold_start_ml_untrained_no_llm(self):
        """ML non entraine, pas de LLM -> non-classe."""
        moteur = _make_moteur_regle()
        ml = _make_ml()  # untrained
        capex = DetecteurCAPEX()

        pipeline = PipelineCategorisation(moteur, ml, None, capex)
        result = pipeline.categoriser("Test", "test", Decimal("10.00"))

        assert result.source == "non-classe"
        assert result.confiance == 0.0

    def test_capex_flag_set_on_qualifying_transaction(self):
        """CAPEX est signale sur les transactions qualifiantes."""
        moteur = _make_moteur_regle()
        ml = _make_ml("Depenses:Informatique", 0.92)
        capex = DetecteurCAPEX()

        pipeline = PipelineCategorisation(moteur, ml, None, capex)
        result = pipeline.categoriser("Apple Store", "MacBook Pro laptop", Decimal("2500.00"))

        assert result.est_capex is True
        assert result.classe_dpa == 50

    def test_capex_forces_pending_destination(self):
        """CAPEX force la destination 'pending' meme avec haute confiance."""
        moteur = _make_moteur_regle()
        ml = _make_ml("Depenses:Informatique", 0.98)
        capex = DetecteurCAPEX()

        pipeline = PipelineCategorisation(moteur, ml, None, capex)
        result = pipeline.categoriser("Dell", "serveur informatique", Decimal("3000.00"))

        assert result.est_capex is True
        assert pipeline.determiner_destination(result) == "pending"

    def test_rule_match_with_capex(self):
        """Regle matche ET CAPEX -> source regle mais capex signale."""
        moteur = _make_moteur_regle("Depenses:Informatique")
        capex = DetecteurCAPEX()

        pipeline = PipelineCategorisation(moteur, None, None, capex)
        result = pipeline.categoriser("Apple", "MacBook Pro", Decimal("2500.00"))

        assert result.source == "regle"
        assert result.confiance == 1.0
        assert result.est_capex is True
        assert result.classe_dpa == 50
