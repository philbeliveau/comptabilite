"""Tests pour le serveur MCP CompteQC -- services et outils.

Teste la couche services (calculer_soldes, lister_pending) et le comportement
des outils (truncation, read-only) sans tester le transport MCP.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from beancount.parser import parser as beancount_parser

from compteqc.mcp.server import AppContext
from compteqc.mcp.services import calculer_soldes, formater_montant, lister_pending


# ---------- Fixtures ----------

LEDGER_SIMPLE = """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2026-01-01 open Actifs:Banque:Desjardins
2026-01-01 open Revenus:Consultation
2026-01-01 open Depenses:Fournitures
2026-01-01 open Depenses:Repas
2026-01-01 open Passifs:TPS-Percue
2026-01-01 open Passifs:TVQ-Percue
2026-01-01 open Capital:Ouverture

2026-01-15 * "Client ABC" "Facture consultation janvier"
  Actifs:Banque:Desjardins  5000.00 CAD
  Revenus:Consultation      -5000.00 CAD

2026-02-01 * "Amazon" "Fournitures informatiques"
  Depenses:Fournitures  150.00 CAD
  Actifs:Banque:Desjardins  -150.00 CAD

2026-02-15 * "Restaurant Chez Jules" "Repas affaires"
  Depenses:Repas  45.00 CAD
  Actifs:Banque:Desjardins  -45.00 CAD
"""

LEDGER_PENDING = """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2026-01-01 open Actifs:Banque:Desjardins
2026-01-01 open Depenses:Non-Classe

2026-03-01 * "Inconnu" "Transaction mystere" #pending
  confidence: "0.65"
  ai-source: "ml"
  Depenses:Non-Classe  99.99 CAD
  Actifs:Banque:Desjardins  -99.99 CAD

2026-03-02 * "Netflix" "Abonnement" #pending
  confidence: "0.95"
  ai-source: "regle"
  Depenses:Non-Classe  22.99 CAD
  Actifs:Banque:Desjardins  -22.99 CAD

2026-03-03 * "Bell" "Facture internet"
  Depenses:Non-Classe  89.99 CAD
  Actifs:Banque:Desjardins  -89.99 CAD
"""


def _parse(text: str) -> list:
    """Parse un texte Beancount et retourne les entrees."""
    entries, errors, options = beancount_parser.parse_string(text)
    return entries


# ---------- Tests services ----------


class TestCalculerSoldes:
    def test_soldes_complets(self):
        entries = _parse(LEDGER_SIMPLE)
        soldes = calculer_soldes(entries)
        assert soldes["Actifs:Banque:Desjardins"] == Decimal("4805.00")
        assert soldes["Revenus:Consultation"] == Decimal("-5000.00")
        assert soldes["Depenses:Fournitures"] == Decimal("150.00")
        assert soldes["Depenses:Repas"] == Decimal("45.00")

    def test_soldes_avec_filtre(self):
        entries = _parse(LEDGER_SIMPLE)
        soldes = calculer_soldes(entries, filtre="Depenses")
        assert "Actifs:Banque:Desjardins" not in soldes
        assert "Depenses:Fournitures" in soldes
        assert "Depenses:Repas" in soldes

    def test_filtre_insensible_casse(self):
        entries = _parse(LEDGER_SIMPLE)
        soldes = calculer_soldes(entries, filtre="depenses")
        assert "Depenses:Fournitures" in soldes


class TestListerPending:
    def test_trouve_pending(self):
        entries = _parse(LEDGER_PENDING)
        pending = lister_pending(entries)
        assert len(pending) == 2

    def test_metadata_extraite(self):
        entries = _parse(LEDGER_PENDING)
        pending = lister_pending(entries)
        # Trier par date pour stabilite
        pending.sort(key=lambda p: p["date"])
        assert pending[0]["confiance"] == "0.65"
        assert pending[0]["source"] == "ml"
        assert pending[1]["confiance"] == "0.95"
        assert pending[1]["source"] == "regle"

    def test_montant_positif(self):
        entries = _parse(LEDGER_PENDING)
        pending = lister_pending(entries)
        pending.sort(key=lambda p: p["date"])
        assert pending[0]["montant"] == Decimal("99.99")


class TestFormaterMontant:
    def test_format_simple(self):
        assert formater_montant(Decimal("1234.56")) == "1,234.56"

    def test_format_negatif(self):
        assert formater_montant(Decimal("-500.00")) == "-500.00"


# ---------- Tests AppContext ----------


class TestAppContext:
    def test_read_only_flag(self):
        ctx = AppContext(
            ledger_path="fake.beancount",
            entries=[],
            errors=[],
            options={},
            read_only=True,
        )
        assert ctx.read_only is True

    def test_read_write_flag(self):
        ctx = AppContext(
            ledger_path="fake.beancount",
            entries=[],
            errors=[],
            options={},
            read_only=False,
        )
        assert ctx.read_only is False

    def test_reload_refreshes_entries(self, tmp_path):
        """Verifie que reload() recharge les entrees depuis le fichier."""
        ledger_file = tmp_path / "test.beancount"
        ledger_file.write_text(
            'option "name_assets" "Actifs"\n'
            'option "name_liabilities" "Passifs"\n'
            'option "name_equity" "Capital"\n'
            'option "name_income" "Revenus"\n'
            'option "name_expenses" "Depenses"\n'
            '2026-01-01 open Actifs:Banque\n',
            encoding="utf-8",
        )

        ctx = AppContext(
            ledger_path=str(ledger_file),
            entries=[],
            errors=[],
            options={},
            read_only=False,
        )
        assert len(ctx.entries) == 0

        ctx.reload()
        assert len(ctx.entries) > 0  # Au moins l'open directive


# ---------- Tests truncation ----------


class TestTruncation:
    def test_truncation_flag(self):
        """Verifie que les reponses > 50 items ont tronque=True."""
        # Generer un ledger avec plus de 50 comptes
        lines = [
            'option "name_assets" "Actifs"',
            'option "name_liabilities" "Passifs"',
            'option "name_equity" "Capital"',
            'option "name_income" "Revenus"',
            'option "name_expenses" "Depenses"',
        ]
        for i in range(55):
            lines.append(f"2026-01-01 open Depenses:Cat{i:03d}")
        for i in range(55):
            lines.append(
                f'2026-01-{(i % 28) + 1:02d} * "Vendor{i}" "Purchase {i}"\n'
                f"  Depenses:Cat{i:03d}  {10 + i:.2f} CAD\n"
                f"  Actifs:Banque  -{10 + i:.2f} CAD"
            )
        # Also open Actifs:Banque
        lines.insert(5, "2026-01-01 open Actifs:Banque")
        ledger_text = "\n".join(lines)

        entries = _parse(ledger_text)
        soldes = calculer_soldes(entries)

        # Filter to only Depenses to get 55 accounts
        comptes_depenses = {
            k: v for k, v in sorted(soldes.items())
            if k.startswith("Depenses") and v != Decimal("0")
        }
        assert len(comptes_depenses) == 55

        # Simulate what soldes_comptes tool does
        comptes = [
            {"compte": k, "solde": formater_montant(v)}
            for k, v in sorted(comptes_depenses.items())
        ]
        result = {
            "nb_comptes": len(comptes),
            "comptes": comptes[:50],
            "tronque": len(comptes) > 50,
        }
        assert result["tronque"] is True
        assert len(result["comptes"]) == 50
        assert result["nb_comptes"] == 55
