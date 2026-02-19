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


# ---------------------------------------------------------------------------
# Tests: sommaires de periode et concordance TPS/TVQ
# ---------------------------------------------------------------------------


def _creer_transaction(date, narration, postings_data, payee=None):
    """Helper: cree une transaction Beancount avec des postings simples."""
    from beancount.core import data
    from beancount.core.number import D

    meta = data.new_metadata("<test>", 0)
    txn = data.Transaction(
        meta=meta,
        date=date,
        flag="*",
        payee=payee,
        narration=narration,
        tags=frozenset(),
        links=frozenset(),
        postings=[],
    )
    for compte, montant in postings_data:
        data.create_simple_posting(txn, compte, D(str(montant)), "CAD")
    return txn


class TestSommairePeriode:
    """Tests pour les sommaires de periode de declaration TPS/TVQ."""

    def test_sommaire_periode_simple(self):
        """3 transactions (2 depenses avec taxes, 1 revenu avec taxes)
        -> sommaire correct."""
        import datetime

        from compteqc.quebec.taxes.sommaire import generer_sommaire_periode

        entries = [
            # Depense 1: $114.98 TTC (TPS $5.00, TVQ $9.98)
            _creer_transaction(
                datetime.date(2026, 2, 15),
                "Achat fournitures",
                [
                    ("Depenses:Bureau:Fournitures", "100.00"),
                    ("Actifs:TPS-Payee", "5.00"),
                    ("Actifs:TVQ-Payee", "9.98"),
                    ("Actifs:Banque:RBC:Cheques", "-114.98"),
                ],
            ),
            # Depense 2: $57.49 TTC (TPS $2.50, TVQ $4.99)
            _creer_transaction(
                datetime.date(2026, 3, 10),
                "Abonnement logiciel",
                [
                    ("Depenses:Bureau:Abonnements-Logiciels", "50.00"),
                    ("Actifs:TPS-Payee", "2.50"),
                    ("Actifs:TVQ-Payee", "4.99"),
                    ("Actifs:Banque:RBC:Cheques", "-57.49"),
                ],
            ),
            # Revenu: $1149.75 (TPS $50.00, TVQ $99.75 percues)
            _creer_transaction(
                datetime.date(2026, 1, 31),
                "Consultation janvier",
                [
                    ("Actifs:Banque:RBC:Cheques", "1149.75"),
                    ("Revenus:Consultation", "-1000.00"),
                    ("Passifs:TPS-Percue", "-50.00"),
                    ("Passifs:TVQ-Percue", "-99.75"),
                ],
            ),
        ]

        sommaire = generer_sommaire_periode(
            entries,
            datetime.date(2026, 1, 1),
            datetime.date(2026, 3, 31),
        )

        assert sommaire.tps_percue == Decimal("50.00")
        assert sommaire.tvq_percue == Decimal("99.75")
        assert sommaire.tps_payee == Decimal("7.50")  # 5.00 + 2.50
        assert sommaire.tvq_payee == Decimal("14.97")  # 9.98 + 4.99
        assert sommaire.tps_nette == Decimal("42.50")  # 50.00 - 7.50
        assert sommaire.tvq_nette == Decimal("84.78")  # 99.75 - 14.97
        assert sommaire.nb_transactions == 3

    def test_sommaire_trimestriel(self):
        """Transactions dans 2 trimestres -> chaque sommaire trimestriel est independant."""
        import datetime

        from compteqc.quebec.taxes.sommaire import generer_sommaires_annuels

        entries = [
            # Q1: depense avec taxes
            _creer_transaction(
                datetime.date(2026, 2, 15),
                "Achat Q1",
                [
                    ("Depenses:Bureau:Fournitures", "100.00"),
                    ("Actifs:TPS-Payee", "5.00"),
                    ("Actifs:TVQ-Payee", "9.98"),
                    ("Actifs:Banque:RBC:Cheques", "-114.98"),
                ],
            ),
            # Q3: revenu avec taxes
            _creer_transaction(
                datetime.date(2026, 8, 15),
                "Consultation Q3",
                [
                    ("Actifs:Banque:RBC:Cheques", "1149.75"),
                    ("Revenus:Consultation", "-1000.00"),
                    ("Passifs:TPS-Percue", "-50.00"),
                    ("Passifs:TVQ-Percue", "-99.75"),
                ],
            ),
        ]

        sommaires = generer_sommaires_annuels(entries, 2026, "trimestriel")
        assert len(sommaires) == 4

        # Q1: depense seulement
        q1 = sommaires[0]
        assert q1.tps_payee == Decimal("5.00")
        assert q1.tvq_payee == Decimal("9.98")
        assert q1.tps_percue == Decimal("0")
        assert q1.nb_transactions == 1

        # Q2: rien
        q2 = sommaires[1]
        assert q2.nb_transactions == 0

        # Q3: revenu seulement
        q3 = sommaires[2]
        assert q3.tps_percue == Decimal("50.00")
        assert q3.tvq_percue == Decimal("99.75")
        assert q3.tps_payee == Decimal("0")
        assert q3.nb_transactions == 1

        # Q4: rien
        q4 = sommaires[3]
        assert q4.nb_transactions == 0


