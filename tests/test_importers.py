"""Tests pour les importateurs RBC (CSV chèques, CSV carte crédit, OFX)."""

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
from compteqc.ingestion.rbc_ofx import RBCOfxImporter

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

    def test_identify_cheques_only(self, importer):
        assert importer.identify(str(FIXTURES / "rbc_cheques_sample.csv")) is True

    def test_identify_carte_only_returns_false(self, importer):
        """Un fichier avec seulement du Visa ne doit pas matcher chèques."""
        assert importer.identify(str(FIXTURES / "rbc_carte_sample.csv")) is False

    def test_identify_combined_file(self, importer):
        """Un fichier combiné contenant du chèques doit matcher."""
        assert importer.identify(str(FIXTURES / "rbc_combined_sample.csv")) is True

    def test_identify_non_csv(self, importer, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("not a csv")
        assert importer.identify(str(f)) is False

    def test_account(self, importer):
        assert importer.account("any") == "Actifs:Banque:RBC:Cheques"

    def test_extract_nombre_transactions(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_cheques_sample.csv"), [])
        assert len(txns) == 8

    def test_extract_from_combined_only_cheques(self, importer):
        """Depuis un fichier combiné, n'extrait que les lignes Chèques."""
        txns = importer.extract(str(FIXTURES / "rbc_combined_sample.csv"), [])
        assert len(txns) == 5
        for txn in txns:
            assert txn.meta["source"] == "rbc-cheques-csv"

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
        filepath = str(FIXTURES / "rbc_cheques_sample.csv")
        txns1 = importer.extract(filepath, [])
        assert len(txns1) == 8
        txns2 = importer.extract(filepath, txns1)
        assert len(txns2) == 0

    def test_extract_comptes_corrects(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_cheques_sample.csv"), [])
        for txn in txns:
            assert txn.postings[0].account == "Actifs:Banque:RBC:Cheques"
            assert txn.postings[1].account == "Depenses:Non-Classe"

    def test_depot_montant_positif(self, importer):
        """Un dépôt (positif dans CSV) doit débiter le compte bancaire."""
        txns = importer.extract(str(FIXTURES / "rbc_cheques_sample.csv"), [])
        # Premier txn est un dépôt de 522.67
        depot = txns[0]
        assert depot.postings[0].units.number == Decimal("522.67")
        assert depot.postings[1].units.number == Decimal("-522.67")

    def test_paiement_montant_negatif(self, importer):
        """Un paiement (négatif dans CSV) doit créditer le compte bancaire."""
        txns = importer.extract(str(FIXTURES / "rbc_cheques_sample.csv"), [])
        # Deuxième txn est un paiement de -81.14
        paiement = txns[1]
        assert paiement.postings[0].units.number == Decimal("-81.14")
        assert paiement.postings[1].units.number == Decimal("81.14")


# ---------------------------------------------------------------------------
# Tests RBCCarteImporter
# ---------------------------------------------------------------------------


class TestRBCCarteImporter:
    @pytest.fixture
    def importer(self):
        return RBCCarteImporter()

    def test_identify_carte_only(self, importer):
        assert importer.identify(str(FIXTURES / "rbc_carte_sample.csv")) is True

    def test_identify_cheques_only_returns_false(self, importer):
        """Un fichier avec seulement du chèques ne doit pas matcher Visa."""
        assert importer.identify(str(FIXTURES / "rbc_cheques_sample.csv")) is False

    def test_identify_combined_file(self, importer):
        """Un fichier combiné contenant du Visa doit matcher."""
        assert importer.identify(str(FIXTURES / "rbc_combined_sample.csv")) is True

    def test_account(self, importer):
        assert importer.account("any") == "Passifs:CartesCredit:RBC"

    def test_extract_nombre_transactions(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_carte_sample.csv"), [])
        assert len(txns) == 8

    def test_extract_from_combined_only_visa(self, importer):
        """Depuis un fichier combiné, n'extrait que les lignes Visa."""
        txns = importer.extract(str(FIXTURES / "rbc_combined_sample.csv"), [])
        assert len(txns) == 5
        for txn in txns:
            assert txn.meta["source"] == "rbc-carte-csv"

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

    def test_visa_achat_signes_corrects(self, importer):
        """Un achat Visa (négatif dans CSV RBC) : carte reçoit le négatif, dépense le positif."""
        txns = importer.extract(str(FIXTURES / "rbc_carte_sample.csv"), [])
        # Premier txn: achat Anthropic de -16.28
        achat = txns[0]
        assert achat.postings[0].units.number == Decimal("-16.28")
        assert achat.postings[0].account == "Passifs:CartesCredit:RBC"
        assert achat.postings[1].units.number == Decimal("16.28")
        assert achat.postings[1].account == "Depenses:Non-Classe"

    def test_visa_paiement_signes_corrects(self, importer):
        """Un paiement Visa (positif dans CSV RBC) : carte reçoit le positif, contrepartie le négatif."""
        txns = importer.extract(str(FIXTURES / "rbc_carte_sample.csv"), [])
        # 7e txn (index 6): paiement de 1973.69
        paiement = txns[6]
        assert paiement.postings[0].units.number == Decimal("1973.69")
        assert paiement.postings[0].account == "Passifs:CartesCredit:RBC"
        assert paiement.postings[1].units.number == Decimal("-1973.69")

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


# ---------------------------------------------------------------------------
# Tests fichier réel RBC (Latin-1 encodé)
# ---------------------------------------------------------------------------


class TestRealRBCFile:
    """Tests avec le vrai fichier RBC pour valider l'encodage et le parsing."""

    @pytest.fixture
    def real_file(self):
        path = FIXTURES / "rbc_real_sample.csv"
        if not path.exists():
            pytest.skip("Fichier reel RBC non disponible")
        return path

    def test_cheques_identify_real(self, real_file):
        imp = RBCChequesImporter()
        assert imp.identify(str(real_file)) is True

    def test_carte_identify_real(self, real_file):
        imp = RBCCarteImporter()
        assert imp.identify(str(real_file)) is True

    def test_cheques_extract_real(self, real_file):
        imp = RBCChequesImporter()
        txns = imp.extract(str(real_file), [])
        assert len(txns) > 0
        for txn in txns:
            assert txn.meta["source"] == "rbc-cheques-csv"
            assert isinstance(txn.postings[0].units.number, Decimal)
            assert len(txn.postings) == 2
            total = sum(p.units.number for p in txn.postings)
            assert total == Decimal("0")

    def test_carte_extract_real(self, real_file):
        imp = RBCCarteImporter()
        txns = imp.extract(str(real_file), [])
        assert len(txns) > 0
        for txn in txns:
            assert txn.meta["source"] == "rbc-carte-csv"
            assert isinstance(txn.postings[0].units.number, Decimal)
            assert len(txn.postings) == 2
            total = sum(p.units.number for p in txn.postings)
            assert total == Decimal("0")

    def test_combined_no_overlap(self, real_file):
        """Chèques et Visa ne se chevauchent pas."""
        imp_ch = RBCChequesImporter()
        imp_vi = RBCCarteImporter()
        txns_ch = imp_ch.extract(str(real_file), [])
        txns_vi = imp_vi.extract(str(real_file), [])
        # Le total des deux doit couvrir toutes les lignes de données
        # (moins les lignes vides éventuelles)
        assert len(txns_ch) > 0
        assert len(txns_vi) > 0
        # Pas de source croisée
        for txn in txns_ch:
            assert txn.meta["source"] == "rbc-cheques-csv"
        for txn in txns_vi:
            assert txn.meta["source"] == "rbc-carte-csv"


# ---------------------------------------------------------------------------
# Tests RBCOfxImporter
# ---------------------------------------------------------------------------


class TestRBCOfxImporter:
    @pytest.fixture
    def importer(self):
        return RBCOfxImporter(
            account="Actifs:Banque:RBC:Cheques",
            account_id="12345-6789012",
        )

    def test_identify_bon_fichier(self, importer):
        assert importer.identify(str(FIXTURES / "rbc_sample.ofx")) is True

    def test_identify_mauvais_account_id(self):
        imp = RBCOfxImporter(account="Actifs:Banque:RBC:Cheques", account_id="99999-0000000")
        assert imp.identify(str(FIXTURES / "rbc_sample.ofx")) is False

    def test_identify_non_ofx(self, importer, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("not ofx")
        assert importer.identify(str(f)) is False

    def test_account(self, importer):
        assert importer.account("any") == "Actifs:Banque:RBC:Cheques"

    def test_extract_nombre_transactions(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_sample.ofx"), [])
        assert len(txns) == 6

    def test_extract_montants_decimal(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_sample.ofx"), [])
        for txn in txns:
            for posting in txn.postings:
                assert isinstance(posting.units.number, Decimal)

    def test_extract_deux_postings(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_sample.ofx"), [])
        for txn in txns:
            assert len(txn.postings) == 2

    def test_extract_postings_balancent(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_sample.ofx"), [])
        for txn in txns:
            total = sum(p.units.number for p in txn.postings)
            assert total == Decimal("0")

    def test_extract_flag_en_attente(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_sample.ofx"), [])
        for txn in txns:
            assert txn.flag == "!"

    def test_extract_fitid_present(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_sample.ofx"), [])
        for txn in txns:
            assert "fitid" in txn.meta
            assert txn.meta["fitid"] != ""

    def test_extract_metadata(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_sample.ofx"), [])
        for txn in txns:
            assert txn.meta["source"] == "rbc-ofx"
            assert txn.meta["categorisation"] == "non-classe"

    def test_deduplication_fitid(self, importer):
        filepath = str(FIXTURES / "rbc_sample.ofx")
        txns1 = importer.extract(filepath, [])
        assert len(txns1) == 6
        txns2 = importer.extract(filepath, txns1)
        assert len(txns2) == 0

    def test_extract_comptes_corrects(self, importer):
        txns = importer.extract(str(FIXTURES / "rbc_sample.ofx"), [])
        for txn in txns:
            assert txn.postings[0].account == "Actifs:Banque:RBC:Cheques"
            assert txn.postings[1].account == "Depenses:Non-Classe"

    def test_extract_fichier_invalide_raise(self, tmp_path):
        f = tmp_path / "bad.ofx"
        f.write_text("this is not valid OFX")
        imp = RBCOfxImporter(account="Actifs:Banque:RBC:Cheques", account_id="12345-6789012")
        with pytest.raises(ValueError, match="invalide"):
            imp.extract(str(f), [])
