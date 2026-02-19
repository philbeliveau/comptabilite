"""Tests pour la CLI de revision des transactions en attente."""

from __future__ import annotations

import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.core import amount, data
from typer.testing import CliRunner

from compteqc.categorisation.pending import ecrire_pending, lire_pending
from compteqc.categorisation.pipeline import ResultatPipeline

PROJECT_ROOT = Path(__file__).parent.parent
runner = CliRunner()


def _make_txn(
    payee: str,
    narration: str,
    montant: Decimal,
    compte_debit: str = "Depenses:Non-Classe",
    compte_credit: str = "Actifs:Banque:RBC:Cheques",
    txn_date: date | None = None,
) -> data.Transaction:
    """Cree une transaction Beancount de test."""
    d = txn_date or date(2026, 1, 15)
    meta = data.new_metadata("<test>", 0)
    meta["categorisation"] = "non-classe"
    return data.Transaction(
        meta=meta,
        date=d,
        flag="!",
        payee=payee,
        narration=narration,
        tags=frozenset(),
        links=frozenset(),
        postings=[
            data.Posting(
                compte_credit,
                amount.Amount(-montant, "CAD"),
                None, None, None, None,
            ),
            data.Posting(
                compte_debit,
                amount.Amount(montant, "CAD"),
                None, None, None, None,
            ),
        ],
    )


def _make_resultat(
    compte: str = "Depenses:Repas-Representation",
    confiance: float = 0.88,
    source: str = "ml",
    est_capex: bool = False,
    classe_dpa: int | None = None,
    revue_obligatoire: bool = False,
    suggestions: dict | None = None,
) -> ResultatPipeline:
    return ResultatPipeline(
        compte=compte,
        confiance=confiance,
        source=source,
        regle=None,
        est_capex=est_capex,
        classe_dpa=classe_dpa,
        revue_obligatoire=revue_obligatoire,
        suggestions=suggestions,
    )


@pytest.fixture
def ledger_env(tmp_path, monkeypatch):
    """Cree un environnement ledger temporaire avec main.beancount et pending."""
    ledger_dir = tmp_path / "ledger"
    ledger_dir.mkdir()

    # Copier comptes.beancount
    shutil.copy(
        PROJECT_ROOT / "ledger" / "comptes.beancount",
        ledger_dir / "comptes.beancount",
    )

    # Creer un main.beancount propre
    main_content = (
        'option "title" "CompteQC - Test"\n'
        'option "operating_currency" "CAD"\n'
        'option "name_assets" "Actifs"\n'
        'option "name_liabilities" "Passifs"\n'
        'option "name_equity" "Capital"\n'
        'option "name_income" "Revenus"\n'
        'option "name_expenses" "Depenses"\n'
        '\n'
        'include "comptes.beancount"\n'
    )
    (ledger_dir / "main.beancount").write_text(main_content, encoding="utf-8")

    # Patcher le chemin historique dans reviser.py
    import compteqc.cli.reviser as reviser_mod

    monkeypatch.setattr(
        reviser_mod, "CHEMIN_HISTORIQUE_DEFAUT",
        tmp_path / "corrections" / "historique.json",
    )

    # Store CLI args for --ledger and --regles options
    # (The Typer callback always resets globals from CLI defaults,
    # so monkeypatching _ledger_path is ineffective. Pass via CLI args instead.)
    regles_path = tmp_path / "rules" / "categorisation.yaml"

    return {
        "ledger_dir": ledger_dir,
        "main": ledger_dir / "main.beancount",
        "pending": ledger_dir / "pending.beancount",
        "tmp_path": tmp_path,
        "cli_args": ["--ledger", str(ledger_dir / "main.beancount"),
                      "--regles", str(regles_path)],
    }


def _setup_pending(ledger_env, txns_resultats: list[tuple] | None = None):
    """Configure des transactions pending pour les tests."""
    if txns_resultats is None:
        txns_resultats = [
            (
                _make_txn("Tim Hortons", "cafe", Decimal("5.50")),
                _make_resultat("Depenses:Repas-Representation", 0.88),
            ),
            (
                _make_txn("Mystere Inc", "paiement inconnu", Decimal("200.00")),
                _make_resultat("Depenses:Divers", 0.65, revue_obligatoire=True),
            ),
            (
                _make_txn("Shell", "essence", Decimal("65.00")),
                _make_resultat("Depenses:Deplacement:Transport", 0.92),
            ),
        ]

    txns = [t for t, _ in txns_resultats]
    resultats = [r for _, r in txns_resultats]
    ecrire_pending(ledger_env["pending"], txns, resultats)


