"""Tests pour le package CPA: verification fin d'exercice, orchestrateur et CLI.

Couvre le checklist de verification (6 checks), le generateur de package ZIP,
et les commandes CLI cqc cpa export / cqc cpa verifier.
"""

from __future__ import annotations

import csv
import os
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.parser.parser import parse_string

from compteqc.echeances.verification import (
    Severite,
    VerificationResult,
    verifier_fin_exercice,
)
from compteqc.rapports.cpa_package import (
    CpaPackageError,
    generer_package_cpa,
)


# ---------------------------------------------------------------------------
# Fixture: well-formed test ledger
# ---------------------------------------------------------------------------

BEANCOUNT_BALANCED = """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2025-01-01 open Actifs:Banque:RBC CAD
  gifi: "1001"

2025-01-01 open Passifs:CartesCredit CAD
  gifi: "2700"

2025-01-01 open Passifs:TPS-Percue CAD
2025-01-01 open Passifs:TVQ-Percue CAD
2025-01-01 open Actifs:TPS-Payee CAD
2025-01-01 open Actifs:TVQ-Payee CAD

2025-01-01 open Capital:Actions CAD
  gifi: "3500"

2025-01-01 open Revenus:Consultation CAD
  gifi: "8000"

2025-01-01 open Depenses:Bureau:Loyer CAD
  gifi: "8810"

2025-01-01 open Depenses:Salaires:Brut CAD
  gifi: "8960"

2025-01-01 open Passifs:Pret-Actionnaire CAD

; Mise de fonds
2025-01-01 * "Apport" "Mise de fonds initiale"
  Actifs:Banque:RBC  50000.00 CAD
  Capital:Actions  -50000.00 CAD

; Revenu
2025-02-01 * "Client" "Consultation"
  Actifs:Banque:RBC  10000.00 CAD
  Revenus:Consultation  -10000.00 CAD

; Depense loyer
2025-02-01 * "Proprio" "Loyer"
  Depenses:Bureau:Loyer  1000.00 CAD
  Actifs:Banque:RBC  -1000.00 CAD

; Paie
2025-02-28 * "Paie" "Salaire" #paie
  Depenses:Salaires:Brut  3000.00 CAD
  Actifs:Banque:RBC  -3000.00 CAD
"""

BEANCOUNT_UNBALANCED = """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2025-01-01 open Actifs:Banque:RBC CAD
  gifi: "1001"

2025-01-01 open Capital:Actions CAD
  gifi: "3500"

2025-01-01 open Revenus:Consultation CAD
  gifi: "8000"

2025-01-01 * "Apport" "Mise de fonds"
  Actifs:Banque:RBC  10000.00 CAD
  Capital:Actions  -10000.00 CAD
"""

BEANCOUNT_WITH_NON_CLASSE = """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2025-01-01 open Actifs:Banque:RBC CAD
  gifi: "1001"

2025-01-01 open Capital:Actions CAD
  gifi: "3500"

2025-01-01 open Depenses:Non-Classe CAD

2025-01-01 * "Apport" "Mise de fonds"
  Actifs:Banque:RBC  5000.00 CAD
  Capital:Actions  -5000.00 CAD

2025-03-15 * "Inconnu" "Transaction mystere"
  Depenses:Non-Classe  100.00 CAD
  Actifs:Banque:RBC  -100.00 CAD
"""

BEANCOUNT_WITH_PENDING = """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2025-01-01 open Actifs:Banque:RBC CAD
  gifi: "1001"

2025-01-01 open Capital:Actions CAD
  gifi: "3500"

2025-01-01 open Depenses:Bureau:Loyer CAD
  gifi: "8810"

2025-01-01 * "Apport" "Mise de fonds"
  Actifs:Banque:RBC  5000.00 CAD
  Capital:Actions  -5000.00 CAD

2025-03-15 ! "Proprio" "Loyer en attente"
  Depenses:Bureau:Loyer  500.00 CAD
  Actifs:Banque:RBC  -500.00 CAD
"""


@pytest.fixture
def balanced_entries():
    entries, errors, _ = parse_string(BEANCOUNT_BALANCED)
    assert not errors, f"Parse errors: {errors}"
    return entries


@pytest.fixture
def unbalanced_entries():
    """Entries that will fail GIFI check when we inject an imbalance."""
    entries, errors, _ = parse_string(BEANCOUNT_UNBALANCED)
    assert not errors, f"Parse errors: {errors}"
    return entries


@pytest.fixture
def non_classe_entries():
    entries, errors, _ = parse_string(BEANCOUNT_WITH_NON_CLASSE)
    assert not errors, f"Parse errors: {errors}"
    return entries


@pytest.fixture
def pending_entries():
    entries, errors, _ = parse_string(BEANCOUNT_WITH_PENDING)
    assert not errors, f"Parse errors: {errors}"
    return entries


@pytest.fixture
def weasyprint_available():
    """Skip test if WeasyPrint system libs not available."""
    try:
        if "DYLD_FALLBACK_LIBRARY_PATH" not in os.environ:
            homebrew_lib = "/opt/homebrew/lib"
            if Path(homebrew_lib).exists():
                os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = homebrew_lib
        from weasyprint import HTML  # noqa: F401
    except OSError:
        pytest.skip("WeasyPrint system libraries (pango/gobject) not available")


# ===========================================================================
# Tests: Verification fin d'exercice
# ===========================================================================


