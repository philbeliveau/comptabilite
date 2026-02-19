"""Tests pour le classificateur LLM (toutes les interactions API sont mockees)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from compteqc.categorisation.llm import (
    ClassificateurLLM,
    ResultatLLM,
)

COMPTES_VALIDES = [
    "Depenses:Repas",
    "Depenses:Transport",
    "Depenses:Bureau:Fournitures",
    "Depenses:Informatique",
    "Depenses:Non-Classe",
]


@pytest.fixture
def chemin_log(tmp_path):
    return tmp_path / "llm_log" / "categorisations.jsonl"


@pytest.fixture
def classificateur(chemin_log):
    return ClassificateurLLM(
        comptes_valides=COMPTES_VALIDES,
        chemin_log=chemin_log,
    )


def _make_mock_response(compte: str, confiance: float, raisonnement: str, est_capex: bool = False):
    """Cree un mock de reponse OpenAI ChatCompletion."""
    content_json = json.dumps({
        "compte": compte,
        "confiance": confiance,
        "raisonnement": raisonnement,
        "est_capex": est_capex,
    })
    message = MagicMock()
    message.content = content_json

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    response.usage = MagicMock(prompt_tokens=150, completion_tokens=50)
    return response


class TestClassificateurLLM:
    """Tests pour ClassificateurLLM."""

    def test_classification_valide(self, classificateur, chemin_log):
        """Classification avec compte valide retourne ResultatLLM correct."""
        mock_response = _make_mock_response(
            "Depenses:Repas", 0.92, "Restaurant typique"
        )

        with patch.object(classificateur, "_get_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            resultat = classificateur.classifier("Tim Hortons", "cafe", Decimal("5.50"))

        assert isinstance(resultat, ResultatLLM)
        assert resultat.compte == "Depenses:Repas"
        assert resultat.confiance == 0.92
        assert resultat.raisonnement == "Restaurant typique"
        assert resultat.est_capex is False

    def test_compte_invalide_fallback_non_classe(self, classificateur):
        """Compte invalide retourne par LLM -> fallback a Non-Classe avec confiance 0.1."""
        mock_response = _make_mock_response(
            "Depenses:CompteInvente", 0.85, "Pas dans la liste"
        )

        with patch.object(classificateur, "_get_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            resultat = classificateur.classifier("Inconnu", "achat", Decimal("100.00"))

        assert resultat.compte == "Depenses:Non-Classe"
        assert resultat.confiance == 0.1
        assert "invalide" in resultat.raisonnement.lower()

    def test_capex_flag_preserved(self, classificateur):
        """Flag est_capex est preserve quand le LLM le retourne."""
        mock_response = _make_mock_response(
            "Depenses:Informatique", 0.95, "Achat ordinateur", est_capex=True
        )

        with patch.object(classificateur, "_get_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            resultat = classificateur.classifier("Apple", "MacBook Pro", Decimal("2500.00"))

        assert resultat.est_capex is True
        assert resultat.compte == "Depenses:Informatique"

    def test_jsonl_log_created(self, classificateur, chemin_log):
        """Le fichier JSONL est cree et contient les champs attendus."""
        mock_response = _make_mock_response("Depenses:Repas", 0.9, "Cafe")

        with patch.object(classificateur, "_get_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            classificateur.classifier("Tim Hortons", "cafe", Decimal("5.50"))

        assert chemin_log.exists()
        lines = chemin_log.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["payee"] == "Tim Hortons"
        assert entry["narration"] == "cafe"
        assert entry["montant"] == "5.50"
        assert entry["modele"] == "anthropic/claude-sonnet-4"
        assert entry["compte"] == "Depenses:Repas"
        assert entry["confiance"] == 0.9
        assert "prompt_hash" in entry
        assert "timestamp" in entry
        assert entry["tokens_utilises"] == 200  # 150 prompt + 50 completion

    def test_jsonl_log_multiple_entries(self, classificateur, chemin_log):
        """Plusieurs classifications s'ajoutent au meme fichier JSONL."""
        mock_response = _make_mock_response("Depenses:Repas", 0.9, "Cafe")

        with patch.object(classificateur, "_get_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            classificateur.classifier("Tim Hortons", "cafe", Decimal("5.50"))
            classificateur.classifier("Starbucks", "latte", Decimal("6.00"))

        lines = chemin_log.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_est_disponible_with_key(self, classificateur):
        """est_disponible retourne True quand OPENROUTER_API_KEY est defini."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-fake"}):
            assert classificateur.est_disponible is True

    def test_est_disponible_without_key(self, classificateur):
        """est_disponible retourne False quand OPENROUTER_API_KEY n'est pas defini."""
        with patch.dict("os.environ", {}, clear=True):
            assert classificateur.est_disponible is False

    def test_api_error_returns_non_classe(self, classificateur):
        """Erreur API retourne Non-Classe avec confiance 0."""
        with patch.object(classificateur, "_get_client") as mock_client:
            mock_client.return_value.chat.completions.create.side_effect = Exception("Network error")

            resultat = classificateur.classifier("Test", "test", Decimal("10.00"))

        assert resultat.compte == "Depenses:Non-Classe"
        assert resultat.confiance == 0.0
        assert resultat.raisonnement == "Erreur API"
        assert resultat.est_capex is False

    def test_historique_vendeur_in_prompt(self, classificateur):
        """L'historique vendeur est inclus dans le prompt."""
        mock_response = _make_mock_response("Depenses:Repas", 0.9, "Cafe")

        with patch.object(classificateur, "_get_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            classificateur.classifier(
                "Tim Hortons",
                "cafe",
                Decimal("5.50"),
                historique_vendeur=[
                    {"compte": "Depenses:Repas", "confiance": 0.95},
                ],
            )

        call_args = mock_client.return_value.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        prompt_content = messages[1]["content"]
        assert "HISTORIQUE DE CE VENDEUR" in prompt_content
        assert "Depenses:Repas" in prompt_content

    def test_transactions_similaires_in_prompt(self, classificateur):
        """Les transactions similaires sont incluses dans le prompt."""
        mock_response = _make_mock_response("Depenses:Repas", 0.9, "Cafe")

        with patch.object(classificateur, "_get_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            classificateur.classifier(
                "Tim Hortons",
                "cafe",
                Decimal("5.50"),
                transactions_similaires=[
                    {"payee": "Starbucks", "narration": "latte", "compte": "Depenses:Repas"},
                ],
            )

        call_args = mock_client.return_value.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        prompt_content = messages[1]["content"]
        assert "TRANSACTIONS SIMILAIRES" in prompt_content
        assert "Starbucks" in prompt_content

    def test_comptes_valides_in_prompt(self, classificateur):
        """La liste des comptes valides est incluse dans le prompt."""
        mock_response = _make_mock_response("Depenses:Repas", 0.9, "Cafe")

        with patch.object(classificateur, "_get_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            classificateur.classifier("Test", "test", Decimal("10.00"))

        call_args = mock_client.return_value.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        prompt_content = messages[1]["content"]
        assert "COMPTES VALIDES" in prompt_content
        assert "Depenses:Repas" in prompt_content
        assert "Depenses:Transport" in prompt_content
