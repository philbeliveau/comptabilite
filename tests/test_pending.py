"""Tests pour la gestion des transactions pending."""

from __future__ import annotations

import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.core import amount, data

from compteqc.categorisation.pending import (
    approuver_transactions,
    ecrire_pending,
    lire_pending,
    rejeter_transactions,
)
from compteqc.categorisation.pipeline import ResultatPipeline

PROJECT_ROOT = Path(__file__).parent.parent


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
    compte: str = "Depenses:Repas",
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
def ledger_env(tmp_path):
    """Cree un environnement ledger temporaire avec main.beancount."""
    ledger_dir = tmp_path / "ledger"
    ledger_dir.mkdir()

    # Copier comptes.beancount
    shutil.copy(
        PROJECT_ROOT / "ledger" / "comptes.beancount",
        ledger_dir / "comptes.beancount",
    )

    # Creer un main.beancount propre (sans includes vers des fichiers manquants)
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

    return {
        "ledger_dir": ledger_dir,
        "main": ledger_dir / "main.beancount",
        "pending": ledger_dir / "pending.beancount",
    }


class TestEcrirePending:
    """Tests pour ecrire_pending."""

    def test_ecrire_transactions_pending(self, ledger_env):
        """Ecrit des transactions et les retrouve avec le tag #pending."""
        txn = _make_txn("Tim Hortons", "cafe", Decimal("5.50"))
        resultat = _make_resultat("Depenses:Repas-Representation", 0.88)

        nb = ecrire_pending(ledger_env["pending"], [txn], [resultat])

        assert nb == 1
        assert ledger_env["pending"].exists()
        contenu = ledger_env["pending"].read_text(encoding="utf-8")
        assert "#pending" in contenu
        assert "Depenses:Repas-Representation" in contenu

    def test_ecrire_multiple_transactions(self, ledger_env):
        """Ecrit plusieurs transactions pending."""
        txns = [
            _make_txn("Tim Hortons", "cafe", Decimal("5.50")),
            _make_txn("Shell", "essence", Decimal("65.00")),
        ]
        resultats = [
            _make_resultat("Depenses:Repas-Representation", 0.88),
            _make_resultat("Depenses:Deplacement:Transport", 0.85),
        ]

        nb = ecrire_pending(ledger_env["pending"], txns, resultats)

        assert nb == 2

    def test_ecrire_vide_retourne_zero(self, ledger_env):
        """Ecrire une liste vide retourne 0."""
        nb = ecrire_pending(ledger_env["pending"], [], [])
        assert nb == 0

    def test_metadata_ia_presentes(self, ledger_env):
        """Les metadata source_ia et confiance sont presentes."""
        txn = _make_txn("Test", "test", Decimal("10.00"))
        resultat = _make_resultat("Depenses:Repas", 0.92, source="llm")

        ecrire_pending(ledger_env["pending"], [txn], [resultat])

        contenu = ledger_env["pending"].read_text(encoding="utf-8")
        assert 'source_ia: "llm"' in contenu
        assert 'confiance: "0.92"' in contenu

    def test_capex_metadata(self, ledger_env):
        """Les metadata CAPEX sont ajoutees quand est_capex=True."""
        txn = _make_txn("Apple", "MacBook", Decimal("2500.00"))
        resultat = _make_resultat(
            "Depenses:Bureau:Fournitures", 0.95,
            est_capex=True, classe_dpa=50,
        )

        ecrire_pending(ledger_env["pending"], [txn], [resultat])

        contenu = ledger_env["pending"].read_text(encoding="utf-8")
        assert 'capex: "oui"' in contenu
        assert 'classe_dpa_suggeree: "50"' in contenu

    def test_suggestions_desaccord(self, ledger_env):
        """Les suggestions ML/LLM sont ajoutees en cas de desaccord."""
        txn = _make_txn("Cinema", "film", Decimal("15.00"))
        resultat = _make_resultat(
            "Depenses:Divers", 0.85,
            suggestions={
                "ml": ("Depenses:Repas-Representation", 0.82),
                "llm": ("Depenses:Divers", 0.85),
            },
        )

        ecrire_pending(ledger_env["pending"], [txn], [resultat])

        contenu = ledger_env["pending"].read_text(encoding="utf-8")
        assert "suggestion_ml" in contenu
        assert "suggestion_llm" in contenu


