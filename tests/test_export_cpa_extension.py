"""Tests pour l'aperçu filtre de ExportCPAExtension."""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from beancount.core import data
from flask import Flask
from fava.core.filters import FilterError

from compteqc.fava_ext.export_cpa import ExportCPAExtension
from compteqc.rapports.cpa_package import CpaPackageError


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


def test_export_endpoint_generates_zip_download(tmp_path, monkeypatch):
    """Le endpoint d'export genere un ZIP et le retourne en telechargement."""
    ext = ExportCPAExtension.__new__(ExportCPAExtension)
    txn = _make_transaction()
    ledger = Mock()
    ledger.beancount_file_path = str(tmp_path / "ledger" / "main.beancount")
    ledger.get_filtered.return_value = SimpleNamespace(entries=[txn])
    ext.ledger = ledger

    zip_path = tmp_path / "ledger" / "exports" / "cpa-package-2026.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.write_bytes(b"zip-data")

    def faux_generer_package_cpa(*, entries, annee, output_dir, **_kwargs):
        assert entries == [txn]
        assert annee == 2026
        assert Path(output_dir) == tmp_path / "ledger" / "exports"
        return zip_path

    monkeypatch.setattr(
        "compteqc.fava_ext.export_cpa.generer_package_cpa",
        faux_generer_package_cpa,
    )

    app = Flask(__name__)
    filtre = 'fichier_source:"^debit\\\\-march\\\\.csv$"'
    with app.test_request_context(
        "/export",
        method="POST",
        data={"annee": "2026", "filter": filtre},
    ):
        response = ext.export()

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert "attachment" in response.headers["Content-Disposition"]


def test_export_endpoint_returns_400_on_cpa_error(monkeypatch, tmp_path):
    """Une erreur metier CPA remonte en 400 JSON."""
    ext = ExportCPAExtension.__new__(ExportCPAExtension)
    txn = _make_transaction()
    ledger = Mock()
    ledger.beancount_file_path = str(tmp_path / "ledger" / "main.beancount")
    ledger.get_filtered.return_value = SimpleNamespace(entries=[txn])
    ext.ledger = ledger

    monkeypatch.setattr(
        "compteqc.fava_ext.export_cpa.generer_package_cpa",
        lambda **_kwargs: (_ for _ in ()).throw(CpaPackageError("fatales detectees")),
    )

    app = Flask(__name__)
    with app.test_request_context(
        "/export",
        method="POST",
        data={"annee": "2026", "filter": 'fichier_source:"ok"'},
    ):
        response, status = ext.export()

    assert status == 400
    assert response.get_json()["message"] == "fatales detectees"


def test_export_endpoint_rejects_empty_scope(tmp_path):
    """Le endpoint refuse un export sans transaction."""
    ext = ExportCPAExtension.__new__(ExportCPAExtension)
    ledger = Mock()
    ledger.beancount_file_path = str(tmp_path / "ledger" / "main.beancount")
    ledger.get_filtered.return_value = SimpleNamespace(entries=[])
    ext.ledger = ledger

    app = Flask(__name__)
    with app.test_request_context(
        "/export",
        method="POST",
        data={"annee": "2026", "filter": 'fichier_source:"vide"'},
    ):
        response, status = ext.export()

    assert status == 400
    assert "Aucune transaction" in response.get_json()["message"]
