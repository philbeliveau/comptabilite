"""Tests pour le detecteur CAPEX."""

from __future__ import annotations

from decimal import Decimal

import pytest

from compteqc.categorisation.capex import DetecteurCAPEX, ResultatCAPEX


class TestDetecteurCAPEX:
    """Tests pour DetecteurCAPEX."""

    def setup_method(self):
        self.capex = DetecteurCAPEX()

    def test_amount_above_threshold_flagged(self):
        """Montant >= 500$ est signale comme CAPEX."""
        result = self.capex.verifier(Decimal("599.99"), "Bureau en Gros", "achat divers")
        assert result.est_capex is True
        assert result.raison is not None

    def test_exact_threshold_flagged(self):
        """Montant exactement a 500$ est signale."""
        result = self.capex.verifier(Decimal("500.00"), "Inconnu", "achat")
        assert result.est_capex is True

    def test_known_vendor_below_threshold(self):
        """Vendeur connu (Apple) sous 500$ est quand meme signale."""
        result = self.capex.verifier(Decimal("199.99"), "Apple Store", "achat accessoire")
        assert result.est_capex is True
        assert "apple" in result.raison.lower()

    def test_unknown_vendor_below_threshold_not_flagged(self):
        """Vendeur inconnu sous 500$ n'est PAS signale."""
        result = self.capex.verifier(Decimal("49.99"), "Tim Hortons", "cafe")
        assert result.est_capex is False
        assert result.raison is None
        assert result.classe_suggeree is None

    def test_cca_class_computer(self):
        """Ordinateur/laptop -> classe 50."""
        result = self.capex.verifier(Decimal("2500.00"), "Apple", "MacBook Pro laptop")
        assert result.est_capex is True
        assert result.classe_suggeree == 50

    def test_cca_class_furniture(self):
        """Meuble de bureau -> classe 8."""
        result = self.capex.verifier(Decimal("800.00"), "IKEA", "bureau et chaise ergonomique")
        assert result.est_capex is True
        assert result.classe_suggeree == 8

    def test_cca_class_vehicle(self):
        """Vehicule -> classe 10."""
        result = self.capex.verifier(Decimal("35000.00"), "Concessionnaire", "vehicule auto")
        assert result.est_capex is True
        assert result.classe_suggeree == 10

    def test_cca_class_software(self):
        """Logiciel -> classe 12."""
        result = self.capex.verifier(Decimal("600.00"), "Adobe", "licence logiciel annuelle")
        assert result.est_capex is True
        assert result.classe_suggeree == 12

    def test_cca_class_phone(self):
        """Telephone -> classe 50."""
        result = self.capex.verifier(Decimal("1500.00"), "Apple", "iPhone 15 Pro telephone")
        assert result.est_capex is True
        assert result.classe_suggeree == 50

    def test_cca_class_unknown_capex(self):
        """CAPEX inconnu -> classe_suggeree None."""
        result = self.capex.verifier(Decimal("700.00"), "Inconnu", "equipement special")
        assert result.est_capex is True
        assert result.classe_suggeree is None

    def test_negative_amount_uses_abs(self):
        """Montant negatif utilise la valeur absolue."""
        result = self.capex.verifier(Decimal("-800.00"), "Dell", "moniteur")
        assert result.est_capex is True

    def test_vendor_match_case_insensitive(self):
        """La recherche de vendeur est insensible a la casse."""
        result = self.capex.verifier(Decimal("50.00"), "APPLE store", "cable")
        assert result.est_capex is True
