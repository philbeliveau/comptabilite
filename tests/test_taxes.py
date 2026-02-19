"""Tests pour le module de calcul TPS/TVQ et le moteur de traitement fiscal."""

from decimal import Decimal

import pytest


# ---------------------------------------------------------------------------
# Tests: extraire_taxes (extraction TPS/TVQ d'un montant TTC)
# ---------------------------------------------------------------------------


class TestExtraireTaxes:
    """Tests pour extraire_taxes: extraire TPS et TVQ d'un montant taxes incluses."""

    def test_extraire_taxes_standard(self):
        """$114.98 TTC -> pre_tax ~$100.01, TPS ~$5.00, TVQ ~$9.98.
        TPS et TVQ arrondis independamment."""
        from compteqc.quebec.taxes.calcul import extraire_taxes

        avant_taxes, tps, tvq = extraire_taxes(
            Decimal("114.98"), Decimal("0.05"), Decimal("0.09975")
        )
        # Pre-tax is the plug value: total - tps - tvq
        assert avant_taxes + tps + tvq == Decimal("114.98") or abs(
            avant_taxes + tps + tvq - Decimal("114.98")
        ) <= Decimal("0.01")
        # TPS and TVQ should be reasonable
        assert tps > Decimal("0")
        assert tvq > Decimal("0")
        # TPS should be approximately 5% of pre-tax
        assert abs(tps - (avant_taxes * Decimal("0.05")).quantize(Decimal("0.01"))) <= Decimal("0.01")

    def test_extraire_taxes_rounding_discrepancy(self):
        """$57.49: independent rounding may cause $0.01 discrepancy.
        Pre-tax is the plug value: total - tps - tvq."""
        from compteqc.quebec.taxes.calcul import extraire_taxes

        avant_taxes, tps, tvq = extraire_taxes(
            Decimal("57.49"), Decimal("0.05"), Decimal("0.09975")
        )
        # The plug ensures avant_taxes = total - tps - tvq
        assert avant_taxes == Decimal("57.49") - tps - tvq
        # All values positive
        assert avant_taxes > Decimal("0")
        assert tps > Decimal("0")
        assert tvq > Decimal("0")

    def test_extraire_taxes_zero(self):
        """$0.00 -> tout a zero."""
        from compteqc.quebec.taxes.calcul import extraire_taxes

        avant_taxes, tps, tvq = extraire_taxes(
            Decimal("0.00"), Decimal("0.05"), Decimal("0.09975")
        )
        assert avant_taxes == Decimal("0.00")
        assert tps == Decimal("0.00")
        assert tvq == Decimal("0.00")

    def test_extraire_taxes_petit_montant(self):
        """$1.15 -> pas d'erreur de division, valeurs raisonnables."""
        from compteqc.quebec.taxes.calcul import extraire_taxes

        avant_taxes, tps, tvq = extraire_taxes(
            Decimal("1.15"), Decimal("0.05"), Decimal("0.09975")
        )
        assert avant_taxes >= Decimal("0")
        assert tps >= Decimal("0")
        assert tvq >= Decimal("0")
        # Plug value check
        assert avant_taxes == Decimal("1.15") - tps - tvq

    def test_appliquer_taxes_revenu(self):
        """Pre-tax $1000 -> TPS = $50.00, TVQ = $99.75, total = $1,149.75."""
        from compteqc.quebec.taxes.calcul import appliquer_taxes

        tps, tvq, total = appliquer_taxes(
            Decimal("1000"), Decimal("0.05"), Decimal("0.09975")
        )
        assert tps == Decimal("50.00")
        assert tvq == Decimal("99.75")
        assert total == Decimal("1149.75")


# ---------------------------------------------------------------------------
# Tests: traitement fiscal (regles par categorie/vendeur/client)
# ---------------------------------------------------------------------------


class TestTraitementFiscal:
    """Tests pour le moteur de regles de traitement fiscal."""

    @pytest.fixture
    def regles(self, tmp_path):
        """Charge les regles de taxes depuis le fichier YAML du projet."""
        from compteqc.quebec.taxes.traitement import charger_regles_taxes

        # Use the project's rules file
        return charger_regles_taxes(
            str(tmp_path / "taxes.yaml"),
            _default_yaml=True,
        )

    @pytest.fixture
    def regles_from_file(self):
        """Charge les regles depuis le vrai fichier rules/taxes.yaml."""
        from compteqc.quebec.taxes.traitement import charger_regles_taxes

        return charger_regles_taxes("rules/taxes.yaml")

    def test_traitement_defaut_taxable(self, regles):
        """Vendeur/categorie inconnus -> 'taxable'."""
        from compteqc.quebec.taxes.traitement import determiner_traitement_depense

        result = determiner_traitement_depense(
            "Depenses:Divers", "VENDEUR INCONNU XYZ", regles
        )
        assert result == "taxable"

    def test_traitement_categorie_exempt(self, regles):
        """Depenses:Frais-Bancaires -> 'exempt'."""
        from compteqc.quebec.taxes.traitement import determiner_traitement_depense

        result = determiner_traitement_depense(
            "Depenses:Frais-Bancaires", "QUELCONQUE", regles
        )
        assert result == "exempt"

    def test_traitement_vendeur_override_exempt(self, regles):
        """Vendeur matchant '.*RBC.*' -> 'exempt'."""
        from compteqc.quebec.taxes.traitement import determiner_traitement_depense

        result = determiner_traitement_depense(
            "Depenses:Bureau:Fournitures", "PAIEMENT RBC MASTERCARD", regles
        )
        assert result == "exempt"

    def test_traitement_vendeur_tps_seulement(self, regles):
        """Vendeur matchant '.*AMAZON.*WEB.*SERVICES.*' -> 'tps_seulement'."""
        from compteqc.quebec.taxes.traitement import determiner_traitement_depense

        result = determiner_traitement_depense(
            "Depenses:Bureau:Abonnements-Logiciels",
            "AMAZON WEB SERVICES INC",
            regles,
        )
        assert result == "tps_seulement"

    def test_traitement_client_quebec_tps_tvq(self, regles):
        """Client matchant '.*PROCOM.*' -> 'tps_tvq'."""
        from compteqc.quebec.taxes.traitement import determiner_traitement_revenu

        result = determiner_traitement_revenu("PROCOM SERVICES", "", regles)
        assert result == "tps_tvq"

    def test_traitement_client_international_aucune(self, regles):
        """Client matchant '.*INTERNATIONAL.*' -> 'aucune_taxe'."""
        from compteqc.quebec.taxes.traitement import determiner_traitement_revenu

        result = determiner_traitement_revenu("ACME INTERNATIONAL LTD", "", regles)
        assert result == "aucune_taxe"

    def test_vendeur_override_wins_over_categorie(self, regles):
        """Un override vendeur prend precedence sur le defaut de la categorie."""
        from compteqc.quebec.taxes.traitement import determiner_traitement_depense

        # Depenses:Bureau:Abonnements-Logiciels is normally taxable (not in exempt list)
        # But AWS vendor override should return tps_seulement
        result = determiner_traitement_depense(
            "Depenses:Bureau:Abonnements-Logiciels",
            "AMAZON WEB SERVICES INC",
            regles,
        )
        assert result == "tps_seulement"

    def test_charger_regles_from_real_file(self, regles_from_file):
        """Verifie que le fichier rules/taxes.yaml se charge correctement."""
        assert regles_from_file.defaut == "taxable"
        assert len(regles_from_file.categories.exempt) > 0