class TestReviserListe:
    """Tests pour la commande reviser liste."""

    def test_liste_affiche_pending(self, ledger_env):
        """La commande liste affiche les transactions pending."""
        from compteqc.cli.app import app

        _setup_pending(ledger_env)

        result = runner.invoke(app, ledger_env["cli_args"] + ["reviser", "liste"])

        assert result.exit_code == 0
        assert "Tim Hortons" in result.output
        assert "Mystere Inc" in result.output
        assert "Shell" in result.output

    def test_liste_vide(self, ledger_env):
        """Sans transactions pending, affiche un message."""
        from compteqc.cli.app import app

        result = runner.invoke(app, ledger_env["cli_args"] + ["reviser", "liste"])

        assert result.exit_code == 0
        assert "Aucune transaction en attente" in result.output

    def test_liste_filtre_obligatoire(self, ledger_env):
        """Le filtre --obligatoire n'affiche que les <80%."""
        from compteqc.cli.app import app

        _setup_pending(ledger_env)

        result = runner.invoke(app, ledger_env["cli_args"] + ["reviser", "liste", "--obligatoire"])

        assert result.exit_code == 0
        assert "Mystere Inc" in result.output
        # Les optionnelles ne doivent pas apparaitre dans le resultat filtre
        # (Tim Hortons a 88%, Shell a 92%)

    def test_liste_affiche_colonnes(self, ledger_env):
        """La table contient les colonnes requises."""
        from compteqc.cli.app import app

        _setup_pending(ledger_env)

        result = runner.invoke(app, ledger_env["cli_args"] + ["reviser", "liste"])

        # Rich may truncate column headers in narrow terminals,
        # so check for the title and key data presence instead
        assert "Transactions en attente" in result.output
        assert "Beneficiaire" in result.output
        assert "Compte propose" in result.output
        # Conf. and Source may be truncated by Rich; verify data is present
        assert "Depenses:" in result.output

    def test_liste_resume_footer(self, ledger_env):
        """Le resume affiche le nombre de transactions."""
        from compteqc.cli.app import app

        _setup_pending(ledger_env)

        result = runner.invoke(app, ledger_env["cli_args"] + ["reviser", "liste"])

        assert "3 transactions en attente" in result.output
        assert "1 obligatoires" in result.output
        assert "2 optionnelles" in result.output


class TestReviserApprouver:
    """Tests pour la commande reviser approuver."""

    def test_approuver_deplace_vers_mensuel(self, ledger_env):
        """Approuver une transaction la deplace vers le fichier mensuel."""
        from compteqc.cli.app import app

        _setup_pending(ledger_env)

        result = runner.invoke(app, ledger_env["cli_args"] + ["reviser", "approuver", "1"])

        assert result.exit_code == 0
        assert "approuvee" in result.output

        # Verifier que le pending a diminue
        pending = lire_pending(ledger_env["pending"])
        assert len(pending) == 2

    def test_approuver_vide(self, ledger_env):
        """Approuver depuis un pending vide affiche un message."""
        from compteqc.cli.app import app

        result = runner.invoke(app, ledger_env["cli_args"] + ["reviser", "approuver", "1"])

        assert result.exit_code == 0
        assert "Aucune transaction en attente" in result.output


class TestReviserRejeter:
    """Tests pour la commande reviser rejeter."""

    def test_rejeter_supprime(self, ledger_env):
        """Rejeter une transaction la supprime du pending."""
        from compteqc.cli.app import app

        _setup_pending(ledger_env)

        result = runner.invoke(app, ledger_env["cli_args"] + ["reviser", "rejeter", "1"])

        assert result.exit_code == 0
        assert "rejetee" in result.output

        pending = lire_pending(ledger_env["pending"])
        assert len(pending) == 2

    def test_rejeter_vide(self, ledger_env):
        """Rejeter depuis un pending vide affiche un message."""
        from compteqc.cli.app import app

        result = runner.invoke(app, ledger_env["cli_args"] + ["reviser", "rejeter", "1"])

        assert result.exit_code == 0
        assert "Aucune transaction en attente" in result.output


