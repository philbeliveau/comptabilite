"""Tests pour le module de feedback et auto-generation de regles."""

from __future__ import annotations

import json
import re

import pytest

from compteqc.categorisation.feedback import (
    SEUIL_AUTO_REGLE,
    ajouter_regle_auto,
    charger_historique,
    enregistrer_correction,
)
from compteqc.categorisation.regles import ConditionRegle, Regle


class TestEnregistrerCorrection:
    """Tests pour enregistrer_correction."""

    def test_premiere_correction_pas_de_regle(self, tmp_path):
        """La premiere correction ne genere pas de regle."""
        chemin = tmp_path / "historique.json"

        result = enregistrer_correction(
            chemin, "Tim Hortons", "Depenses:Repas-Representation"
        )

        assert result is None

    def test_deuxieme_correction_identique_genere_regle(self, tmp_path):
        """Apres 2 corrections identiques, une regle est generee."""
        chemin = tmp_path / "historique.json"

        enregistrer_correction(chemin, "Tim Hortons", "Depenses:Repas-Representation")
        result = enregistrer_correction(
            chemin, "Tim Hortons", "Depenses:Repas-Representation"
        )

        assert result is not None
        assert isinstance(result, Regle)
        assert result.compte == "Depenses:Repas-Representation"
        assert result.confiance == 0.95
        assert result.nom.startswith("auto-")

    def test_compte_different_meme_vendeur_pas_de_regle(self, tmp_path):
        """Des corrections vers des comptes differents ne declenchent pas de regle."""
        chemin = tmp_path / "historique.json"

        enregistrer_correction(chemin, "Tim Hortons", "Depenses:Repas-Representation")
        result = enregistrer_correction(chemin, "Tim Hortons", "Depenses:Divers")

        assert result is None

    def test_regle_generee_a_pattern_regex_correct(self, tmp_path):
        """La regle generee a un pattern regex correct (escape des caracteres speciaux)."""
        chemin = tmp_path / "historique.json"

        enregistrer_correction(chemin, "Tim Hortons (123)", "Depenses:Repas-Representation")
        result = enregistrer_correction(
            chemin, "Tim Hortons (123)", "Depenses:Repas-Representation"
        )

        assert result is not None
        # Le pattern doit etre echape (parentheses -> \( \))
        assert r"\(" in result.condition.payee
        assert r"\)" in result.condition.payee
        # Mais il doit quand meme matcher le texte original
        assert re.search(result.condition.payee, "Tim Hortons (123)")

    def test_historique_persiste(self, tmp_path):
        """L'historique persiste entre les appels."""
        chemin = tmp_path / "historique.json"

        enregistrer_correction(chemin, "Tim Hortons", "Depenses:Repas-Representation")

        # Recharger l'historique
        historique = charger_historique(chemin)
        assert "TIM HORTONS" in historique
        assert historique["TIM HORTONS"]["comptes"]["Depenses:Repas-Representation"] == 1

    def test_notes_stockees(self, tmp_path):
        """Les notes sont stockees avec les corrections."""
        chemin = tmp_path / "historique.json"

        enregistrer_correction(
            chemin,
            "Tim Hortons",
            "Depenses:Repas-Representation",
            compte_original="Depenses:Divers",
            note="Toujours des repas chez Tim",
        )

        historique = charger_historique(chemin)
        notes = historique["TIM HORTONS"]["notes"]
        assert len(notes) == 1
        assert notes[0]["note"] == "Toujours des repas chez Tim"
        assert notes[0]["compte_original"] == "Depenses:Divers"
        assert notes[0]["compte_corrige"] == "Depenses:Repas-Representation"

    def test_correction_sans_note_pas_de_note_ajoutee(self, tmp_path):
        """Sans note, la liste des notes reste vide."""
        chemin = tmp_path / "historique.json"

        enregistrer_correction(chemin, "Tim Hortons", "Depenses:Repas-Representation")

        historique = charger_historique(chemin)
        assert historique["TIM HORTONS"]["notes"] == []

    def test_normalisation_vendeur(self, tmp_path):
        """Le nom du vendeur est normalise (uppercase + strip)."""
        chemin = tmp_path / "historique.json"

        enregistrer_correction(chemin, "  tim hortons  ", "Depenses:Repas-Representation")
        result = enregistrer_correction(
            chemin, "TIM HORTONS", "Depenses:Repas-Representation"
        )

        # Les deux doivent matcher -> regle generee
        assert result is not None

    def test_seuil_est_deux(self):
        """Le seuil par defaut est 2."""
        assert SEUIL_AUTO_REGLE == 2


