"""Tests pour les importateurs RBC (CSV cheques, CSV carte credit)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.core import data

from compteqc.ingestion.normalisation import (
    archiver_fichier,
    detecter_encodage,
    nettoyer_beneficiaire,
)
from compteqc.ingestion.rbc_carte import RBCCarteImporter
from compteqc.ingestion.rbc_cheques import RBCChequesImporter

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Tests nettoyer_beneficiaire
# ---------------------------------------------------------------------------


class TestNettoyerBeneficiaire:
    def test_normalise_espaces(self):
        assert nettoyer_beneficiaire("  CAFE   XYZ  ") == "Cafe Xyz"

    def test_retire_reference_fin(self):
        assert nettoyer_beneficiaire("PAIEMENT INTERAC   CAFE XYZ  REF87654") == "Paiement Interac Cafe Xyz"

    def test_retire_numero_long(self):
        assert nettoyer_beneficiaire("BELL CANADA 1234567") == "Bell Canada"

    def test_conserve_numero_court(self):
        # Les numeros de moins de 5 chiffres ne sont pas retires
        assert nettoyer_beneficiaire("ACME INC 42") == "Acme Inc 42"

    def test_title_case(self):
        assert nettoyer_beneficiaire("AWS AMAZON COM  SEATTLE WA") == "Aws Amazon Com Seattle Wa"


# ---------------------------------------------------------------------------
# Tests detecter_encodage
# ---------------------------------------------------------------------------


class TestDetecterEncodage:
    def test_utf8(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("hello,world\n", encoding="utf-8")
        assert detecter_encodage(f) == "utf-8"

    def test_latin1(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_bytes("caf\xe9\n".encode("latin-1"))
        assert detecter_encodage(f) in ("utf-8", "latin-1")


# ---------------------------------------------------------------------------
# Tests archiver_fichier
# ---------------------------------------------------------------------------


class TestArchiverFichier:
    def test_archive_copie_fichier(self, tmp_path):
        source = tmp_path / "original.csv"
        source.write_text("data,here\n")
        dest_dir = tmp_path / "processed"

        result = archiver_fichier(source, dest_dir, nombre_transactions=5)

        assert result.exists()
        assert result.name == "original.csv"
        assert result.read_text() == "data,here\n"

    def test_archive_cree_meta_json(self, tmp_path):
        source = tmp_path / "original.csv"
        source.write_text("data,here\n")
        dest_dir = tmp_path / "processed"

        result = archiver_fichier(source, dest_dir, nombre_transactions=5)

        meta_path = result.with_suffix(".csv.meta.json")
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["nombre_transactions"] == 5
        assert "hash_sha256" in meta
        assert "date_import" in meta
        assert "chemin_original" in meta


# ---------------------------------------------------------------------------
# Tests RBCChequesImporter
# ---------------------------------------------------------------------------


class TestRBCChequesImporter:
    @pytest.fixture
    def importer(self):
        return RBCChequesImporter()

    def test_identify_bon_fichier(self, importer):
        assert importer.identify(str(FIXTURES / "rbc_cheques_sample.csv")) is True

    def test_identify_mauvais_fichier(self, importer):
        assert importer.identify(str(FIXTURES / "rbc_carte_sample.csv")) is False

    def test_identify_non_csv(self, importer, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("not a csv")
        assert importer.identify(str(f)) is False

    def test_account(self, importer):
        assert importer.account("any") == "Actifs:Banque:RBC:Cheques"

    def test_extract_nombre_transactions(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_cheques_sample.csv"), [])
        assert len(txns) == 8

    def test_extract_montants_decimal(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_cheques_sample.csv"), [])
        for txn in txns:
            for posting in txn.postings:
                assert isinstance(posting.units.number, Decimal)

    def test_extract_deux_postings(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_cheques_sample.csv"), [])
        for txn in txns:
            assert len(txn.postings) == 2

    def test_extract_postings_balancent(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_cheques_sample.csv"), [])
        for txn in txns:
            total = sum(p.units.number for p in txn.postings)
            assert total == Decimal("0")

    def test_extract_flag_en_attente(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_cheques_sample.csv"), [])
        for txn in txns:
            assert txn.flag == "!"

    def test_extract_metadata(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_cheques_sample.csv"), [])
        for txn in txns:
            assert txn.meta["source"] == "rbc-cheques-csv"
            assert txn.meta["categorisation"] == "non-classe"

    def test_deduplication_meme_fichier(self, importer):
        """Importer deux fois le meme fichier retourne 0 nouvelles transactions."""
        filepath = str(FIXTURES / "rbc_cheques_sample.csv")
        txns1 = importer.extract(filepath, [])
        assert len(txns1) == 8

        # Re-importer avec les transactions precedentes comme existing
        txns2 = importer.extract(filepath, txns1)
        assert len(txns2) == 0

    def test_extract_comptes_corrects(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_cheques_sample.csv"), [])
        for txn in txns:
            assert txn.postings[0].account == "Actifs:Banque:RBC:Cheques"
            assert txn.postings[1].account == "Depenses:Non-Classe"


# ---------------------------------------------------------------------------
# Tests RBCCarteImporter
# ---------------------------------------------------------------------------


class TestRBCCarteImporter:
    @pytest.fixture
    def importer(self):
        return RBCCarteImporter()

    def test_identify_bon_fichier(self, importer):
        assert importer.identify(str(FIXTURES / "rbc_carte_sample.csv")) is True

    def test_identify_mauvais_fichier(self, importer):
        assert importer.identify(str(FIXTURES / "rbc_cheques_sample.csv")) is False

    def test_account(self, importer):
        assert importer.account("any") == "Passifs:CartesCredit:RBC"

    def test_extract_nombre_transactions(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_carte_sample.csv"), [])
        assert len(txns) == 8

    def test_extract_montants_decimal(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_carte_sample.csv"), [])
        for txn in txns:
            for posting in txn.postings:
                assert isinstance(posting.units.number, Decimal)

    def test_extract_deux_postings(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_carte_sample.csv"), [])
        for txn in txns:
            assert len(txn.postings) == 2

    def test_extract_postings_balancent(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_carte_sample.csv"), [])
        for txn in txns:
            total = sum(p.units.number for p in txn.postings)
            assert total == Decimal("0")

    def test_extract_flag_en_attente(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_carte_sample.csv"), [])
        for txn in txns:
            assert txn.flag == "!"

    def test_carte_achat_signes_corrects(self, importer):
        """Un achat (positif dans CSV) doit crediter la carte et debiter la depense."""
        txns = importer.extract(str(FIXTURES / "rbc_carte_sample.csv"), [])
        # Premier txn est un achat de 45.67
        achat = txns[0]
        # Posting carte credit: negatif (credit = augmente le passif)
        assert achat.postings[0].units.number == Decimal("-45.67")
        # Posting depense: positif (debit)
        assert achat.postings[1].units.number == Decimal("45.67")

    def test_carte_paiement_signes_corrects(self, importer):
        """Un paiement (negatif dans CSV) doit debiter la carte et crediter la depense."""
        txns = importer.extract(str(FIXTURES / "rbc_carte_sample.csv"), [])
        # 5eme txn est un paiement de -2500.00
        paiement = txns[4]
        # Posting carte credit: positif (debit = diminue le passif)
        assert paiement.postings[0].units.number == Decimal("2500.00")
        # Posting contrepartie: negatif
        assert paiement.postings[1].units.number == Decimal("-2500.00")

    def test_deduplication_meme_fichier(self, importer):
        filepath = str(FIXTURES / "rbc_carte_sample.csv")
        txns1 = importer.extract(filepath, [])
        assert len(txns1) == 8
        txns2 = importer.extract(filepath, txns1)
        assert len(txns2) == 0

    def test_extract_metadata(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_carte_sample.csv"), [])
        for txn in txns:
            assert txn.meta["source"] == "rbc-carte-csv"
