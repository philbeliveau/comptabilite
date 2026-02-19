"""Tests pour le module de generation de rapports financiers (CSV + PDF).

Couvre les trois rapports financiers (balance, resultats, bilan),
la validation GIFI et l'export CSV GIFI.
"""

from __future__ import annotations

import csv
import os
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.parser.parser import parse_string

from compteqc.rapports.balance_verification import BalanceVerification
from compteqc.rapports.bilan import Bilan
from compteqc.rapports.etat_resultats import EtatResultats
from compteqc.rapports.gifi_export import (
    GIFIValidationResult,
    aggregate_by_gifi,
    export_gifi_csv,
    extract_gifi_map,
    validate_gifi,
)

# ---------------------------------------------------------------------------
# Fixture: entrees Beancount de test avec soldes connus et metadata GIFI
# ---------------------------------------------------------------------------

BEANCOUNT_TEST = """\
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"

2025-01-01 open Actifs:Banque:RBC CAD
  gifi: "1001"

2025-01-01 open Actifs:ComptesClients CAD
  gifi: "1060"

2025-01-01 open Passifs:CartesCredit CAD
  gifi: "2700"

2025-01-01 open Capital:Actions CAD
  gifi: "3500"

2025-01-01 open Revenus:Consultation CAD
  gifi: "8000"

2025-01-01 open Revenus:Produit CAD
  gifi: "8000"

2025-01-01 open Depenses:Bureau:Loyer CAD
  gifi: "8810"

2025-01-01 open Depenses:Bureau:Internet CAD
  gifi: "8811"

2025-01-01 open Depenses:Salaires:Brut CAD
  gifi: "8960"

; Mise de fonds initiale
2025-01-01 * "Mise de fonds" "Apport initial"
  Actifs:Banque:RBC  10000.00 CAD
  Capital:Actions  -10000.00 CAD

; Revenu de consultation
2025-02-01 * "Client ABC" "Consultation janvier"
  Actifs:Banque:RBC  5000.00 CAD
  Revenus:Consultation  -5000.00 CAD

; Revenu produit logiciel
2025-02-15 * "Stripe" "Ventes Enact fevrier"
  Actifs:Banque:RBC  1000.00 CAD
  Revenus:Produit  -1000.00 CAD

; Depense loyer
2025-02-01 * "Proprio" "Loyer bureau fevrier"
  Depenses:Bureau:Loyer  800.00 CAD
  Actifs:Banque:RBC  -800.00 CAD

; Depense internet
2025-02-01 * "Bell" "Internet fevrier"
  Depenses:Bureau:Internet  100.00 CAD
  Actifs:Banque:RBC  -100.00 CAD

; Depense salaire
2025-02-28 * "Paie" "Salaire brut fevrier"
  Depenses:Salaires:Brut  3000.00 CAD
  Actifs:Banque:RBC  -3000.00 CAD

; Achat sur carte de credit
2025-03-01 * "Amazon" "Fournitures bureau"
  Depenses:Bureau:Internet  50.00 CAD
  Passifs:CartesCredit  -50.00 CAD
"""


@pytest.fixture
def entries():
    """Entrees Beancount de test avec soldes connus."""
    entries_list, errors, options = parse_string(BEANCOUNT_TEST)
    assert not errors, f"Erreurs de parsing: {errors}"
    return entries_list


@pytest.fixture
def weasyprint_available():
    """Skip test if WeasyPrint system libs not available."""
    try:
        # Set DYLD path for macOS homebrew
        if "DYLD_FALLBACK_LIBRARY_PATH" not in os.environ:
            homebrew_lib = "/opt/homebrew/lib"
            if Path(homebrew_lib).exists():
                os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = homebrew_lib
        from weasyprint import HTML  # noqa: F401
    except OSError:
        pytest.skip("WeasyPrint system libraries (pango/gobject) not available")


# ===========================================================================
# Tests: Balance de verification
# ===========================================================================