class TestChargerHistorique:
    """Tests pour charger_historique."""

    def test_fichier_inexistant_retourne_vide(self, tmp_path):
        """Un fichier inexistant retourne un dict vide."""
        result = charger_historique(tmp_path / "inexistant.json")
        assert result == {}

    def test_fichier_vide_retourne_vide(self, tmp_path):
        """Un fichier vide retourne un dict vide."""
        chemin = tmp_path / "historique.json"
        chemin.write_text("", encoding="utf-8")
        result = charger_historique(chemin)
        assert result == {}


class TestAjouterRegleAuto:
    """Tests pour ajouter_regle_auto."""

    def test_ajouter_regle_nouveau_fichier(self, tmp_path):
        """Ajouter une regle cree le fichier YAML si necessaire."""
        chemin = tmp_path / "rules" / "categorisation.yaml"
        regle = Regle(
            nom="auto-tim-hortons",
            condition=ConditionRegle(payee="Tim Hortons"),
            compte="Depenses:Repas-Representation",
            confiance=0.95,
        )

        ajouter_regle_auto(chemin, regle)

        assert chemin.exists()
        contenu = chemin.read_text(encoding="utf-8")
        assert "auto-tim-hortons" in contenu
        assert "Depenses:Repas-Representation" in contenu

    def test_doublon_pas_ajoute(self, tmp_path):
        """Une regle avec le meme pattern payee n'est pas ajoutee en double."""
        chemin = tmp_path / "categorisation.yaml"
        regle = Regle(
            nom="auto-tim-hortons",
            condition=ConditionRegle(payee="Tim Hortons"),
            compte="Depenses:Repas-Representation",
            confiance=0.95,
        )

        ajouter_regle_auto(chemin, regle)
        ajouter_regle_auto(chemin, regle)  # Doublon

        import yaml

        donnees = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        assert len(donnees["regles"]) == 1

    def test_ajouter_regle_fichier_existant(self, tmp_path):
        """Ajouter une regle a un fichier avec des regles existantes."""
        chemin = tmp_path / "categorisation.yaml"
        import yaml

        donnees_initiales = {
            "regles": [
                {
                    "nom": "existante",
                    "condition": {"payee": "Shell"},
                    "compte": "Depenses:Deplacement:Transport",
                    "confiance": 0.9,
                }
            ]
        }
        chemin.write_text(yaml.dump(donnees_initiales), encoding="utf-8")

        regle = Regle(
            nom="auto-tim-hortons",
            condition=ConditionRegle(payee="Tim Hortons"),
            compte="Depenses:Repas-Representation",
            confiance=0.95,
        )

        ajouter_regle_auto(chemin, regle)

        donnees = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        assert len(donnees["regles"]) == 2

    def test_ajouter_regle_fichier_vide(self, tmp_path):
        """Ajouter une regle a un fichier YAML vide fonctionne."""
        chemin = tmp_path / "categorisation.yaml"
        chemin.write_text("", encoding="utf-8")

        regle = Regle(
            nom="auto-test",
            condition=ConditionRegle(payee="Test"),
            compte="Depenses:Divers",
            confiance=0.95,
        )

        ajouter_regle_auto(chemin, regle)

        import yaml

        donnees = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        assert len(donnees["regles"]) == 1
