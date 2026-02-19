"""Tests d'integration pour le moteur de paie et le generateur de journal.

Teste le flux complet: calcul de paie -> generation de transaction Beancount.
"""

from __future__ import annotations

import datetime
import os
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.core import data

from compteqc.quebec.paie.journal import generer_transaction_paie
from compteqc.quebec.paie.moteur import ResultatPaie, calculer_paie


@pytest.fixture()
def ledger_vide(tmp_path: Path) -> str:
    """Cree un ledger vide minimal pour les tests."""
    comptes = tmp_path / "comptes.beancount"
    comptes.write_text(
        'option "name_assets" "Actifs"\n'
        'option "name_liabilities" "Passifs"\n'
        'option "name_equity" "Capital"\n'
        'option "name_income" "Revenus"\n'
        'option "name_expenses" "Depenses"\n'
        '\n'
        '2025-01-01 open Actifs:Banque:RBC:Cheques CAD\n'
        '2025-01-01 open Passifs:Retenues:QPP-Base CAD\n'
        '2025-01-01 open Passifs:Retenues:QPP-Supp1 CAD\n'
        '2025-01-01 open Passifs:Retenues:QPP-Supp2 CAD\n'
        '2025-01-01 open Passifs:Retenues:RQAP CAD\n'
        '2025-01-01 open Passifs:Retenues:AE CAD\n'
        '2025-01-01 open Passifs:Retenues:Impot-Federal CAD\n'
        '2025-01-01 open Passifs:Retenues:Impot-Quebec CAD\n'
        '2025-01-01 open Passifs:Cotisations-Employeur:QPP CAD\n'
        '2025-01-01 open Passifs:Cotisations-Employeur:RQAP CAD\n'
        '2025-01-01 open Passifs:Cotisations-Employeur:AE CAD\n'
        '2025-01-01 open Passifs:Cotisations-Employeur:FSS CAD\n'
        '2025-01-01 open Passifs:Cotisations-Employeur:CNESST CAD\n'
        '2025-01-01 open Passifs:Cotisations-Employeur:Normes-Travail CAD\n'
        '2025-01-01 open Passifs:Pret-Actionnaire CAD\n'
        '2025-01-01 open Depenses:Salaires:Brut CAD\n'
        '2025-01-01 open Depenses:Salaires:RRQ-Employeur CAD\n'
        '2025-01-01 open Depenses:Salaires:RQAP-Employeur CAD\n'
        '2025-01-01 open Depenses:Salaires:AE-Employeur CAD\n'
        '2025-01-01 open Depenses:Salaires:FSS CAD\n'
        '2025-01-01 open Depenses:Salaires:CNESST CAD\n'
        '2025-01-01 open Depenses:Salaires:Normes-Travail CAD\n',
        encoding="utf-8",
    )

    main = tmp_path / "main.beancount"
    main.write_text(
        'option "title" "Test Ledger"\n'
        'option "operating_currency" "CAD"\n'
        'option "name_assets" "Actifs"\n'
        'option "name_liabilities" "Passifs"\n'
        'option "name_equity" "Capital"\n'
        'option "name_income" "Revenus"\n'
        'option "name_expenses" "Depenses"\n'
        '\n'
        'include "comptes.beancount"\n',
        encoding="utf-8",
    )

    return str(main)


class TestCalculerPaie:
    """Tests pour le moteur de paie."""

    def test_calcul_complet_5000_brut(self, ledger_vide: str):
        """$5,000 bi-weekly, period 1, empty ledger -> all fields populated."""
        resultat = calculer_paie(
            brut=Decimal("5000"),
            numero_periode=1,
            chemin_ledger=ledger_vide,
            annee=2026,
            nb_periodes=26,
        )

        assert isinstance(resultat, ResultatPaie)
        assert resultat.brut == Decimal("5000")
        assert resultat.numero_periode == 1
        assert resultat.nb_periodes == 26

        # All deductions should be positive
        assert resultat.qpp_base > Decimal("0")
        assert resultat.qpp_supp1 > Decimal("0")
        assert resultat.rqap > Decimal("0")
        assert resultat.ae > Decimal("0")
        assert resultat.impot_federal > Decimal("0")
        assert resultat.impot_quebec > Decimal("0")

        # All employer contributions should be positive
        assert resultat.qpp_base_employeur > Decimal("0")
        assert resultat.rqap_employeur > Decimal("0")
        assert resultat.ae_employeur > Decimal("0")
        assert resultat.fss > Decimal("0")
        assert resultat.cnesst > Decimal("0")
        assert resultat.normes_travail > Decimal("0")

        # Net = brut - total_retenues
        assert resultat.net == resultat.brut - resultat.total_retenues

        # Total retenues = sum of employee deductions
        attendu = (
            resultat.qpp_base + resultat.qpp_supp1 + resultat.qpp_supp2
            + resultat.rqap + resultat.ae
            + resultat.impot_federal + resultat.impot_quebec
        )
        assert resultat.total_retenues == attendu.quantize(Decimal("0.01"))

        # Net should be reasonable (~$3,000-$4,000 on $5,000 gross)
        assert Decimal("2500") < resultat.net < Decimal("4500")

    def test_tous_champs_sont_decimal(self, ledger_vide: str):
        """Tous les champs monetaires sont des Decimal."""
        resultat = calculer_paie(
            brut=Decimal("5000"),
            numero_periode=1,
            chemin_ledger=ledger_vide,
        )

        champs_monetaires = [
            resultat.brut, resultat.qpp_base, resultat.qpp_supp1,
            resultat.qpp_supp2, resultat.rqap, resultat.ae,
            resultat.impot_federal, resultat.impot_quebec,
            resultat.qpp_base_employeur, resultat.qpp_supp1_employeur,
            resultat.qpp_supp2_employeur, resultat.rqap_employeur,
            resultat.ae_employeur, resultat.fss, resultat.cnesst,
            resultat.normes_travail, resultat.total_retenues,
            resultat.total_cotisations_employeur, resultat.net,
        ]

        for champ in champs_monetaires:
            assert isinstance(champ, Decimal), f"Expected Decimal, got {type(champ)}"