class TestBalanceVerification:
    """Tests pour le rapport de balance de verification."""

    def test_balance_csv_columns(self, entries, tmp_path):
        """CSV a 4 colonnes: Compte, GIFI, Debit, Credit."""
        rapport = BalanceVerification(entries, annee=2025)
        csv_path = rapport.to_csv(tmp_path / "balance.csv")
        assert csv_path.exists()

        with open(csv_path) as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert headers == ["Compte", "GIFI", "Debit", "Credit"]

    def test_balance_totals_match(self, entries, tmp_path):
        """Total debits == Total credits dans la sortie CSV."""
        rapport = BalanceVerification(entries, annee=2025)
        csv_path = rapport.to_csv(tmp_path / "balance.csv")

        with open(csv_path) as f:
            reader = csv.reader(f)
            next(reader)  # skip headers
            rows = list(reader)

        # Derniere ligne = TOTAL
        total_row = rows[-1]
        assert total_row[0] == "TOTAL"
        total_debit = Decimal(total_row[2])
        total_credit = Decimal(total_row[3])
        assert total_debit == total_credit

    def test_balance_data_equilibre(self, entries):
        """extract_data() indique que la balance est equilibree."""
        rapport = BalanceVerification(entries, annee=2025)
        d = rapport.data
        assert d["equilibre"] is True
        assert d["total_debit"] == d["total_credit"]

    def test_balance_pdf_renders(self, entries, tmp_path, weasyprint_available):
        """PDF genere sans erreur et commence par %PDF."""
        rapport = BalanceVerification(entries, annee=2025, entreprise="Test Inc.")
        pdf_path = rapport.to_pdf(tmp_path / "balance.pdf")
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"


# ===========================================================================
# Tests: Etat des resultats
# ===========================================================================


class TestEtatResultats:
    """Tests pour le rapport de l'etat des resultats."""

    def test_resultats_csv_has_revenue_and_expenses(self, entries, tmp_path):
        """CSV contient les sections revenus et depenses."""
        rapport = EtatResultats(entries, annee=2025)
        csv_path = rapport.to_csv(tmp_path / "resultats.csv")

        with open(csv_path) as f:
            content = f.read()

        assert "--- REVENUS ---" in content
        assert "--- DEPENSES ---" in content
        assert "RESULTAT NET" in content

    def test_resultats_net_income_correct(self, entries):
        """Resultat net = Revenus - Depenses avec les montants de test."""
        rapport = EtatResultats(entries, annee=2025)
        d = rapport.data

        # Revenus: 5000 (consultation) + 1000 (produit) = 6000
        assert d["total_revenus"] == Decimal("6000.00")

        # Depenses: 800 (loyer) + 100 (internet) + 50 (internet CC) + 3000 (salaire) = 3950
        assert d["total_depenses"] == Decimal("3950.00")

        # Net = 6000 - 3950 = 2050
        assert d["resultat_net"] == Decimal("2050.00")

    def test_resultats_pdf_renders(self, entries, tmp_path, weasyprint_available):
        """PDF genere sans erreur."""
        rapport = EtatResultats(entries, annee=2025, entreprise="Test Inc.")
        pdf_path = rapport.to_pdf(tmp_path / "resultats.pdf")
        assert pdf_path.exists()
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"


# ===========================================================================
# Tests: Bilan
# ===========================================================================


class TestBilan:
    """Tests pour le rapport du bilan."""

    def test_bilan_equation_balanced(self, entries):
        """Actifs = Passifs + Capitaux propres dans la sortie."""
        rapport = Bilan(entries, annee=2025)
        d = rapport.data
        assert d["equilibre"] is True
        assert d["total_actifs"] == d["total_passifs_capitaux"]

    def test_bilan_includes_net_income(self, entries):
        """Resultat net apparait sous capitaux propres."""
        rapport = Bilan(entries, annee=2025)
        d = rapport.data
        assert d["resultat_net"] == Decimal("2050.00")

    def test_bilan_csv_sections(self, entries, tmp_path):
        """CSV contient les trois sections du bilan."""
        rapport = Bilan(entries, annee=2025)
        csv_path = rapport.to_csv(tmp_path / "bilan.csv")

        with open(csv_path) as f:
            content = f.read()

        assert "--- ACTIFS ---" in content
        assert "--- PASSIFS ---" in content
        assert "--- CAPITAUX PROPRES ---" in content
        assert "Resultat net de l'exercice" in content

    def test_bilan_pdf_renders(self, entries, tmp_path, weasyprint_available):
        """PDF genere sans erreur."""
        rapport = Bilan(entries, annee=2025, entreprise="Test Inc.")
        pdf_path = rapport.to_pdf(tmp_path / "bilan.pdf")
        assert pdf_path.exists()
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"


# ===========================================================================
# Tests: BaseReport.generate()
# ===========================================================================


class TestGenerate:
    """Tests pour la methode generate() qui produit CSV + PDF."""

    def test_generate_creates_both(self, entries, tmp_path, weasyprint_available):
        """generate() cree a la fois le CSV et le PDF."""
        rapport = BalanceVerification(entries, annee=2025, entreprise="Test Inc.")
        result = rapport.generate(tmp_path)
        assert "csv" in result
        assert "pdf" in result
        assert result["csv"].exists()
        assert result["pdf"].exists()