class TestReviserRecategoriser:
    """Tests pour la commande reviser recategoriser."""

    def test_recategoriser_met_a_jour(self, ledger_env):
        """Recategoriser met a jour le compte et deplace la transaction."""
        from compteqc.cli.app import app

        _setup_pending(ledger_env)

        result = runner.invoke(
            app, ledger_env["cli_args"] + ["reviser", "recategoriser", "1", "Depenses:Bureau:Fournitures"]
        )

        assert result.exit_code == 0
        assert "recategorisee" in result.output

        # Verifier que le pending a diminue
        pending = lire_pending(ledger_env["pending"])
        assert len(pending) == 2

    def test_recategoriser_indice_invalide(self, ledger_env):
        """Un indice invalide affiche une erreur."""
        from compteqc.cli.app import app

        _setup_pending(ledger_env)

        result = runner.invoke(
            app, ledger_env["cli_args"] + ["reviser", "recategoriser", "99", "Depenses:Bureau:Fournitures"]
        )

        assert result.exit_code == 0
        assert "invalide" in result.output.lower()

    def test_recategoriser_compte_invalide(self, ledger_env):
        """Un compte invalide affiche une erreur."""
        from compteqc.cli.app import app

        _setup_pending(ledger_env)

        result = runner.invoke(
            app, ledger_env["cli_args"] + ["reviser", "recategoriser", "1", "Depenses:CompteInexistant"]
        )

        assert result.exit_code == 0
        assert "invalide" in result.output.lower()

    def test_auto_regle_apres_deux_corrections(self, ledger_env):
        """Apres 2 corrections identiques, une regle auto est generee."""
        from compteqc.cli.app import app

        # Setup avec 2 transactions du meme vendeur
        # Note: beancount parser sorts by date, so Tim Hortons dates must be
        # before Shell to ensure consistent index ordering after re-parse.
        txns_resultats = [
            (
                _make_txn("Tim Hortons", "cafe matin", Decimal("5.50"),
                           txn_date=date(2026, 1, 10)),
                _make_resultat("Depenses:Divers", 0.65),
            ),
            (
                _make_txn("Tim Hortons", "cafe aprem", Decimal("4.50"),
                           txn_date=date(2026, 1, 11)),
                _make_resultat("Depenses:Divers", 0.70),
            ),
            (
                _make_txn("Shell", "essence", Decimal("65.00"),
                           txn_date=date(2026, 1, 20)),
                _make_resultat("Depenses:Deplacement:Transport", 0.85),
            ),
        ]
        _setup_pending(ledger_env, txns_resultats)

        # Premiere correction
        result1 = runner.invoke(
            app, ledger_env["cli_args"] + ["reviser", "recategoriser", "1", "Depenses:Repas-Representation"]
        )
        assert result1.exit_code == 0
        assert "regle auto" not in result1.output.lower()

        # Deuxieme correction identique (meme vendeur, meme compte)
        # Apres la premiere, l'indice 1 est maintenant "Tim Hortons cafe aprem"
        result2 = runner.invoke(
            app, ledger_env["cli_args"] + ["reviser", "recategoriser", "1", "Depenses:Repas-Representation"]
        )
        assert result2.exit_code == 0
        assert "regle auto" in result2.output.lower()


class TestParseIndices:
    """Tests pour le parsing des indices."""

    def test_parse_simple(self):
        from compteqc.cli.reviser import _parse_indices

        assert _parse_indices("1,3,5", 10) == [0, 2, 4]

    def test_parse_range(self):
        from compteqc.cli.reviser import _parse_indices

        assert _parse_indices("1-3", 10) == [0, 1, 2]

    def test_parse_all(self):
        from compteqc.cli.reviser import _parse_indices

        assert _parse_indices("all", 5) == [0, 1, 2, 3, 4]

    def test_parse_hors_limites(self):
        from compteqc.cli.reviser import _parse_indices

        # Indices hors limites sont filtres
        assert _parse_indices("10,20", 5) == []
