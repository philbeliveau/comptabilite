"""Tests pour le moteur de categorisation par regles YAML."""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.core import data
from beancount.core.data import EMPTY_SET

from compteqc.categorisation import appliquer_categorisation
from compteqc.categorisation.moteur import MoteurRegles
from compteqc.categorisation.regles import ConfigRegles, Regle, ConditionRegle, charger_regles

RULES_DIR = Path(__file__).parent.parent / "rules"

# Set de comptes valides pour les tests
COMPTES_VALIDES = {
    "Depenses:Non-Classe",
    "Depenses:Bureau:Internet-Telecom",
    "Depenses:Bureau:Abonnements-Logiciels",
    "Depenses:Frais-Bancaires",
    "Depenses:Repas-Representation",
    "Revenus:Consultation",
}


# ---------------------------------------------------------------------------
# Tests charger_regles
# ---------------------------------------------------------------------------


class TestChargerRegles:
    def test_charger_fichier_vide(self):
        """Le fichier rules/categorisation.yaml avec regles: [] est valide."""
        config = charger_regles(RULES_DIR / "categorisation.yaml")
        assert isinstance(config, ConfigRegles)
        assert config.regles == []

    def test_charger_regles_valides(self, tmp_path):
        f = tmp_path / "regles.yaml"
        f.write_text(
            """
regles:
  - nom: bell
    condition:
      payee: "BELL"
    compte: "Depenses:Bureau:Internet-Telecom"
    confiance: 0.95
  - nom: github
    condition:
      payee: "GITHUB"
    compte: "Depenses:Bureau:Abonnements-Logiciels"
""",
            encoding="utf-8",
        )
        config = charger_regles(f)
        assert len(config.regles) == 2
        assert config.regles[0].nom == "bell"
        assert config.regles[0].confiance == 0.95
        assert config.regles[1].confiance == 0.9  # default

    def test_charger_fichier_inexistant(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            charger_regles(tmp_path / "inexistant.yaml")

    def test_charger_fichier_invalide(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("regles:\n  - invalid_field: oops\n", encoding="utf-8")
        with pytest.raises(ValueError, match="invalide"):
            charger_regles(f)

    def test_charger_fichier_yaml_none(self, tmp_path):
        """Un fichier YAML vide retourne un ConfigRegles vide."""
        f = tmp_path / "vide.yaml"
        f.write_text("", encoding="utf-8")
        config = charger_regles(f)
        assert config.regles == []


# ---------------------------------------------------------------------------
# Tests MoteurRegles
# ---------------------------------------------------------------------------


def _creer_moteur_avec_regles() -> MoteurRegles:
    """Cree un moteur avec quelques regles de test."""
    config = ConfigRegles(
        regles=[
            Regle(
                nom="bell",
                condition=ConditionRegle(payee="BELL"),
                compte="Depenses:Bureau:Internet-Telecom",
                confiance=0.95,
            ),
            Regle(
                nom="github",
                condition=ConditionRegle(payee="GITHUB"),
                compte="Depenses:Bureau:Abonnements-Logiciels",
                confiance=0.9,
            ),
            Regle(
                nom="frais-bancaires",
                condition=ConditionRegle(payee="FRAIS BANCAIRES"),
                compte="Depenses:Frais-Bancaires",
                confiance=0.99,
            ),
            Regle(
                nom="gros-montant",
                condition=ConditionRegle(montant_min=Decimal("5000")),
                compte="Revenus:Consultation",
                confiance=0.7,
            ),
        ]
    )
    return MoteurRegles(config, COMPTES_VALIDES)


class TestMoteurRegles:
    def test_categorise_bell(self):
        moteur = _creer_moteur_avec_regles()
        resultat = moteur.categoriser("BELL CANADA", "PAIEMENT MENSUEL", Decimal("-125.50"))
        assert resultat.compte == "Depenses:Bureau:Internet-Telecom"
        assert resultat.confiance == 0.95
        assert resultat.regle == "bell"
        assert resultat.source == "regle"

    def test_categorise_github(self):
        moteur = _creer_moteur_avec_regles()
        resultat = moteur.categoriser("Github Inc", "ABONNEMENT", Decimal("-27.00"))
        assert resultat.compte == "Depenses:Bureau:Abonnements-Logiciels"
        assert resultat.regle == "github"

    def test_non_classe_quand_pas_de_regle(self):
        moteur = _creer_moteur_avec_regles()
        resultat = moteur.categoriser("INCONNU XYZ", "ACHAT MYSTERE", Decimal("-50.00"))
        assert resultat.compte == "Depenses:Non-Classe"
        assert resultat.confiance == 0.0
        assert resultat.regle is None
        assert resultat.source == "non-classe"

    def test_non_classe_quand_moteur_vide(self):
        moteur = MoteurRegles(ConfigRegles(), COMPTES_VALIDES)
        resultat = moteur.categoriser("BELL", "PAIEMENT", Decimal("-100"))
        assert resultat.compte == "Depenses:Non-Classe"
        assert resultat.source == "non-classe"

    def test_compte_invalide_retourne_non_classe(self):
        """Un compte de regle qui n'existe pas dans comptes_valides -> non-classe + warning."""
        config = ConfigRegles(
            regles=[
                Regle(
                    nom="mauvais-compte",
                    condition=ConditionRegle(payee="TEST"),
                    compte="Depenses:Inexistant",
                    confiance=0.9,
                ),
            ]
        )
        moteur = MoteurRegles(config, COMPTES_VALIDES)
        resultat = moteur.categoriser("TEST INC", "ACHAT", Decimal("-50"))
        assert resultat.compte == "Depenses:Non-Classe"
        assert resultat.regle == "mauvais-compte"
        assert resultat.source == "non-classe"

    def test_premiere_regle_gagne(self):
        """Les regles sont evaluees dans l'ordre, la premiere qui matche gagne."""
        config = ConfigRegles(
            regles=[
                Regle(
                    nom="regle-a",
                    condition=ConditionRegle(payee="TEST"),
                    compte="Depenses:Frais-Bancaires",
                ),
                Regle(
                    nom="regle-b",
                    condition=ConditionRegle(payee="TEST"),
                    compte="Depenses:Bureau:Internet-Telecom",
                ),
            ]
        )
        moteur = MoteurRegles(config, COMPTES_VALIDES)
        resultat = moteur.categoriser("TEST", "SOMETHING", Decimal("-10"))
        assert resultat.regle == "regle-a"
        assert resultat.compte == "Depenses:Frais-Bancaires"

    def test_montant_min_filtre(self):
        moteur = _creer_moteur_avec_regles()
        # Montant sous le seuil de la regle gros-montant
        resultat = moteur.categoriser("RANDOM", "VIREMENT", Decimal("4999"))
        assert resultat.compte == "Depenses:Non-Classe"

    def test_montant_min_matche(self):
        moteur = _creer_moteur_avec_regles()
        # Montant au-dessus du seuil
        resultat = moteur.categoriser("RANDOM", "VIREMENT", Decimal("8500"))
        assert resultat.compte == "Revenus:Consultation"
        assert resultat.regle == "gros-montant"


# ---------------------------------------------------------------------------
# Tests appliquer_categorisation
# ---------------------------------------------------------------------------


def _creer_transaction(payee: str, narration: str, montant: Decimal) -> data.Transaction:
    """Helper pour creer une transaction de test."""
    meta = data.new_metadata("test.py", 0, {"categorisation": "non-classe"})
    return data.Transaction(
        meta=meta,
        date=datetime.date(2026, 1, 15),
        flag="!",
        payee=payee,
        narration=narration,
        tags=EMPTY_SET,
        links=EMPTY_SET,
        postings=[
            data.Posting(
                account="Actifs:Banque:RBC:Cheques",
                units=data.Amount(montant, "CAD"),
                cost=None,
                price=None,
                flag=None,
                meta=None,
            ),
            data.Posting(
                account="Depenses:Non-Classe",
                units=data.Amount(-montant, "CAD"),
                cost=None,
                price=None,
                flag=None,
                meta=None,
            ),
        ],
    )


class TestAppliquerCategorisation:
    def test_categorise_transactions(self):
        moteur = _creer_moteur_avec_regles()
        txns = [
            _creer_transaction("BELL CANADA", "PAIEMENT MENSUEL", Decimal("-125.50")),
            _creer_transaction("INCONNU", "ACHAT", Decimal("-50")),
        ]
        resultat = appliquer_categorisation(txns, moteur)
        assert len(resultat) == 2

        # Bell categorise
        assert resultat[0].postings[1].account == "Depenses:Bureau:Internet-Telecom"
        assert resultat[0].meta["categorisation"] == "regle"
        assert resultat[0].meta["regle"] == "bell"

        # Inconnu reste non-classe
        assert resultat[1].postings[1].account == "Depenses:Non-Classe"
        assert resultat[1].meta["categorisation"] == "non-classe"

    def test_ne_mute_pas_originaux(self):
        """Les transactions originales ne doivent pas etre modifiees."""
        moteur = _creer_moteur_avec_regles()
        original = _creer_transaction("BELL CANADA", "PAIEMENT", Decimal("-125.50"))
        original_meta_copy = dict(original.meta)
        original_posting_account = original.postings[1].account

        resultat = appliquer_categorisation([original], moteur)

        # L'original n'a pas change
        assert original.meta["categorisation"] == original_meta_copy["categorisation"]
        assert original.postings[1].account == original_posting_account
        assert original.postings[1].account == "Depenses:Non-Classe"

        # Le resultat est different
        assert resultat[0].postings[1].account == "Depenses:Bureau:Internet-Telecom"

    def test_ignore_transactions_deja_classees(self):
        """Les transactions deja categorisees ne sont pas re-categorisees."""
        moteur = _creer_moteur_avec_regles()
        txn = _creer_transaction("BELL CANADA", "PAIEMENT", Decimal("-125.50"))
        # Simuler une transaction deja classee
        txn.meta["categorisation"] = "regle"

        resultat = appliquer_categorisation([txn], moteur)
        # Pas de changement -- la transaction garde son posting original
        assert resultat[0].postings[1].account == "Depenses:Non-Classe"

    def test_postings_balancent_apres_categorisation(self):
        moteur = _creer_moteur_avec_regles()
        txns = [
            _creer_transaction("BELL CANADA", "PAIEMENT", Decimal("-125.50")),
        ]
        resultat = appliquer_categorisation(txns, moteur)
        for txn in resultat:
            total = sum(p.units.number for p in txn.postings)
            assert total == Decimal("0")
