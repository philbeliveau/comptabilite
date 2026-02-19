"""Tests pour l'extension Fava ApprobationExtension.

Teste l'importabilite, la logique de confiance, le flag gros montant,
et l'integration avec lister_pending() (sans lancer le serveur Fava).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from beancount.parser import parser as beancount_parser

from compteqc.mcp.services import lister_pending


# ---------- Fixtures ----------

LEDGER_AVEC_PENDING = """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2026-01-01 open Actifs:Banque:Desjardins
2026-01-01 open Depenses:Fournitures
2026-01-01 open Depenses:Repas

2026-02-10 ! "Amazon" "Clavier mecanique" #pending
  confiance: "0.97"
  source_ia: "regle"
  compte_propose: "Depenses:Fournitures"
  Depenses:Fournitures  150.00 CAD
  Actifs:Banque:Desjardins  -150.00 CAD

2026-02-11 ! "Restaurant Le Local" "Repas d affaires" #pending
  confiance: "0.82"
  source_ia: "ml"
  compte_propose: "Depenses:Repas"
  Depenses:Repas  85.00 CAD
  Actifs:Banque:Desjardins  -85.00 CAD

2026-02-12 ! "Apple" "MacBook Pro" #pending
  confiance: "0.65"
  source_ia: "llm"
  compte_propose: "Depenses:Fournitures"
  Depenses:Fournitures  3500.00 CAD
  Actifs:Banque:Desjardins  -3500.00 CAD

2026-02-13 * "Client ABC" "Facture consultation"
  Actifs:Banque:Desjardins  5000.00 CAD
  Depenses:Fournitures  -5000.00 CAD
"""


@pytest.fixture
def entries_avec_pending():
    entries, errors, _ = beancount_parser.parse_string(LEDGER_AVEC_PENDING)
    assert not errors, f"Erreurs de parsing: {errors}"
    return entries


# ---------- Test Fava installation ----------


def test_fava_installed():
    """Fava est installe et importable."""
    import fava

    assert fava.__version__


# ---------- Test extension importability ----------


def test_extension_importable():
    """ApprobationExtension est importable."""
    from compteqc.fava_ext.approbation import ApprobationExtension

    assert ApprobationExtension is not None


def test_extension_report_title():
    """Le report_title est correct."""
    from compteqc.fava_ext.approbation import ApprobationExtension

    assert ApprobationExtension.report_title == "File d'approbation"


def test_extension_is_subclass():
    """ApprobationExtension herite de FavaExtensionBase."""
    from fava.ext import FavaExtensionBase

    from compteqc.fava_ext.approbation import ApprobationExtension

    assert issubclass(ApprobationExtension, FavaExtensionBase)


# ---------- Test data layer (lister_pending) ----------


def test_lister_pending_returns_pending_only(entries_avec_pending):
    """lister_pending retourne uniquement les transactions #pending."""
    pending = lister_pending(entries_avec_pending)
    assert len(pending) == 3


def test_lister_pending_fields(entries_avec_pending):
    """Chaque transaction pending contient les champs requis."""
    pending = lister_pending(entries_avec_pending)
    for txn in pending:
        assert "date" in txn
        assert "payee" in txn
        assert "narration" in txn
        assert "confiance" in txn
        assert "source" in txn
        assert "montant" in txn
        assert "compte_propose" in txn


def test_lister_pending_confiance_et_source(entries_avec_pending):
    """Les metadonnees AI sont correctement extraites."""
    pending = lister_pending(entries_avec_pending)

    # Premiere transaction: confiance 0.97, source regle
    assert pending[0]["confiance"] == "0.97"
    assert pending[0]["source"] == "regle"
    assert pending[0]["compte_propose"] == "Depenses:Fournitures"

    # Deuxieme: confiance 0.82, source ml
    assert pending[1]["confiance"] == "0.82"
    assert pending[1]["source"] == "ml"

    # Troisieme: confiance 0.65, source llm
    assert pending[2]["confiance"] == "0.65"
    assert pending[2]["source"] == "llm"


def test_lister_pending_montants(entries_avec_pending):
    """Les montants sont correctement calcules (debit side)."""
    pending = lister_pending(entries_avec_pending)
    assert pending[0]["montant"] == Decimal("150.00")
    assert pending[1]["montant"] == Decimal("85.00")
    assert pending[2]["montant"] == Decimal("3500.00")


# ---------- Test confidence badge logic ----------


def test_niveau_confiance_elevee():
    """Confiance >= 0.95 retourne 'elevee'."""
    from compteqc.fava_ext.approbation import niveau_confiance

    assert niveau_confiance(0.95) == "elevee"
    assert niveau_confiance(1.0) == "elevee"
    assert niveau_confiance(0.99) == "elevee"


def test_niveau_confiance_moderee():
    """Confiance >= 0.80 et < 0.95 retourne 'moderee'."""
    from compteqc.fava_ext.approbation import niveau_confiance

    assert niveau_confiance(0.80) == "moderee"
    assert niveau_confiance(0.94) == "moderee"
    assert niveau_confiance(0.85) == "moderee"


def test_niveau_confiance_revision():
    """Confiance < 0.80 retourne 'revision'."""
    from compteqc.fava_ext.approbation import niveau_confiance

    assert niveau_confiance(0.79) == "revision"
    assert niveau_confiance(0.50) == "revision"
    assert niveau_confiance(0.0) == "revision"


def test_niveau_confiance_boundary():
    """Test des valeurs limites exactes."""
    from compteqc.fava_ext.approbation import niveau_confiance

    assert niveau_confiance(0.95) == "elevee"
    assert niveau_confiance(0.80) == "moderee"
    assert niveau_confiance(0.79) == "revision"


def test_niveau_confiance_string():
    """Confiance en string est convertie en float."""
    from compteqc.fava_ext.approbation import niveau_confiance

    assert niveau_confiance("0.97") == "elevee"
    assert niveau_confiance("0.85") == "moderee"
    assert niveau_confiance("0.50") == "revision"


def test_niveau_confiance_unknown():
    """Valeur non-convertible retourne 'revision'."""
    from compteqc.fava_ext.approbation import niveau_confiance

    assert niveau_confiance("unknown") == "revision"


# ---------- Test $2,000 flagging ----------


def test_est_gros_montant_above():
    """Montant > 2000 est un gros montant."""
    from compteqc.fava_ext.approbation import est_gros_montant

    assert est_gros_montant(Decimal("2000.01")) is True
    assert est_gros_montant(Decimal("3500.00")) is True
    assert est_gros_montant(Decimal("10000")) is True


def test_est_gros_montant_at_threshold():
    """Montant == 2000 n'est PAS un gros montant (strictement superieur)."""
    from compteqc.fava_ext.approbation import est_gros_montant

    assert est_gros_montant(Decimal("2000.00")) is False


def test_est_gros_montant_below():
    """Montant < 2000 n'est pas un gros montant."""
    from compteqc.fava_ext.approbation import est_gros_montant

    assert est_gros_montant(Decimal("1999.99")) is False
    assert est_gros_montant(Decimal("150.00")) is False
    assert est_gros_montant(Decimal("0")) is False


def test_gros_montant_identified_in_pending(entries_avec_pending):
    """Le MacBook a 3500$ est identifie comme gros montant dans pending."""
    from compteqc.fava_ext.approbation import est_gros_montant

    pending = lister_pending(entries_avec_pending)
    gros = [t for t in pending if est_gros_montant(t["montant"])]
    assert len(gros) == 1
    assert gros[0]["payee"] == "Apple"
    assert gros[0]["montant"] == Decimal("3500.00")
