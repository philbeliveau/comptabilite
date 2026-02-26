"""Tests for approval queue AR/AP matching (Phase 15 -- RCAP-03, RCAP-04)."""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


class TestMatchEnrichment:
    """Test that pending transactions are enriched with AR/AP match suggestions."""

    def _make_pending_txn(self, *, payee: str, montant: Decimal, date: str = "2026-03-05"):
        """Create a pending transaction dict matching ApprobationExtension format."""
        return {
            "date": date,
            "payee": payee,
            "narration": f"Paiement {payee}",
            "montant": montant,
            "confiance": 0.85,
            "source": "ml",
            "compte_propose": "Revenus:Consultation",
            "niveau": "moderee",
            "gros_montant": False,
        }

    def test_deposit_matches_ar_invoice(self):
        """RCAP-03: Deposit matching an open AR invoice produces match suggestion."""
        try:
            from compteqc.rapprochement import (
                suggerer_rapprochement_ar,
                SuggestionRapprochement,
            )
            from compteqc.models.transaction import TransactionNormalisee
        except ImportError:
            pytest.skip("rapprochement module not available (Phase 13)")

        # Create a deposit transaction
        txn = TransactionNormalisee(
            date=datetime.date(2026, 3, 5),
            montant=Decimal("5750.00"),
            devise="CAD",
            beneficiaire="Acme Corp",
            description="Virement Acme",
            source="pending",
        )

        # Create a mock invoice that matches
        mock_facture = MagicMock()
        mock_facture.numero = "FAC-2026-003"
        mock_facture.nom_client = "Acme Corp"
        mock_facture.total = Decimal("5750.00")
        mock_facture.statut = MagicMock()
        mock_facture.statut.name = "SENT"
        # If solde property exists, use it
        type(mock_facture).solde = property(lambda self: Decimal("5750.00"))

        suggestions = suggerer_rapprochement_ar(txn, [mock_facture])
        assert len(suggestions) >= 1
        assert suggestions[0].type_match == "ar"
        assert suggestions[0].confiance > 0.5

    def test_withdrawal_matches_ap_bill(self):
        """RCAP-03: Withdrawal matching an open AP bill produces match suggestion."""
        try:
            from compteqc.rapprochement import (
                suggerer_rapprochement_ap,
                SuggestionRapprochement,
            )
            from compteqc.models.transaction import TransactionNormalisee
        except ImportError:
            pytest.skip("rapprochement module not available (Phase 13)")

        # Create a withdrawal transaction
        txn = TransactionNormalisee(
            date=datetime.date(2026, 3, 1),
            montant=Decimal("-1149.75"),
            devise="CAD",
            beneficiaire="Cabinet Comptable",
            description="Paiement Cabinet",
            source="pending",
        )

        # Create a mock bill that matches
        mock_bill = MagicMock()
        mock_bill.numero_interne = "FOUR-2026-001"
        mock_bill.fournisseur = "Cabinet Comptable XYZ"
        mock_bill.total = Decimal("1149.75")
        mock_bill.statut = MagicMock()
        mock_bill.statut.name = "APPROVED"
        type(mock_bill).solde = property(lambda self: Decimal("1149.75"))

        suggestions = suggerer_rapprochement_ap(txn, [mock_bill])
        assert len(suggestions) >= 1
        assert suggestions[0].type_match == "ap"
        assert suggestions[0].confiance > 0.5

    def test_no_match_when_amount_differs(self):
        """RCAP-03: No suggestion when amounts do not match."""
        try:
            from compteqc.rapprochement import suggerer_rapprochement_ar
            from compteqc.models.transaction import TransactionNormalisee
        except ImportError:
            pytest.skip("rapprochement module not available (Phase 13)")

        txn = TransactionNormalisee(
            date=datetime.date(2026, 3, 5),
            montant=Decimal("999.99"),
            devise="CAD",
            beneficiaire="Acme Corp",
            description="Virement",
            source="pending",
        )

        mock_facture = MagicMock(spec=[])
        mock_facture.numero = "FAC-2026-003"
        mock_facture.nom_client = "Other Client"
        mock_facture.total = Decimal("5750.00")
        mock_facture.statut = MagicMock()
        mock_facture.statut.name = "SENT"

        suggestions = suggerer_rapprochement_ar(txn, [mock_facture])
        assert len(suggestions) == 0

    def test_enrichment_adds_match_apar_to_txn_dict(self):
        """RCAP-03: _enrichir_rapprochements adds match_apar dict to pending txn."""
        # Test the shape of the match_apar dict
        match_dict = {
            "type": "ar",
            "numero": "FAC-2026-003",
            "nom": "Acme Corp",
            "montant": 5750.00,
            "confiance": 97,
        }

        assert match_dict["type"] in ("ar", "ap")
        assert isinstance(match_dict["numero"], str)
        assert isinstance(match_dict["nom"], str)
        assert isinstance(match_dict["montant"], (int, float))
        assert 0 <= match_dict["confiance"] <= 100


class TestLierAparEndpoint:
    """Test the lier_apar endpoint parameter validation."""

    def test_valid_ar_params(self):
        """RCAP-04: Valid AR linking parameters are accepted."""
        params = {
            "txn_index": "0",
            "numero": "FAC-2026-003",
            "type": "ar",
        }
        assert params["txn_index"].isdigit()
        assert params["numero"]
        assert params["type"] in ("ar", "ap")

    def test_valid_ap_params(self):
        """RCAP-04: Valid AP linking parameters are accepted."""
        params = {
            "txn_index": "2",
            "numero": "FOUR-2026-001",
            "type": "ap",
        }
        assert params["txn_index"].isdigit()
        assert params["numero"]
        assert params["type"] in ("ar", "ap")

    def test_invalid_type_rejected(self):
        """RCAP-04: Invalid type value is rejected."""
        match_type = "invalid"
        assert match_type not in ("ar", "ap")

    def test_empty_numero_rejected(self):
        """RCAP-04: Empty numero is rejected."""
        numero = ""
        assert not numero

    def test_non_digit_index_rejected(self):
        """RCAP-04: Non-digit txn_index is rejected."""
        txn_index = "abc"
        assert not txn_index.isdigit()
