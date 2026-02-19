"""Tests CLI pour CompteQC (commandes cqc)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from compteqc.cli.app import app

runner = CliRunner()

# Chemin du projet pour les fixtures
PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def ledger_tmp(tmp_path):
    """Cree un ledger temporaire isole dans tmp_path.

    Copie main.beancount et comptes.beancount dans tmp_path/ledger/,
    plus le dossier rules/ avec le fichier de regles.
    """
    # Creer la structure ledger
    ledger_dir = tmp_path / "ledger"
    ledger_dir.mkdir()

    # Copier main.beancount et comptes.beancount
    shutil.copy(PROJECT_ROOT / "ledger" / "main.beancount", ledger_dir / "main.beancount")
    shutil.copy(PROJECT_ROOT / "ledger" / "comptes.beancount", ledger_dir / "comptes.beancount")

    # Creer le sous-dossier 2026 si existe
    annee_dir = PROJECT_ROOT / "ledger" / "2026"
    if annee_dir.exists():
        dest_annee = ledger_dir / "2026"
        dest_annee.mkdir()
        for f in annee_dir.glob("*.beancount"):
            shutil.copy(f, dest_annee / f.name)

    # Copier les regles
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    shutil.copy(PROJECT_ROOT / "rules" / "categorisation.yaml", rules_dir / "categorisation.yaml")

    # Initialiser un repo git pour auto_commit
    import subprocess

    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path),
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@test.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@test.com",
            "HOME": str(tmp_path),
            "PATH": "/usr/bin:/usr/local/bin:/opt/homebrew/bin",
        },
    )

    return tmp_path


@pytest.fixture
def ledger_with_transactions(ledger_tmp):
    """Cree un ledger avec des transactions de test pour les rapports."""
    ledger_dir = ledger_tmp / "ledger"
    annee_dir = ledger_dir / "2026"
    annee_dir.mkdir(exist_ok=True)

    # Ecrire des transactions de test
    transactions = """\
; Transactions janvier 2026
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2026-01-06 ! "Acme Consulting" "Paiement consultation"
  Actifs:Banque:RBC:Cheques  8500.00 CAD
  Revenus:Consultation      -8500.00 CAD

2026-01-08 ! "Bell Canada" "Facture telephone"
  Actifs:Banque:RBC:Cheques              -125.50 CAD
  Depenses:Bureau:Internet-Telecom        125.50 CAD

2026-01-15 ! "Github" "Abonnement mensuel"
  Actifs:Banque:RBC:Cheques                  -27.00 CAD
  Depenses:Bureau:Abonnements-Logiciels       27.00 CAD

2026-01-20 ! "Transaction mystere" "Achat inconnu"
  Actifs:Banque:RBC:Cheques  -50.00 CAD
  Depenses:Non-Classe         50.00 CAD
