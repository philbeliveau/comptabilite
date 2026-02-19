"""Tests pour le module de gestion des documents (recus, factures).

Les appels a l'API Anthropic sont mockes. Les tests de matching et upload
sont purement logiques (pas de mock necessaire).
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from compteqc.documents.beancount_link import generer_directive_document
from compteqc.documents.extraction import DonneesRecu
from compteqc.documents.matching import Correspondance, proposer_correspondances
from compteqc.documents.upload import renommer_recu, telecharger_recu


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ledger_dir(tmp_path):
    """Repertoire temporaire simulant le ledger."""
    return tmp_path / "ledger"


@pytest.fixture
def sample_jpg(tmp_path):
    """Cree une petite image JPEG de test."""
    img = Image.new("RGB", (100, 80), color="red")
    path = tmp_path / "receipt.jpg"
    img.save(path)
    return path


@pytest.fixture
def large_jpg(tmp_path):
    """Cree une image JPEG trop grande (> 1568px)."""
    img = Image.new("RGB", (3000, 2000), color="blue")
    path = tmp_path / "large_receipt.jpg"
    img.save(path)
    return path


@pytest.fixture
def sample_pdf(tmp_path):
    """Cree un fichier PDF minimal de test."""
    path = tmp_path / "receipt.pdf"
    # Minimal valid PDF
    path.write_bytes(b"%PDF-1.0\n1 0 obj<</Type/Catalog>>endobj\n%%EOF")
    return path


@pytest.fixture
def donnees_recu():
    """DonneesRecu de test standard."""
    return DonneesRecu(
        fournisseur="Bureau en Gros",
        date="2026-01-15",
        sous_total=Decimal("42.50"),
        montant_tps=Decimal("2.13"),
        montant_tvq=Decimal("4.24"),
        total=Decimal("48.87"),
        description="Fournitures de bureau",
        confiance=0.92,
    )


def _make_beancount_txn(date, narration, amount, account="Depenses:Bureau:Fournitures"):
    """Cree un mock de Transaction Beancount."""
    from beancount.core import amount as beancount_amount
    from beancount.core import data as beancount_data

    units = beancount_amount.Amount(Decimal(str(amount)), "CAD")
    posting = beancount_data.Posting(
        account=account,
        units=units,
        cost=None,
        price=None,
        flag=None,
        meta=None,
    )
    meta = beancount_data.new_metadata("test", 1)
    txn = beancount_data.Transaction(
        meta=meta,
        date=date,
        flag="*",
        payee=None,
        narration=narration,
        tags=frozenset(),
        links=frozenset(),
        postings=[posting],
    )
    return txn


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------


class TestTelechargerRecu:
    def test_stores_file(self, sample_jpg, ledger_dir):
        """Upload copie le fichier dans la bonne structure de repertoire."""
        stored = telecharger_recu(sample_jpg, ledger_dir)

        assert stored.exists()
        assert "documents" in str(stored)
        assert stored.suffix == ".jpg"

    def test_rejects_invalid_type(self, tmp_path, ledger_dir):
        """Fichier .exe est rejete avec une erreur."""
        exe_file = tmp_path / "malware.exe"
        exe_file.write_bytes(b"MZ\x00\x00")

        with pytest.raises(ValueError, match="non supporte"):
            telecharger_recu(exe_file, ledger_dir)

    def test_resizes_large_image(self, large_jpg, ledger_dir):
        """Image > 1568px est redimensionnee."""
        stored = telecharger_recu(large_jpg, ledger_dir)

        with Image.open(stored) as img:
            assert max(img.size) <= 1568

    def test_pdf_accepted(self, sample_pdf, ledger_dir):
        """Les fichiers PDF sont acceptes et copies."""
        stored = telecharger_recu(sample_pdf, ledger_dir)
        assert stored.exists()
        assert stored.suffix == ".pdf"

    def test_file_not_found(self, tmp_path, ledger_dir):
        """Fichier inexistant leve FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            telecharger_recu(tmp_path / "inexistant.jpg", ledger_dir)


class TestRenommerRecu:
    def test_rename_with_extracted_data(self, sample_jpg, ledger_dir, donnees_recu):
        """Renomme avec fournisseur et date extraits."""
        stored = telecharger_recu(sample_jpg, ledger_dir)
        renamed = renommer_recu(stored, donnees_recu)

        assert "bureau-en-gros" in renamed.name
        assert "2026-01-15" in renamed.name
        assert renamed.exists()


# ---------------------------------------------------------------------------
# DonneesRecu model tests
# ---------------------------------------------------------------------------