class TestConcordanceTpsTvq:
    """Tests pour la verification de concordance TPS/TVQ."""

    def test_concordance_ok(self):
        """Toutes les transactions ont TPS + TVQ correspondants -> pas de divergence."""
        import datetime

        from compteqc.quebec.taxes.sommaire import verifier_concordance_tps_tvq

        entries = [
            _creer_transaction(
                datetime.date(2026, 1, 15),
                "Achat avec TPS et TVQ",
                [
                    ("Depenses:Bureau:Fournitures", "100.00"),
                    ("Actifs:TPS-Payee", "5.00"),
                    ("Actifs:TVQ-Payee", "9.98"),
                    ("Actifs:Banque:RBC:Cheques", "-114.98"),
                ],
            ),
            _creer_transaction(
                datetime.date(2026, 2, 28),
                "Revenu avec TPS et TVQ",
                [
                    ("Actifs:Banque:RBC:Cheques", "1149.75"),
                    ("Revenus:Consultation", "-1000.00"),
                    ("Passifs:TPS-Percue", "-50.00"),
                    ("Passifs:TVQ-Percue", "-99.75"),
                ],
            ),
        ]

        divergences = verifier_concordance_tps_tvq(entries, 2026)
        assert divergences == []

    def test_concordance_mismatch(self):
        """Transaction avec TPS mais sans TVQ -> divergence signalee."""
        import datetime

        from compteqc.quebec.taxes.sommaire import verifier_concordance_tps_tvq

        entries = [
            # Transaction avec TPS seulement (TVQ manquante)
            _creer_transaction(
                datetime.date(2026, 3, 15),
                "AWS - TPS seulement",
                [
                    ("Depenses:Bureau:Abonnements-Logiciels", "95.24"),
                    ("Actifs:TPS-Payee", "4.76"),
                    ("Actifs:Banque:RBC:Cheques", "-100.00"),
                ],
            ),
        ]

        divergences = verifier_concordance_tps_tvq(entries, 2026)
        assert len(divergences) == 1
        assert divergences[0]["has_tps"] is True
        assert divergences[0]["has_tvq"] is False
        assert "TPS sans TVQ" in divergences[0]["issue"]

    def test_concordance_exempt_ok(self):
        """Transaction sans aucune ecriture de taxe (exempt) -> pas de divergence."""
        import datetime

        from compteqc.quebec.taxes.sommaire import verifier_concordance_tps_tvq

        entries = [
            # Frais bancaires: exempt, pas de TPS ni TVQ
            _creer_transaction(
                datetime.date(2026, 1, 31),
                "Frais mensuels RBC",
                [
                    ("Depenses:Frais-Bancaires", "15.00"),
                    ("Actifs:Banque:RBC:Cheques", "-15.00"),
                ],
            ),
        ]

        divergences = verifier_concordance_tps_tvq(entries, 2026)
        assert divergences == []
