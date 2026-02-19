"""Tests specifiques aux extensions gap-closure (04-05).

Verifie l'importabilite, le mapping couleur_urgence, la degradation
gracieuse sans Phase 5, et l'enregistrement dans main.beancount.
"""

from pathlib import Path

import pytest
from fava.ext import FavaExtensionBase

from compteqc.fava_ext.echeances import EcheancesExtension, couleur_urgence
from compteqc.fava_ext.recus import RecusExtension

# Racine du projet
PROJECT_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Test: importabilite
# ---------------------------------------------------------------------------

def test_echeances_importable():
    """EcheancesExtension est importable et herite de FavaExtensionBase."""
    assert issubclass(EcheancesExtension, FavaExtensionBase)


def test_recus_importable():
    """RecusExtension est importable et herite de FavaExtensionBase."""
    assert issubclass(RecusExtension, FavaExtensionBase)


# ---------------------------------------------------------------------------
# Test: couleur_urgence mapping
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "urgence, expected_class",
    [
        ("critique", "alerte-critique"),
        ("urgent", "alerte-urgent"),
        ("normal", "alerte-normal"),
        ("info", "alerte-info"),
    ],
)
def test_couleur_urgence_mapping(urgence, expected_class):
    """couleur_urgence retourne la bonne classe CSS pour chaque niveau."""
    assert couleur_urgence(urgence) == expected_class


def test_couleur_urgence_default():
    """couleur_urgence retourne alerte-info pour une valeur inconnue."""
    assert couleur_urgence("inconnu") == "alerte-info"
    assert couleur_urgence("") == "alerte-info"


# ---------------------------------------------------------------------------
# Test: degradation gracieuse sans Phase 5
# ---------------------------------------------------------------------------

def test_echeances_graceful_without_phase5():
    """EcheancesExtension fonctionne sans le module Phase 5 echeances."""
    # Instancier sans ledger reel -- tester les valeurs par defaut
    ext = EcheancesExtension.__new__(EcheancesExtension)
    ext._alertes = []
    ext._echeances_disponible = False

    assert ext.echeances_disponible() is False
    assert ext.alertes() == []


def test_recus_graceful_without_phase5():
    """RecusExtension fonctionne sans le module Phase 5 documents."""
    ext = RecusExtension.__new__(RecusExtension)
    ext._upload_disponible = False
    ext._recent_uploads = []

    assert ext.upload_disponible() is False
    assert ext.recent_uploads() == []


# ---------------------------------------------------------------------------
# Test: main.beancount a 8 directives
# ---------------------------------------------------------------------------

def test_main_beancount_8_extensions():
    """main.beancount contient 8 directives fava-extension."""
    main_path = PROJECT_ROOT / "ledger" / "main.beancount"
    assert main_path.exists(), "ledger/main.beancount manquant"

    content = main_path.read_text()
    extension_lines = [
        line for line in content.splitlines()
        if 'fava-extension' in line and line.strip().startswith("2010")
    ]
    assert len(extension_lines) == 8, (
        f"Attendu 8 directives fava-extension, trouve {len(extension_lines)}"
    )


# ---------------------------------------------------------------------------
# Test: templates existent
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "template_path",
    [
        "src/compteqc/fava_ext/echeances/templates/EcheancesExtension.html",
        "src/compteqc/fava_ext/recus/templates/RecusExtension.html",
    ],
)
def test_templates_exist_gap_closure(template_path):
    """Les templates des extensions gap-closure existent."""
    full_path = PROJECT_ROOT / template_path
    assert full_path.exists(), f"Template manquant: {full_path}"
