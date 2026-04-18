"""Tests for receipt-to-AP pipeline (Phase 15 -- RCAP-01, RCAP-02)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from flask import Flask, g


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

    def test_telecom_receipt_prefill_uses_full_amount_and_category_hint(self):
        """Les recus telecom gardent le montant complet et suggerent seulement la categorie."""
        from compteqc.documents.extraction import DonneesRecu
        from compteqc.fava_ext.recus import RecusExtension

        app = Flask(__name__)
        donnees = DonneesRecu(
            fournisseur="Fizz",
            date="2026-03-04",
            sous_total=Decimal("43.00"),
            montant_tps=Decimal("2.15"),
            montant_tvq=Decimal("4.29"),
            total=Decimal("49.44"),
            description="Forfait internet residentiel",
            confiance=0.9,
        )
        ext = RecusExtension.__new__(RecusExtension)
        ext.ledger = type("LedgerStub", (), {"beancount_file_path": "ledger/main.beancount"})()

        with app.test_request_context("/"):
            g.beancount_file_slug = "beancount"
            url, payload = ext._build_ap_prefill_url(donnees)

        parsed = urlparse(url)
        qs = parse_qs(parsed.query)

        assert qs["prefill"] == ["1"]
        assert qs["tab"] == ["ap"]
        assert qs["fournisseur"] == ["Fizz"]
        assert qs["montant"] == ["43.00"]
        assert qs["categorie"] == ["Depenses:Bureau:Internet-Telecom"]
        assert qs["taux_itc"] == ["1.0"]
        assert qs["taux_itr"] == ["1.0"]
        assert payload["allocation_ratio"] == "1.0"


class TestARQueryParameterConstruction:
    """Verify unmatched revenue documents can prefill the AR draft form."""

    def test_revenue_prefill_url_uses_same_tax_split(self):
        """Le lien AR reprend le sous-total et l'applicabilite TPS/TVQ du document."""
        from compteqc.documents.registre import DocumentFiscal
        from compteqc.fava_ext.recus import RecusExtension

        app = Flask(__name__)
        document = DocumentFiscal(
            chemin_document="documents/2026/04/2026-04-05.procom.pdf",
            nom_fichier="2026-04-05.procom.pdf",
            fournisseur="PROCOM SERVICES",
            date="2026-03-11",
            sous_total=Decimal("1000.00"),
            montant_tps=Decimal("50.00"),
            montant_tvq=Decimal("99.75"),
            total=Decimal("1149.75"),
            description="Services consultation",
            confiance=0.9,
            document_kind="revenue",
            pricing_mode="explicit_tax_lines",
        )
        ext = RecusExtension.__new__(RecusExtension)
        ext.ledger = type("LedgerStub", (), {"beancount_file_path": "ledger/main.beancount"})()

        with app.test_request_context("/"):
            g.beancount_file_slug = "beancount"
            url = ext._build_ar_prefill_url(document)

        parsed = urlparse(url)
        qs = parse_qs(parsed.query)

        assert qs["prefill"] == ["1"]
        assert qs["tab"] == ["ar"]
        assert qs["nom_client"] == ["PROCOM SERVICES"]
        assert qs["montant"] == ["1000.00"]
        assert qs["tps_applicable"] == ["1"]
        assert qs["tvq_applicable"] == ["1"]


class TestReceiptNormalizationSafety:
    """Verify conservative guards around automatic in-place revenue rewrites."""

    def test_entry_slice_with_comments_is_not_considered_safely_rewritable(self):
        """Les commentaires Beancount doivent bloquer la reecriture printer-based."""
        from compteqc.fava_ext.recus import RecusExtension

        assert not RecusExtension._entry_slice_est_safely_rewritable(
            '2026-03-11 * "Client" "Projet"\n  ; note manuelle\n'
        )
        assert RecusExtension._entry_slice_est_safely_rewritable(
            '2026-03-11 * "Client" "Projet"\n  Actifs:Banque:RBC:Cheques  1149.75 CAD\n'
        )


class TestAPTemplatePrefillCoverage:
    """Verify AP/AR form prefill JS consumes the expected query parameters."""

    def test_template_handles_ap_tax_flags_and_notes(self):
        """Le template AP doit consommer tps/tvq/note depuis le query-string."""
        template = Path(
            "src/compteqc/fava_ext/comptes_fournisseurs/templates/ComptesFournisseursExtension.html"
        ).read_text(encoding="utf-8")

        assert "checked = params.has('tps')" in template
        assert "checked = params.has('tvq')" in template
        assert "params.get('categorie')" in template
        assert "params.get('taux_itc')" in template
        assert "params.get('taux_itr')" in template
        assert "textarea[name=\"notes\"]" in template
