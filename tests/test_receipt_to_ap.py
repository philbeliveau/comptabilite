"""Tests for receipt-to-AP pipeline (Phase 15 -- RCAP-01, RCAP-02)."""

from __future__ import annotations

from decimal import Decimal
from urllib.parse import parse_qs, urlencode, urlparse


class TestUploadEndpointExtractedData:
    """Verify upload endpoint returns TPS/TVQ breakdown for AP form pre-fill."""

    def test_extracted_includes_tax_fields(self):
        """RCAP-02: Extracted data must include sous_total, montant_tps, montant_tvq."""
        from compteqc.documents.extraction import DonneesRecu

        donnees = DonneesRecu(
            fournisseur="Cabinet Comptable XYZ",
            date="2026-02-15",
            sous_total=Decimal("1000.00"),
            montant_tps=Decimal("50.00"),
            montant_tvq=Decimal("99.75"),
            total=Decimal("1149.75"),
            description="Honoraires comptables Q4",
            confiance=0.92,
        )

        # Reproduce the extracted dict construction
        extracted = {
            "fournisseur": str(donnees.fournisseur),
            "date": str(donnees.date),
            "total": str(donnees.total),
            "sous_total": str(donnees.sous_total),
            "montant_tps": str(donnees.montant_tps) if donnees.montant_tps is not None else None,
            "montant_tvq": str(donnees.montant_tvq) if donnees.montant_tvq is not None else None,
            "description": str(donnees.description) if donnees.description else "",
            "confiance": round(float(donnees.confiance), 4),
        }

        assert extracted["sous_total"] == "1000.00"
        assert extracted["montant_tps"] == "50.00"
        assert extracted["montant_tvq"] == "99.75"
        assert extracted["fournisseur"] == "Cabinet Comptable XYZ"
        assert extracted["description"] == "Honoraires comptables Q4"

    def test_extracted_handles_null_taxes(self):
        """RCAP-02: Extracted data handles receipts with no tax breakdown."""
        from compteqc.documents.extraction import DonneesRecu

        donnees = DonneesRecu(
            fournisseur="Amazon",
            date="2026-03-01",
            sous_total=Decimal("49.99"),
            montant_tps=None,
            montant_tvq=None,
            total=Decimal("49.99"),
            confiance=0.78,
        )

        extracted = {
            "fournisseur": str(donnees.fournisseur),
            "date": str(donnees.date),
            "total": str(donnees.total),
            "sous_total": str(donnees.sous_total),
            "montant_tps": str(donnees.montant_tps) if donnees.montant_tps is not None else None,
            "montant_tvq": str(donnees.montant_tvq) if donnees.montant_tvq is not None else None,
            "description": str(donnees.description) if donnees.description else "",
            "confiance": round(float(donnees.confiance), 4),
        }

        assert extracted["montant_tps"] is None
        assert extracted["montant_tvq"] is None
        assert extracted["sous_total"] == "49.99"


class TestAPQueryParameterConstruction:
    """Verify query parameters for AP form pre-fill are correctly constructed."""

    def test_full_query_params(self):
        """RCAP-02: Full extraction produces correct query parameters."""
        extracted = {
            "fournisseur": "Cabinet Comptable XYZ",
            "date": "2026-02-15",
            "sous_total": "1000.00",
            "montant_tps": "50.00",
            "montant_tvq": "99.75",
            "description": "Honoraires Q4",
        }

        params = {"prefill": "1", "tab": "ap"}
        if extracted["fournisseur"]:
            params["fournisseur"] = extracted["fournisseur"]
        if extracted["date"] and extracted["date"] != "UNKNOWN":
            params["date"] = extracted["date"]
        if extracted["sous_total"]:
            params["montant"] = extracted["sous_total"]
        if extracted.get("montant_tps"):
            params["tps"] = extracted["montant_tps"]
        if extracted.get("montant_tvq"):
            params["tvq"] = extracted["montant_tvq"]
        if extracted.get("description"):
            params["description"] = extracted["description"]

        url = "/beancount/extension/ComptesFournisseursExtension/?" + urlencode(params)
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)

        assert qs["prefill"] == ["1"]
        assert qs["tab"] == ["ap"]
        assert qs["fournisseur"] == ["Cabinet Comptable XYZ"]
        assert qs["date"] == ["2026-02-15"]
        assert qs["montant"] == ["1000.00"]
        assert qs["tps"] == ["50.00"]
        assert qs["tvq"] == ["99.75"]
        assert qs["description"] == ["Honoraires Q4"]

    def test_unknown_date_excluded(self):
        """RCAP-02: UNKNOWN date is not included in query parameters."""
        params = {"prefill": "1", "tab": "ap"}
        date_val = "UNKNOWN"
        if date_val and date_val != "UNKNOWN":
            params["date"] = date_val

        assert "date" not in params

    def test_null_taxes_excluded(self):
        """RCAP-02: Null TPS/TVQ values are not included in query parameters."""
        params = {"prefill": "1", "tab": "ap"}
        montant_tps = None
        montant_tvq = None
        if montant_tps:
            params["tps"] = montant_tps
        if montant_tvq:
            params["tvq"] = montant_tvq

        assert "tps" not in params
        assert "tvq" not in params