class TestVerification:
    """Tests pour le checklist de fin d'exercice."""

    def test_verification_balanced_passes(self, balanced_entries):
        """Toutes les verifications passent sur un ledger bien forme."""
        resultats = verifier_fin_exercice(balanced_entries, 2025)
        assert len(resultats) == 6
        # Aucune erreur fatale
        fatals = [r for r in resultats if r.severite == Severite.ERROR]
        assert len(fatals) == 0

    def test_verification_unbalanced_fails(self, balanced_entries):
        """Verification de l'equation echoue sur un ledger desequilibre."""
        # Inject a phantom entry to break the equation
        from beancount.core.data import Transaction, TxnPosting
        from beancount.core.amount import Amount
        from beancount.core.number import D
        import datetime

        # We'll modify the soldes check by adding a fake account balance
        # Actually, we test via the GIFI validation with injected imbalance
        from compteqc.mcp.services import calculer_soldes
        from compteqc.rapports.gifi_export import extract_gifi_map, validate_gifi

        soldes = calculer_soldes(balanced_entries)
        soldes["Actifs:Fantome"] = Decimal("999.99")
        gifi_map = extract_gifi_map(balanced_entries)
        result = validate_gifi(soldes, gifi_map)
        assert result.balanced is False

    def test_verification_unclassified_warns(self, non_classe_entries):
        """Avertissement quand des transactions Non-Classe existent."""
        resultats = verifier_fin_exercice(non_classe_entries, 2025)
        non_classe = [r for r in resultats if "non classee" in r.nom.lower()]
        assert len(non_classe) == 1
        assert non_classe[0].severite == Severite.WARNING
        assert "1 transaction" in non_classe[0].message

    def test_verification_pending_warns(self, pending_entries):
        """Avertissement quand des transactions en attente existent."""
        resultats = verifier_fin_exercice(pending_entries, 2025)
        pending = [r for r in resultats if "attente" in r.nom.lower()]
        assert len(pending) == 1
        assert pending[0].severite == Severite.WARNING
        assert "1 transaction" in pending[0].message


# ===========================================================================
# Tests: CPA Package (ZIP)
# ===========================================================================


class TestCpaPackage:
    """Tests pour le generateur de package CPA."""

    def test_generer_package_creates_zip(self, balanced_entries, tmp_path, weasyprint_available):
        """Le ZIP est cree avec succes."""
        zip_path = generer_package_cpa(
            entries=balanced_entries,
            annee=2025,
            output_dir=tmp_path,
        )
        assert zip_path.exists()
        assert zip_path.suffix == ".zip"
        assert "cpa-package-2025" in zip_path.name

    def test_generer_package_zip_contents(self, balanced_entries, tmp_path, weasyprint_available):
        """Le ZIP contient les sous-repertoires rapports/, annexes/, gifi/."""
        zip_path = generer_package_cpa(
            entries=balanced_entries,
            annee=2025,
            output_dir=tmp_path,
        )

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()

        # Check subdirectories exist
        has_rapports = any("rapports/" in n for n in names)
        has_annexes = any("annexes/" in n for n in names)
        has_gifi = any("gifi/" in n for n in names)

        assert has_rapports, f"rapports/ not found in {names}"
        assert has_annexes, f"annexes/ not found in {names}"
        # GIFI may or may not exist depending on whether accounts have GIFI codes
        # With our test data, some accounts have GIFI codes
        assert has_gifi, f"gifi/ not found in {names}"

    def test_generer_package_aborts_on_fatal(self, balanced_entries, tmp_path):
        """CpaPackageError quand l'equation ne balance pas."""
        # We mock the verification to return an error
        from unittest.mock import patch

        fake_results = [
            VerificationResult(
                nom="Equation comptable",
                passe=False,
                message="FATAL: Equation desequilibree",
                severite=Severite.ERROR,
            ),
        ]

        with patch(
            "compteqc.rapports.cpa_package.verifier_fin_exercice",
            return_value=fake_results,
        ):
            with pytest.raises(CpaPackageError, match="fatales"):
                generer_package_cpa(
                    entries=balanced_entries,
                    annee=2025,
                    output_dir=tmp_path,
                )


# ===========================================================================
# Tests: CLI
# ===========================================================================


class TestCLI:
    """Tests pour les commandes CLI cpa."""

    def test_cli_cpa_verifier(self, tmp_path):
        """CLI cpa verifier affiche le checklist."""
        from typer.testing import CliRunner

        from compteqc.cli.app import app

        # Write a test ledger file
        ledger_path = tmp_path / "main.beancount"
        ledger_path.write_text(BEANCOUNT_BALANCED, encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["cpa", "verifier", "--annee", "2025", "--ledger", str(ledger_path)],
        )
        assert result.exit_code == 0, f"Output: {result.output}"
        assert "Verification" in result.output or "verif" in result.output.lower()

    def test_cli_cpa_export(self, tmp_path, weasyprint_available):
        """CLI cpa export produit un ZIP."""
        from typer.testing import CliRunner

        from compteqc.cli.app import app

        ledger_path = tmp_path / "main.beancount"
        ledger_path.write_text(BEANCOUNT_BALANCED, encoding="utf-8")
        output_dir = tmp_path / "exports"

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "cpa", "export",
                "--annee", "2025",
                "--ledger", str(ledger_path),
                "--sortie", str(output_dir),
            ],
        )
        assert result.exit_code == 0, f"Output: {result.output}"
        assert "cpa-package-2025" in result.output