"""
    fichier_mensuel = annee_dir / "01.beancount"
    fichier_mensuel.write_text(transactions, encoding="utf-8")

    # Ajouter l'include dans main.beancount
    main = ledger_dir / "main.beancount"
    contenu = main.read_text(encoding="utf-8")
    if 'include "2026/01.beancount"' not in contenu:
        contenu += '\ninclude "2026/01.beancount"\n'
        main.write_text(contenu, encoding="utf-8")

    return ledger_tmp


# =============================================================================
# Tests aide et version
# =============================================================================


class TestAideEtVersion:
    def test_help_retourne_0(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_help_contient_compteqc(self):
        result = runner.invoke(app, ["--help"])
        assert "CompteQC" in result.output

    def test_help_en_francais(self):
        result = runner.invoke(app, ["--help"])
        assert "Comptabilite" in result.output

    def test_version_retourne_0(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0

    def test_version_contient_numero(self):
        result = runner.invoke(app, ["--version"])
        assert "0.1.0" in result.output

    def test_importer_help(self):
        result = runner.invoke(app, ["importer", "--help"])
        assert result.exit_code == 0
        assert "fichier" in result.output.lower()


# =============================================================================
# Tests import
# =============================================================================


class TestImporterFichier:
    def test_import_fichier_inexistant(self, ledger_tmp):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_tmp / "ledger" / "main.beancount"),
                "--regles",
                str(ledger_tmp / "rules" / "categorisation.yaml"),
                "importer",
                "fichier",
                "/chemin/inexistant/fichier.csv",
            ],
        )
        assert result.exit_code == 1
        assert "introuvable" in result.output.lower()

    def test_import_format_non_reconnu(self, ledger_tmp):
        # Creer un fichier CSV non-RBC
        fake_csv = ledger_tmp / "fake.csv"
        fake_csv.write_text("col1,col2\na,b\n", encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_tmp / "ledger" / "main.beancount"),
                "--regles",
                str(ledger_tmp / "rules" / "categorisation.yaml"),
                "importer",
                "fichier",
                str(fake_csv),
            ],
        )
        assert result.exit_code == 1
        assert "non reconnu" in result.output.lower() or "Format" in result.output

    def test_import_csv_cheques_reussit(self, ledger_tmp):
        # Copier la fixture CSV
        src = FIXTURES_DIR / "rbc_cheques_sample.csv"
        dest = ledger_tmp / "import_test.csv"
        shutil.copy(src, dest)

        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_tmp / "ledger" / "main.beancount"),
                "--regles",
                str(ledger_tmp / "rules" / "categorisation.yaml"),
                "importer",
                "fichier",
                str(dest),
            ],
        )
        assert result.exit_code == 0
        assert "8" in result.output  # 8 transactions
        assert "import" in result.output.lower()

    def test_import_cree_transactions_dans_ledger(self, ledger_tmp):
        src = FIXTURES_DIR / "rbc_cheques_sample.csv"
        dest = ledger_tmp / "import_test.csv"
        shutil.copy(src, dest)

        runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_tmp / "ledger" / "main.beancount"),
                "--regles",
                str(ledger_tmp / "rules" / "categorisation.yaml"),
                "importer",
                "fichier",
                str(dest),
            ],
        )

        # Verifier que le fichier mensuel contient des transactions
        fichier_mensuel = ledger_tmp / "ledger" / "2026" / "01.beancount"
        assert fichier_mensuel.exists()
        contenu = fichier_mensuel.read_text(encoding="utf-8")
        assert "Actifs:Banque:RBC:Cheques" in contenu


# =============================================================================
# Tests soldes
# =============================================================================


class TestSoldes:
    def test_soldes_ledger_vide(self, ledger_tmp):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_tmp / "ledger" / "main.beancount"),
                "soldes",
            ],
        )
        assert result.exit_code == 0
        assert "Aucun compte" in result.output

    def test_soldes_avec_transactions(self, ledger_with_transactions):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_with_transactions / "ledger" / "main.beancount"),
                "soldes",
            ],
        )
        assert result.exit_code == 0
        assert "Actifs:Banque:RBC:Cheques" in result.output

    def test_soldes_filtre_compte(self, ledger_with_transactions):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_with_transactions / "ledger" / "main.beancount"),
                "soldes",
                "--compte",
                "Depenses",
            ],
        )
        assert result.exit_code == 0
        # Should show expense accounts only
        assert "Depenses" in result.output


# =============================================================================
# Tests rapport balance
# =============================================================================


class TestRapportBalance:
    def test_balance_ledger_vide(self, ledger_tmp):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_tmp / "ledger" / "main.beancount"),
                "rapport",
                "balance",
            ],
        )
        assert result.exit_code == 0
        assert "Aucune transaction" in result.output

    def test_balance_avec_transactions(self, ledger_with_transactions):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_with_transactions / "ledger" / "main.beancount"),
                "rapport",
                "balance",
            ],
        )
        assert result.exit_code == 0
        assert "Balance" in result.output or "balance" in result.output
        assert "TOTAL" in result.output


# =============================================================================
# Tests rapport resultats
# =============================================================================


class TestRapportResultats:
    def test_resultats_ledger_vide(self, ledger_tmp):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_tmp / "ledger" / "main.beancount"),
                "rapport",
                "resultats",
            ],
        )
        assert result.exit_code == 0
        assert "Aucune transaction" in result.output

    def test_resultats_avec_transactions(self, ledger_with_transactions):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_with_transactions / "ledger" / "main.beancount"),
                "rapport",
                "resultats",
            ],
        )
        assert result.exit_code == 0
        # Should show revenue and expenses
        assert "REVENUS" in result.output or "revenus" in result.output
        assert "DEPENSES" in result.output or "depenses" in result.output
        assert "RESULTAT NET" in result.output or "resultat" in result.output


# =============================================================================
# Tests rapport bilan
# =============================================================================


class TestRapportBilan:
    def test_bilan_ledger_vide(self, ledger_tmp):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_tmp / "ledger" / "main.beancount"),
                "rapport",
                "bilan",
            ],
        )
        assert result.exit_code == 0
        assert "Aucune donnee" in result.output

    def test_bilan_avec_transactions(self, ledger_with_transactions):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_with_transactions / "ledger" / "main.beancount"),
                "rapport",
                "bilan",
            ],
        )
        assert result.exit_code == 0
        assert "ACTIFS" in result.output
        assert "PASSIFS" in result.output
        assert "CAPITAUX" in result.output


# =============================================================================
# Tests revue
# =============================================================================


class TestRevue:
    def test_revue_ledger_vide(self, ledger_tmp):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_tmp / "ledger" / "main.beancount"),
                "revue",
            ],
        )
        assert result.exit_code == 0
        assert "Aucune transaction non-classee" in result.output

    def test_revue_avec_non_classees(self, ledger_with_transactions):
        result = runner.invoke(
            app,
            [
                "--ledger",
                str(ledger_with_transactions / "ledger" / "main.beancount"),
                "revue",
            ],
        )
        assert result.exit_code == 0
        # The fixture has one non-classified transaction
        assert "non-classee" in result.output.lower()
        assert "Transaction mystere" in result.output or "Achat inconnu" in result.output