class TestDonneesRecu:
    def test_valid_model(self, donnees_recu):
        """DonneesRecu valide correctement avec des montants Decimal."""
        assert donnees_recu.fournisseur == "Bureau en Gros"
        assert donnees_recu.total == Decimal("48.87")
        assert isinstance(donnees_recu.sous_total, Decimal)
        assert 0.0 <= donnees_recu.confiance <= 1.0

    def test_optional_taxes(self):
        """Les montants de taxes peuvent etre None."""
        d = DonneesRecu(
            fournisseur="Test",
            date="2026-01-01",
            sous_total=Decimal("10.00"),
            total=Decimal("10.00"),
            confiance=0.5,
        )
        assert d.montant_tps is None
        assert d.montant_tvq is None


# ---------------------------------------------------------------------------
# Matching tests
# ---------------------------------------------------------------------------


class TestProposerCorrespondances:
    def test_exact_match(self, donnees_recu):
        """Meme montant + meme date = score eleve (~1.0)."""
        txn = _make_beancount_txn(
            datetime.date(2026, 1, 15), "Bureau en Gros fournitures", "48.87"
        )
        matches = proposer_correspondances(donnees_recu, [txn], seuil=0.0)

        assert len(matches) == 1
        assert matches[0].score >= 0.9

    def test_close_match(self, donnees_recu):
        """Montant dans $0.05, date +1 jour = score eleve."""
        txn = _make_beancount_txn(
            datetime.date(2026, 1, 16), "Bureau en Gros", "48.85"
        )
        matches = proposer_correspondances(donnees_recu, [txn], seuil=0.0)

        assert len(matches) == 1
        assert matches[0].score >= 0.8

    def test_no_match(self, donnees_recu):
        """Montant different de $50 = en dessous du seuil."""
        txn = _make_beancount_txn(
            datetime.date(2026, 1, 15), "Autre achat", "98.87"
        )
        matches = proposer_correspondances(donnees_recu, [txn], seuil=0.5)

        assert len(matches) == 0

    def test_max_five(self, donnees_recu):
        """Ne retourne jamais plus de 5 correspondances."""
        txns = [
            _make_beancount_txn(
                datetime.date(2026, 1, 15), f"Achat {i}", "48.87"
            )
            for i in range(10)
        ]
        matches = proposer_correspondances(donnees_recu, txns, seuil=0.0)

        assert len(matches) <= 5

    def test_sorted_by_score(self, donnees_recu):
        """Les correspondances sont triees par score decroissant."""
        txns = [
            _make_beancount_txn(datetime.date(2026, 1, 20), "Lointain", "48.87"),
            _make_beancount_txn(datetime.date(2026, 1, 15), "Exact", "48.87"),
            _make_beancount_txn(datetime.date(2026, 1, 16), "Proche", "48.87"),
        ]
        matches = proposer_correspondances(donnees_recu, txns, seuil=0.0)

        assert len(matches) >= 2
        for i in range(len(matches) - 1):
            assert matches[i].score >= matches[i + 1].score


# ---------------------------------------------------------------------------
# Beancount directive tests
# ---------------------------------------------------------------------------


class TestGenererDirectiveDocument:
    def test_format(self):
        """La directive suit la syntaxe Beancount document."""
        directive = generer_directive_document(
            datetime.date(2026, 1, 15),
            "Depenses:Bureau:Fournitures",
            "documents/2026/01/2026-01-15.bureau-en-gros.jpg",
        )

        assert directive == (
            '2026-01-15 document Depenses:Bureau:Fournitures '
            '"documents/2026/01/2026-01-15.bureau-en-gros.jpg"'
        )


# ---------------------------------------------------------------------------
# Extraction tests (mocked)
# ---------------------------------------------------------------------------


class TestExtractionMock:
    def test_extraction_returns_donnees_recu(self, sample_jpg):
        """Mock de l'API Anthropic, verifie le parsing en DonneesRecu."""
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.input = {
            "fournisseur": "Tim Hortons",
            "date": "2026-02-01",
            "sous_total": "5.00",
            "montant_tps": "0.25",
            "montant_tvq": "0.50",
            "total": "5.75",
            "description": "Cafe et muffin",
            "confiance": 0.95,
        }

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]

        with patch("compteqc.documents.extraction._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            from compteqc.documents.extraction import extraire_recu

            result = extraire_recu(sample_jpg)

        assert isinstance(result, DonneesRecu)
        assert result.fournisseur == "Tim Hortons"
        assert result.total == Decimal("5.75")
        assert result.confiance == 0.95