# ===========================================================================
# Tests: GIFI
# ===========================================================================


class TestGIFI:
    """Tests pour la validation et l'export GIFI."""

    def test_extract_gifi_map_from_entries(self, entries):
        """Lecture des codes GIFI depuis les directives Open."""
        gifi_map = extract_gifi_map(entries)
        assert gifi_map["Actifs:Banque:RBC"] == "1001"
        assert gifi_map["Revenus:Consultation"] == "8000"
        assert gifi_map["Depenses:Bureau:Loyer"] == "8810"
        assert gifi_map["Capital:Actions"] == "3500"
        assert len(gifi_map) == 9  # 9 comptes avec GIFI

    def test_validate_gifi_balanced(self, entries):
        """Validation passe quand l'equation balance."""
        from compteqc.mcp.services import calculer_soldes

        soldes = calculer_soldes(entries)
        gifi_map = extract_gifi_map(entries)
        result = validate_gifi(soldes, gifi_map)
        assert result.balanced is True
        assert len(result.errors) == 0

    def test_validate_gifi_imbalanced(self, entries):
        """Validation echoue quand l'equation ne balance pas."""
        from compteqc.mcp.services import calculer_soldes

        soldes = calculer_soldes(entries)
        # Ajouter un montant fantome pour desequilibrer
        soldes["Actifs:Fantome"] = Decimal("999.99")
        gifi_map = extract_gifi_map(entries)
        result = validate_gifi(soldes, gifi_map)
        assert result.balanced is False
        assert len(result.errors) >= 1
        assert "desequilibree" in result.errors[0].lower()

    def test_aggregate_by_gifi_sums_correctly(self, entries):
        """Deux comptes avec le meme GIFI sont additionnes."""
        from compteqc.mcp.services import calculer_soldes

        soldes = calculer_soldes(entries)
        gifi_map = extract_gifi_map(entries)
        gifi_balances = aggregate_by_gifi(soldes, gifi_map)

        # Revenus:Consultation (-5000) et Revenus:Produit (-1000) -> GIFI 8000 = -6000
        assert gifi_balances["8000"] == Decimal("-6000.00")

        # Depenses:Bureau:Internet (150) -> GIFI 8811, but check sum
        assert "8811" in gifi_balances

    def test_export_gifi_csv_format(self, entries, tmp_path):
        """CSV GIFI a le format GIFI_CODE,AMOUNT,SCHEDULE avec 2 decimales."""
        from compteqc.mcp.services import calculer_soldes

        soldes = calculer_soldes(entries)
        gifi_map = extract_gifi_map(entries)
        gifi_balances = aggregate_by_gifi(soldes, gifi_map)
        csv_path = export_gifi_csv(gifi_balances, tmp_path / "gifi.csv")

        assert csv_path.exists()
        with open(csv_path) as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert headers == ["GIFI_CODE", "AMOUNT", "SCHEDULE"]
            rows = list(reader)

        # Verifier que les montants ont 2 decimales
        for row in rows:
            amount = row[1]
            assert "." in amount
            assert len(amount.split(".")[1]) == 2

    def test_export_gifi_skips_zero(self, tmp_path):
        """Les soldes GIFI a zero ne sont pas dans la sortie."""
        gifi_balances = {
            "1001": Decimal("5000.00"),
            "8000": Decimal("0"),
            "8810": Decimal("800.00"),
        }
        csv_path = export_gifi_csv(gifi_balances, tmp_path / "gifi.csv")

        with open(csv_path) as f:
            reader = csv.reader(f)
            next(reader)  # headers
            codes = [row[0] for row in reader]

        assert "1001" in codes
        assert "8810" in codes
        assert "8000" not in codes  # zero balance excluded

    def test_gifi_totals_match_trial_balance(self, entries):
        """Somme des GIFI agrege == total balance de verification."""
        from compteqc.mcp.services import calculer_soldes

        soldes = calculer_soldes(entries)
        gifi_map = extract_gifi_map(entries)
        gifi_balances = aggregate_by_gifi(soldes, gifi_map)

        # En beancount, la somme de TOUS les soldes devrait etre 0
        total_gifi = sum(gifi_balances.values())
        total_soldes = sum(v for v in soldes.values() if v != Decimal("0"))
        assert total_gifi == total_soldes
