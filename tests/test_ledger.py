"""Tests pour le ledger Beancount, la validation, git auto-commit et la gestion de fichiers."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from compteqc.ledger.fichiers import ajouter_include, chemin_fichier_mensuel, ecrire_transactions
from compteqc.ledger.git import auto_commit
from compteqc.ledger.validation import charger_comptes_existants, valider_ledger

# Chemin vers le ledger du projet
LEDGER_DIR = Path(__file__).parent.parent / "ledger"
MAIN_BEANCOUNT = LEDGER_DIR / "main.beancount"


class TestValidation:
    """Tests pour la validation du ledger."""

    def test_bean_check_passe_sur_ledger_initial(self):
        """bean-check doit reussir sur le ledger initial."""
        valide, erreurs = valider_ledger(MAIN_BEANCOUNT)
        assert valide, f"bean-check a echoue: {erreurs}"
        assert erreurs == []

    def test_valider_ledger_retourne_true(self):
        """valider_ledger doit retourner True pour un ledger valide."""
        valide, erreurs = valider_ledger(MAIN_BEANCOUNT)
        assert valide is True
        assert isinstance(erreurs, list)

    def test_plan_comptable_contient_au_moins_45_comptes(self):
        """Le plan comptable doit avoir au moins 45 comptes ouverts."""
        comptes = charger_comptes_existants(MAIN_BEANCOUNT)
        assert len(comptes) >= 45, f"Seulement {len(comptes)} comptes trouves"

    def test_chaque_compte_a_metadata_gifi(self):
        """Chaque compte ouvert doit avoir un metadata gifi."""
        from beancount import loader

        entries, _, _ = loader.load_file(str(MAIN_BEANCOUNT))
        comptes_open = [e for e in entries if hasattr(e, "account")]
        for compte in comptes_open:
            assert "gifi" in compte.meta, (
                f"Compte {compte.account} n'a pas de metadata gifi"
            )

    def test_charger_comptes_existants_contient_non_classe(self):
        """Le compte Depenses:Non-Classe doit exister."""
        comptes = charger_comptes_existants(MAIN_BEANCOUNT)
        assert "Depenses:Non-Classe" in comptes

    def test_charger_comptes_existants_contient_banque(self):
        """Le compte Actifs:Banque:RBC:Cheques doit exister."""
        comptes = charger_comptes_existants(MAIN_BEANCOUNT)
        assert "Actifs:Banque:RBC:Cheques" in comptes


class TestFichiers:
    """Tests pour la gestion des fichiers du ledger."""

    def test_chemin_fichier_mensuel_cree_fichier(self, tmp_path: Path):
        """chemin_fichier_mensuel doit creer le fichier s'il n'existe pas."""
        chemin = chemin_fichier_mensuel(2026, 3, tmp_path)
        assert chemin.exists()
        assert chemin.name == "03.beancount"
        contenu = chemin.read_text()
        assert "mars 2026" in contenu

    def test_chemin_fichier_mensuel_cree_repertoire_annee(self, tmp_path: Path):
        """Le repertoire de l'annee doit etre cree automatiquement."""
        chemin = chemin_fichier_mensuel(2027, 1, tmp_path)
        assert (tmp_path / "2027").is_dir()
        assert chemin.exists()

    def test_chemin_fichier_mensuel_idempotent(self, tmp_path: Path):
        """Appeler deux fois ne doit pas ecraser le fichier."""
        chemin1 = chemin_fichier_mensuel(2026, 5, tmp_path)
        ecrire_transactions(chemin1, "2026-05-01 * \"Test\"\n  Depenses:Divers 100 CAD\n")
        chemin2 = chemin_fichier_mensuel(2026, 5, tmp_path)
        assert chemin1 == chemin2
        contenu = chemin2.read_text()
        assert "Test" in contenu  # Le contenu n'a pas ete ecrase

    def test_ajouter_include(self, tmp_path: Path):
        """ajouter_include doit ajouter l'include et ne pas le dupliquer."""
        main = tmp_path / "main.beancount"
        main.write_text('option "title" "Test"\n')

        # Premier ajout
        assert ajouter_include(main, "2026/01.beancount") is True
        contenu = main.read_text()
        assert 'include "2026/01.beancount"' in contenu

        # Deuxieme ajout (deja present)
        assert ajouter_include(main, "2026/01.beancount") is False

    def test_ecrire_transactions(self, tmp_path: Path):
        """ecrire_transactions doit ajouter du texte a la fin du fichier."""
        fichier = tmp_path / "test.beancount"
        fichier.write_text("; Header\n")
        ecrire_transactions(fichier, '2026-01-15 * "Test"\n  Depenses:Divers 50 CAD\n')
        contenu = fichier.read_text()
        assert "; Header" in contenu
        assert "Test" in contenu


class TestAutoCommit:
    """Tests pour l'auto-commit git."""

    def _setup_git_repo(self, tmp_path: Path) -> Path:
        """Cree un repo git temporaire avec un ledger valide."""
        # Init git repo
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(tmp_path),
            capture_output=True,
        )

        # Creer structure ledger
        ledger_dir = tmp_path / "ledger"
        ledger_dir.mkdir()

        main = ledger_dir / "main.beancount"
        main.write_text(
            'option "title" "Test"\n'
            'option "operating_currency" "CAD"\n'
            'option "name_assets" "Actifs"\n'
            'option "name_expenses" "Depenses"\n'
            "\n"
            '2025-01-01 open Actifs:Banque CAD\n'
            '2025-01-01 open Depenses:Test CAD\n'
        )

        # Commit initial
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=str(tmp_path),
            capture_output=True,
        )

        return tmp_path

    def test_auto_commit_cree_commit(self, tmp_path: Path):
        """auto_commit doit creer un commit si le ledger est valide et modifie."""
        repo = self._setup_git_repo(tmp_path)
        ledger_dir = repo / "ledger"

        # Ajouter une transaction (avec name_* options car fichier inclus)
        tx_file = ledger_dir / "test.beancount"
        tx_file.write_text(
            'option "name_assets" "Actifs"\n'
            'option "name_expenses" "Depenses"\n'
            '\n'
            '2026-01-15 * "Test Transaction"\n'
            "  Depenses:Test 100 CAD\n"
            "  Actifs:Banque -100 CAD\n"
        )

        # Ajouter l'include dans main
        main = ledger_dir / "main.beancount"
        contenu = main.read_text()
        contenu += '\ninclude "test.beancount"\n'
        main.write_text(contenu)

        result = auto_commit(repo, "test: ajout transaction")
        assert result is True

        # Verifier que le commit existe
        log = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        assert "test: ajout transaction" in log.stdout

    def test_auto_commit_sans_changements(self, tmp_path: Path):
        """auto_commit doit retourner False s'il n'y a pas de changements."""
        repo = self._setup_git_repo(tmp_path)
        result = auto_commit(repo, "test: pas de changement")
        assert result is False

    def test_auto_commit_refuse_ledger_invalide(self, tmp_path: Path):
        """auto_commit doit refuser de commiter un ledger invalide."""
        repo = self._setup_git_repo(tmp_path)
        ledger_dir = repo / "ledger"

        # Corrompre le ledger
        main = ledger_dir / "main.beancount"
        main.write_text("ceci n'est pas du beancount valide\n")

        with pytest.raises(ValueError, match="Ledger invalide"):
            auto_commit(repo, "test: ledger invalide")