class TestJournalPaie:
    """Tests pour la generation de transactions Beancount."""

    def _resultat_exemple(self) -> ResultatPaie:
        """Cree un ResultatPaie pour les tests de journal."""
        return ResultatPaie(
            brut=Decimal("5000"),
            numero_periode=1,
            nb_periodes=26,
            qpp_base=Decimal("243.46"),
            qpp_supp1=Decimal("28.69"),
            qpp_supp2=Decimal("16.00"),
            rqap=Decimal("17.04"),
            ae=Decimal("34.46"),
            impot_federal=Decimal("572.57"),
            impot_quebec=Decimal("780.84"),
            qpp_base_employeur=Decimal("243.46"),
            qpp_supp1_employeur=Decimal("28.69"),
            qpp_supp2_employeur=Decimal("16.00"),
            rqap_employeur=Decimal("23.85"),
            ae_employeur=Decimal("48.23"),
            fss=Decimal("82.50"),
            cnesst=Decimal("40.00"),
            normes_travail=Decimal("3.00"),
            total_retenues=Decimal("1693.06"),
            total_cotisations_employeur=Decimal("485.73"),
            net=Decimal("3306.94"),
        )

    def test_nombre_de_postings(self):
        """La transaction doit avoir environ 20 postings."""
        resultat = self._resultat_exemple()
        txn = generer_transaction_paie(
            datetime.date(2026, 1, 15), resultat,
        )

        assert isinstance(txn, data.Transaction)
        # 1 brut + 7 retenues + 1 banque + 6 depenses employeur + 6 passifs employeur = 21
        assert len(txn.postings) >= 20

    def test_transaction_equilibree(self):
        """La somme de tous les postings doit etre zero."""
        resultat = self._resultat_exemple()
        txn = generer_transaction_paie(
            datetime.date(2026, 1, 15), resultat,
        )

        total = sum(p.units.number for p in txn.postings)
        assert total == Decimal("0"), f"Transaction desequilibree: {total}"

    def test_narration_contient_paie(self):
        """La narration contient 'Paie #'."""
        resultat = self._resultat_exemple()
        txn = generer_transaction_paie(
            datetime.date(2026, 1, 15), resultat,
        )

        assert "Paie #" in txn.narration
        assert str(resultat.brut) in txn.narration

    def test_tag_paie_present(self):
        """Le tag 'paie' est present."""
        resultat = self._resultat_exemple()
        txn = generer_transaction_paie(
            datetime.date(2026, 1, 15), resultat,
        )

        assert "paie" in txn.tags

    def test_metadata_type_paie(self):
        """Les metadata contiennent le type et la periode."""
        resultat = self._resultat_exemple()
        txn = generer_transaction_paie(
            datetime.date(2026, 1, 15), resultat,
        )

        assert txn.meta["type"] == "paie"
        assert txn.meta["periode"] == "1"
        assert txn.meta["brut"] == "5000"

    def test_salary_offset_ajoute_posting_pret(self):
        """Avec salary_offset, un posting Pret-Actionnaire est ajoute."""
        resultat = self._resultat_exemple()
        offset = Decimal("1000")
        txn = generer_transaction_paie(
            datetime.date(2026, 1, 15), resultat, salary_offset=offset,
        )

        # Find the Pret-Actionnaire posting
        pret_postings = [
            p for p in txn.postings
            if p.account == "Passifs:Pret-Actionnaire"
        ]
        assert len(pret_postings) == 1
        # Credit (negative) reduces the shareholder loan debit balance
        assert pret_postings[0].units.number == Decimal("-1000")

        # Banque posting should be reduced by offset
        banque_postings = [
            p for p in txn.postings
            if p.account == "Actifs:Banque:RBC:Cheques"
        ]
        assert len(banque_postings) == 1
        depot_attendu = -(resultat.net - offset)
        assert banque_postings[0].units.number == depot_attendu

        # Transaction should still balance
        total = sum(p.units.number for p in txn.postings)
        assert total == Decimal("0")

    def test_salary_offset_metadata(self):
        """Le metadata salary_offset est present quand offset fourni."""
        resultat = self._resultat_exemple()
        txn = generer_transaction_paie(
            datetime.date(2026, 1, 15), resultat,
            salary_offset=Decimal("500"),
        )

        assert txn.meta["salary_offset"] == "500"

    def test_salary_offset_depasse_net_raise_error(self):
        """salary_offset > net doit lever ValueError."""
        resultat = self._resultat_exemple()

        with pytest.raises(ValueError, match="ne peut pas depasser"):
            generer_transaction_paie(
                datetime.date(2026, 1, 15), resultat,
                salary_offset=resultat.net + Decimal("1"),
            )

    def test_tous_montants_sont_decimal(self):
        """Tous les montants de postings sont des Decimal."""
        resultat = self._resultat_exemple()
        txn = generer_transaction_paie(
            datetime.date(2026, 1, 15), resultat,
        )

        for posting in txn.postings:
            assert isinstance(posting.units.number, Decimal)
