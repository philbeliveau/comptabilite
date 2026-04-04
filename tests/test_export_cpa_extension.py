"""Tests pour l'aperçu filtre de ExportCPAExtension."""

from __future__ import annotations

import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from beancount.core import data
from flask import Flask
from fava.core.filters import FilterError

from compteqc.fava_ext.export_cpa import ExportCPAExtension


def _make_transaction(
    *,
    fichier_source: str = "debit-march.csv",
    date_txn: datetime.date = datetime.date(2026, 3, 3),
    payee: str = "Amazon",
    narration: str = "Logiciel",
    montant: str = "42.75",
) -> data.Transaction:
    return data.Transaction(
        meta={"fichier_source": fichier_source},
        date=date_txn,
        flag="*",
        payee=payee,
        narration=narration,
        tags=frozenset(),
        links=frozenset(),
        postings=[
            data.Posting(
                account="Depenses:Logiciels",
                units=data.Amount(Decimal(montant), "CAD"),
                cost=None,
                price=None,
                flag=None,
                meta=None,
            ),
            data.Posting(
                account="Actifs:Banque:RBC:Cheques",
                units=data.Amount(Decimal(montant) * Decimal("-1"), "CAD"),
                cost=None,
                price=None,
                flag=None,
                meta=None,
            ),
        ],
    )


def test_export_context_uses_filter_from_request():
    """L'extension passe le filtre d'URL a Fava et expose les lignes d'aperçu."""
    ext = ExportCPAExtension.__new__(ExportCPAExtension)
    txn = _make_transaction()
    ledger = Mock()
    ledger.get_filtered.return_value = SimpleNamespace(entries=[txn])
    ext.ledger = ledger

    app = Flask(__name__)
    filtre = 'fichier_source:"^debit\\\\-march\\\\.csv$"'
    with app.test_request_context(f"/?filter={filtre}"):
        contexte = ext.export_context()

    ledger.get_filtered.assert_called_once_with(filter=filtre)
    assert contexte["filter"] == filtre
    assert contexte["count"] == 1
    assert contexte["sources"] == ["debit-march.csv"]
    assert contexte["transactions"][0]["montant"] == "42.75 CAD"


def test_export_context_handles_invalid_filter_gracefully():
    """Un filtre invalide retourne un message d'erreur au template."""
    ext = ExportCPAExtension.__new__(ExportCPAExtension)
    ledger = Mock()
    ledger.get_filtered.side_effect = FilterError("filter", "Filtre brise")
    ext.ledger = ledger

    app = Flask(__name__)
    with app.test_request_context("/?filter=oops:("):
        contexte = ext.export_context()

    assert contexte["count"] == 0
    assert contexte["transactions"] == []
    assert contexte["error"] == "Filtre brise"


def test_export_context_without_request_uses_all_entries():
    """Hors contexte Flask, l'extension retombe sur toutes les entrees du ledger."""
    ext = ExportCPAExtension.__new__(ExportCPAExtension)
    txn = _make_transaction(fichier_source="credit-march.csv")
    ledger = Mock()
    ledger.all_entries = [txn]
    ext.ledger = ledger

    contexte = ext.export_context()

    ledger.get_filtered.assert_not_called()
    assert contexte["filter"] == ""
    assert contexte["count"] == 1
    assert contexte["sources"] == ["credit-march.csv"]