class TestLirePending:
    """Tests pour lire_pending."""

    def test_lire_pending_roundtrip(self, ledger_env):
        """Ecrire puis lire retourne les transactions avec #pending."""
        txn = _make_txn("Tim Hortons", "cafe", Decimal("5.50"))
        resultat = _make_resultat("Depenses:Repas-Representation", 0.88)

        ecrire_pending(ledger_env["pending"], [txn], [resultat])
        pending = lire_pending(ledger_env["pending"])

        assert len(pending) == 1
        assert "pending" in pending[0].tags
        assert pending[0].payee == "Tim Hortons"

    def test_lire_fichier_inexistant_retourne_vide(self, tmp_path):
        """Lire un fichier inexistant retourne une liste vide."""
        result = lire_pending(tmp_path / "inexistant.beancount")
        assert result == []

    def test_lire_fichier_vide_retourne_vide(self, ledger_env):
        """Lire un fichier pending sans transactions retourne vide."""
        ledger_env["pending"].write_text(
            '; Transactions en attente\n'
            'option "name_assets" "Actifs"\n'
            'option "name_liabilities" "Passifs"\n'
            'option "name_equity" "Capital"\n'
            'option "name_income" "Revenus"\n'
            'option "name_expenses" "Depenses"\n',
            encoding="utf-8",
        )
        result = lire_pending(ledger_env["pending"])
        assert result == []


class TestApprouverTransactions:
    """Tests pour approuver_transactions."""

    def test_approuver_deplace_vers_mensuel(self, ledger_env):
        """Approuver une transaction la deplace vers le fichier mensuel."""
        txn = _make_txn("Tim Hortons", "cafe", Decimal("5.50"))
        resultat = _make_resultat("Depenses:Repas-Representation", 0.88)

        ecrire_pending(ledger_env["pending"], [txn], [resultat])

        nb = approuver_transactions(
            ledger_env["pending"],
            ledger_env["main"],
            [0],
        )

        assert nb == 1

        # La transaction doit etre dans le fichier mensuel
        fichier_mensuel = ledger_env["ledger_dir"] / "2026" / "01.beancount"
        assert fichier_mensuel.exists()
        contenu = fichier_mensuel.read_text(encoding="utf-8")
        assert "Tim Hortons" in contenu
        assert "Depenses:Repas-Representation" in contenu

        # La transaction ne doit plus etre dans pending
        pending = lire_pending(ledger_env["pending"])
        assert len(pending) == 0

    def test_approuver_partiel(self, ledger_env):
        """Approuver certaines transactions laisse les autres dans pending."""
        txns = [
            _make_txn("Tim Hortons", "cafe", Decimal("5.50")),
            _make_txn("Shell", "essence", Decimal("65.00")),
        ]
        resultats = [
            _make_resultat("Depenses:Repas-Representation", 0.88),
            _make_resultat("Depenses:Deplacement:Transport", 0.85),
        ]

        ecrire_pending(ledger_env["pending"], txns, resultats)

        nb = approuver_transactions(
            ledger_env["pending"],
            ledger_env["main"],
            [0],  # Seulement la premiere
        )

        assert nb == 1

        pending = lire_pending(ledger_env["pending"])
        assert len(pending) == 1
        assert pending[0].payee == "Shell"

    def test_approuver_vide_retourne_zero(self, ledger_env):
        """Approuver depuis un pending vide retourne 0."""
        nb = approuver_transactions(
            ledger_env["pending"],
            ledger_env["main"],
            [0],
        )
        assert nb == 0


class TestRejeterTransactions:
    """Tests pour rejeter_transactions."""

    def test_rejeter_supprime_transactions(self, ledger_env):
        """Rejeter supprime les transactions du pending."""
        txns = [
            _make_txn("Tim Hortons", "cafe", Decimal("5.50")),
            _make_txn("Shell", "essence", Decimal("65.00")),
        ]
        resultats = [
            _make_resultat("Depenses:Repas-Representation", 0.88),
            _make_resultat("Depenses:Deplacement:Transport", 0.85),
        ]

        ecrire_pending(ledger_env["pending"], txns, resultats)

        nb = rejeter_transactions(ledger_env["pending"], [0])

        assert nb == 1

        pending = lire_pending(ledger_env["pending"])
        assert len(pending) == 1
        assert pending[0].payee == "Shell"

    def test_rejeter_toutes(self, ledger_env):
        """Rejeter toutes les transactions vide le pending."""
        txns = [
            _make_txn("Tim Hortons", "cafe", Decimal("5.50")),
            _make_txn("Shell", "essence", Decimal("65.00")),
        ]
        resultats = [
            _make_resultat("Depenses:Repas-Representation", 0.88),
            _make_resultat("Depenses:Deplacement:Transport", 0.85),
        ]

        ecrire_pending(ledger_env["pending"], txns, resultats)

        nb = rejeter_transactions(ledger_env["pending"], [0, 1])

        assert nb == 2
        pending = lire_pending(ledger_env["pending"])
        assert len(pending) == 0

    def test_rejeter_vide_retourne_zero(self, ledger_env):
        """Rejeter depuis un pending vide retourne 0."""
        nb = rejeter_transactions(ledger_env["pending"], [0])
        assert nb == 0
