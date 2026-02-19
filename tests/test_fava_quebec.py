"""Tests pour les extensions Fava Quebec.

Verifie l'importabilite, les titres de rapport, l'heritage FavaExtensionBase,
l'existence des templates, l'enregistrement dans main.beancount, et la logique
d'alerte s.15(2).
"""

from pathlib import Path

import pytest
from fava.ext import FavaExtensionBase

from compteqc.fava_ext.approbation import ApprobationExtension
from compteqc.fava_ext.dpa_qc import DpaQCExtension
from compteqc.fava_ext.export_cpa import ExportCPAExtension
from compteqc.fava_ext.paie_qc import PaieQCExtension
from compteqc.fava_ext.pret_actionnaire import PretActionnaireExtension, niveau_alerte_s152
from compteqc.fava_ext.taxes_qc import TaxesQCExtension

# Racine du projet
PROJECT_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Test: report_title correct pour chaque extension
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "cls, expected_title",
    [
        (PaieQCExtension, "Paie Quebec"),
        (TaxesQCExtension, "TPS/TVQ"),
        (DpaQCExtension, "DPA/CCA"),
        (PretActionnaireExtension, "Pret actionnaire"),
        (ExportCPAExtension, "Export CPA"),
    ],
)
def test_report_title(cls, expected_title):
    """Chaque extension a le bon titre de rapport."""
    assert cls.report_title == expected_title


# ---------------------------------------------------------------------------
# Test: toutes les extensions heritent de FavaExtensionBase
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "cls",
    [
        ApprobationExtension,
        PaieQCExtension,
        TaxesQCExtension,
        DpaQCExtension,
        PretActionnaireExtension,
        ExportCPAExtension,
    ],
)
def test_subclass_of_fava_extension_base(cls):
    """Chaque extension est une sous-classe de FavaExtensionBase."""
    assert issubclass(cls, FavaExtensionBase)


# ---------------------------------------------------------------------------
# Test: les templates existent pour chaque extension
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "template_path",
    [
        "src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html",
        "src/compteqc/fava_ext/paie_qc/templates/PaieQCExtension.html",
        "src/compteqc/fava_ext/taxes_qc/templates/TaxesQCExtension.html",
        "src/compteqc/fava_ext/dpa_qc/templates/DpaQCExtension.html",
        "src/compteqc/fava_ext/pret_actionnaire/templates/PretActionnaireExtension.html",
        "src/compteqc/fava_ext/export_cpa/templates/ExportCPAExtension.html",
    ],
)
def test_template_exists(template_path):
    """Le fichier template Jinja2 existe pour chaque extension."""
    full_path = PROJECT_ROOT / template_path
    assert full_path.exists(), f"Template manquant: {full_path}"


# ---------------------------------------------------------------------------
# Test: main.beancount a toutes les directives fava-extension
# ---------------------------------------------------------------------------

def test_main_beancount_has_all_extensions():
    """main.beancount contient 6 directives fava-extension."""
    main_path = PROJECT_ROOT / "ledger" / "main.beancount"
    assert main_path.exists(), "ledger/main.beancount manquant"

    content = main_path.read_text()
    extension_lines = [
        line for line in content.splitlines()
        if 'fava-extension' in line and line.strip().startswith("2010")
    ]
    assert len(extension_lines) == 6, (
        f"Attendu 6 directives fava-extension, trouve {len(extension_lines)}: {extension_lines}"
    )


def test_main_beancount_has_specific_extensions():
    """main.beancount contient les 6 extensions specifiques."""
    main_path = PROJECT_ROOT / "ledger" / "main.beancount"
    content = main_path.read_text()

    expected = [
        "compteqc.fava_ext.approbation",
        "compteqc.fava_ext.paie_qc",
        "compteqc.fava_ext.taxes_qc",
        "compteqc.fava_ext.dpa_qc",
        "compteqc.fava_ext.pret_actionnaire",
        "compteqc.fava_ext.export_cpa",
    ]
    for ext in expected:
        assert ext in content, f"Extension manquante dans main.beancount: {ext}"


# ---------------------------------------------------------------------------
# Test: logique d'alerte s.15(2)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "jours, expected_niveau",
    [
        (365, "normal"),       # Plus de 9 mois
        (300, "normal"),       # Plus de 9 mois
        (271, "normal"),       # Juste au-dessus de 9 mois
        (270, "attention"),    # Exactement 9 mois
        (200, "attention"),    # Entre 6 et 9 mois
        (181, "attention"),    # Juste au-dessus de 6 mois
        (180, "urgent"),       # Exactement 6 mois
        (90, "urgent"),        # Entre 30 jours et 6 mois
        (31, "urgent"),        # Juste au-dessus de 30 jours
        (30, "critique"),      # Exactement 30 jours
        (10, "critique"),      # Moins de 30 jours
        (0, "critique"),       # Jour meme
        (-5, "critique"),      # Depasse
    ],
)
def test_niveau_alerte_s152(jours, expected_niveau):
    """La fonction niveau_alerte_s152 retourne le bon niveau selon les jours restants."""
    assert niveau_alerte_s152(jours) == expected_niveau
