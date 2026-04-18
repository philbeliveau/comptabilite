"""Tests pour les extensions Fava Quebec.

Verifie l'importabilite, les titres de rapport, l'heritage FavaExtensionBase,
l'existence des templates, l'enregistrement dans main.beancount, et la logique
d'alerte s.15(2).
"""

import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from beancount.parser import parser as beancount_parser
from fava.ext import FavaExtensionBase

from compteqc.fava_ext.approbation import ApprobationExtension
from compteqc.fava_ext.dpa_qc import DpaQCExtension
from compteqc.fava_ext.echeances import EcheancesExtension
from compteqc.fava_ext.export_cpa import ExportCPAExtension
from compteqc.fava_ext.paie_qc import PaieQCExtension
from compteqc.fava_ext.pret_actionnaire import PretActionnaireExtension, niveau_alerte_s152
from compteqc.fava_ext.recus import RecusExtension
from compteqc.fava_ext.tableau_bord import TableauBordExtension
from compteqc.fava_ext.taxes_qc import TaxesQCExtension
from compteqc.mcp.tools.quebec import sommaire_tps_tvq

# Racine du projet
PROJECT_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Test: report_title correct pour chaque extension
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "cls, expected_title",
    [
        (PaieQCExtension, "Paie Quebec"),
        (TaxesQCExtension, "Remise TPS/TVQ"),
        (DpaQCExtension, "DPA/CCA"),
        (PretActionnaireExtension, "Pret actionnaire"),
        (ExportCPAExtension, "Export CPA"),
        (EcheancesExtension, "Echeances"),
        (RecusExtension, "Recus"),
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
        EcheancesExtension,
        RecusExtension,
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
        "src/compteqc/fava_ext/echeances/templates/EcheancesExtension.html",
        "src/compteqc/fava_ext/recus/templates/RecusExtension.html",
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
    """main.beancount contient 12 directives fava-extension."""
    main_path = PROJECT_ROOT / "ledger" / "main.beancount"
    assert main_path.exists(), "ledger/main.beancount manquant"

    content = main_path.read_text()
    extension_lines = [
        line for line in content.splitlines()
        if 'fava-extension' in line and line.strip().startswith("2010")
    ]
    assert len(extension_lines) == 12, (
        f"Attendu 12 directives fava-extension, trouve {len(extension_lines)}: {extension_lines}"
    )


def test_main_beancount_has_specific_extensions():
    """main.beancount contient les 8 extensions specifiques."""
    main_path = PROJECT_ROOT / "ledger" / "main.beancount"
    content = main_path.read_text()

    expected = [
        "compteqc.fava_ext.approbation",
        "compteqc.fava_ext.paie_qc",
        "compteqc.fava_ext.taxes_qc",
        "compteqc.fava_ext.dpa_qc",
        "compteqc.fava_ext.pret_actionnaire",
        "compteqc.fava_ext.export_cpa",
        "compteqc.fava_ext.echeances",
        "compteqc.fava_ext.recus",
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


def test_taxes_extension_preparation_defaults_to_last_completed_quarter():
    """L'extension utilise le dernier trimestre complet et expose les options de navigation."""
    entries, errors, _ = beancount_parser.parse_string(
        """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2026-01-01 open Actifs:Banque:RBC:Cheques CAD
2026-01-01 open Actifs:TPS-Payee CAD
2026-01-01 open Actifs:TVQ-Payee CAD
2026-01-01 open Passifs:TPS-Percue CAD
2026-01-01 open Passifs:TVQ-Percue CAD
2026-01-01 open Revenus:Consultation CAD
2026-01-01 open Depenses:Bureau:Abonnements-Logiciels CAD

2026-01-15 * "Client ABC" "Facture janvier"
  Actifs:Banque:RBC:Cheques  1149.75 CAD
  Revenus:Consultation  -1000.00 CAD
  Passifs:TPS-Percue  -50.00 CAD
  Passifs:TVQ-Percue  -99.75 CAD
"""
    )
    assert not errors

    ext = TaxesQCExtension.__new__(TaxesQCExtension)
    ext.ledger = type(
        "LedgerStub",
        (),
        {
            "all_entries": entries,
            "beancount_file_path": str(PROJECT_ROOT / "ledger" / "main.beancount"),
        },
    )()
    ext._date_reference = datetime.date(2026, 4, 4)

    preparation = ext.preparation()
    options = ext.period_options()

    assert preparation.periode.code == "2026-Q1"
    assert preparation.sommaire.tps_percue == 50
    assert any(option["code"] == "2026-Q1" and option["selected"] for option in options)


def test_taxes_extension_surfaces_revenue_anomalies(tmp_path, monkeypatch):
    """Le tab de remise avertit quand un depot revenu brut n'a pas de split TPS/TVQ."""
    entries, errors, _ = beancount_parser.parse_string(
        """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2026-01-01 open Actifs:Banque:RBC:Cheques CAD
2026-01-01 open Revenus:Consultation CAD

2026-03-11 * "Client Web" "Paiement projet site web"
  Actifs:Banque:RBC:Cheques  2299.50 CAD
  Revenus:Consultation      -2299.50 CAD
"""
    )
    assert not errors
    (tmp_path / "ledger" / "documents").mkdir(parents=True)
    (tmp_path / "ledger" / "documents" / "registre.yaml").write_text("[]", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    ext = TaxesQCExtension.__new__(TaxesQCExtension)
    ext.ledger = type(
        "LedgerStub",
        (),
        {"all_entries": entries, "beancount_file_path": str(tmp_path / "ledger" / "main.beancount")},
    )()
    ext._date_reference = datetime.date(2026, 4, 5)

    preparation = ext.preparation()

    assert preparation.nb_anomalies_revenus == 1
    assert any(
        avertissement.titre == "Revenus sans split fiscal explicite"
        for avertissement in preparation.avertissements
    )


def test_dashboard_and_mcp_share_revenue_anomaly_count(tmp_path, monkeypatch):
    """Le tableau de bord et le sommaire MCP utilisent le meme audit revenus/taxes."""
    entries, errors, _ = beancount_parser.parse_string(
        """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2026-01-01 open Actifs:Banque:RBC:Cheques CAD
2026-01-01 open Revenus:Consultation CAD

2026-03-11 * "Client Web" "Paiement projet site web"
  Actifs:Banque:RBC:Cheques  2299.50 CAD
  Revenus:Consultation      -2299.50 CAD
"""
    )
    assert not errors
    ledger_root = tmp_path / "ledger"
    (ledger_root / "documents").mkdir(parents=True)
    (ledger_root / "documents" / "registre.yaml").write_text("[]", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    dashboard = TableauBordExtension.__new__(TableauBordExtension)
    dashboard.ledger = type(
        "LedgerStub",
        (),
        {"all_entries": entries, "beancount_file_path": str(ledger_root / "main.beancount")},
    )()
    dashboard._kpis = {}
    dashboard._compute_kpis()

    ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            lifespan_context=SimpleNamespace(
                entries=entries,
                ledger_path=str(ledger_root / "main.beancount"),
            )
        )
    )
    resultat_mcp = sommaire_tps_tvq("2026-Q1", ctx=ctx)

    assert dashboard.kpis()["revenus_taxe_review_count"] == 1
    assert resultat_mcp["anomalies_revenus_count"] == 1


def test_fava_surfaces_use_ledger_relative_registry_not_cwd(tmp_path, monkeypatch):
    """Le tableau de bord et la remise lisent le registre depuis le ledger actif, pas le cwd."""
    entries, errors, _ = beancount_parser.parse_string(
        """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2026-01-01 open Actifs:Banque:RBC:Cheques CAD
2026-01-01 open Revenus:Consultation CAD

2026-03-11 * "Client Web" "Paiement projet site web"
  Actifs:Banque:RBC:Cheques  1149.75 CAD
  Revenus:Consultation      -1149.75 CAD
"""
    )
    assert not errors

    ledger_root = tmp_path / "ledger"
    (ledger_root / "documents").mkdir(parents=True)
    (ledger_root / "documents" / "registre.yaml").write_text(
        """\
- id: doc-123
  chemin_document: documents/2026/04/revenu.pdf
  nom_fichier: revenu.pdf
  fournisseur: Client Web
  date: "2026-03-11"
  sous_total: "1000.00"
  montant_tps: "50.00"
  montant_tvq: "99.75"
  total: "1149.75"
  description: Services
  confiance: 0.9
  document_kind: revenue
  pricing_mode: explicit_tax_lines
  normalization_status: unmatched
  matched_transaction_ref:
  traitement_taxes:
  review_reason:
  created_at: "2026-04-05T10:00:00"
  updated_at: "2026-04-05T10:00:00"
""",
        encoding="utf-8",
    )
    other_cwd = tmp_path / "autre-cwd"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    dashboard = TableauBordExtension.__new__(TableauBordExtension)
    dashboard.ledger = type(
        "LedgerStub",
        (),
        {"all_entries": entries, "beancount_file_path": str(ledger_root / "main.beancount")},
    )()
    dashboard._kpis = {}
    dashboard._compute_kpis()

    ext = TaxesQCExtension.__new__(TaxesQCExtension)
    ext.ledger = type(
        "LedgerStub",
        (),
        {"all_entries": entries, "beancount_file_path": str(ledger_root / "main.beancount")},
    )()
    ext._date_reference = datetime.date(2026, 4, 5)

    assert dashboard.kpis()["revenus_taxe_review_count"] == 2
    assert ext.preparation().nb_anomalies_revenus == 2
