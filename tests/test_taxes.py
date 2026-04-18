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
        assert abs(
            tps - (avant_taxes * Decimal("0.05")).quantize(Decimal("0.01"))
        ) <= Decimal("0.01")

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

    def test_sommaire_ignore_remittance_reversal_entries(self):
        """Une remise au fisc ne doit pas gonfler les taxes percues du trimestre."""
        import datetime

        from compteqc.quebec.taxes.sommaire import generer_sommaire_periode

        entries = [
            _creer_transaction(
                datetime.date(2026, 1, 31),
                "Facture janvier",
                [
                    ("Actifs:Banque:RBC:Cheques", "1149.75"),
                    ("Revenus:Consultation", "-1000.00"),
                    ("Passifs:TPS-Percue", "-50.00"),
                    ("Passifs:TVQ-Percue", "-99.75"),
                ],
            ),
            _creer_transaction(
                datetime.date(2026, 2, 20),
                "Paiement remise precedente",
                [
                    ("Passifs:TPS-Percue", "50.00"),
                    ("Passifs:TVQ-Percue", "99.75"),
                    ("Actifs:Banque:RBC:Cheques", "-149.75"),
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
        assert sommaire.tps_nette == Decimal("50.00")
        assert sommaire.tvq_nette == Decimal("99.75")
        assert sommaire.nb_transactions == 2


class TestNormalisationRevenus:
    """Tests pour le split fiscal des revenus appuye par documents."""

    def _document_revenu(
        self,
        *,
        pricing_mode: str,
        fournisseur: str = "PROCOM SERVICES",
        sous_total: str = "1000.00",
        total: str = "1149.75",
        montant_tps: str | None = None,
        montant_tvq: str | None = None,
    ):
        from compteqc.documents.registre import DocumentFiscal

        return DocumentFiscal(
            chemin_document="documents/2026/04/2026-04-05.procom.pdf",
            nom_fichier="2026-04-05.procom.pdf",
            fournisseur=fournisseur,
            date="2026-03-11",
            sous_total=Decimal(sous_total),
            montant_tps=Decimal(montant_tps) if montant_tps is not None else None,
            montant_tvq=Decimal(montant_tvq) if montant_tvq is not None else None,
            total=Decimal(total),
            description="Services consultation",
            confiance=0.91,
            document_kind="revenue",
            pricing_mode=pricing_mode,
        )

    def test_explicit_tax_lines_normalizes_matched_deposit(self):
        """Lignes TPS/TVQ visibles -> reecriture bank + revenu net + taxes."""
        import datetime

        from compteqc.quebec.taxes.revenus import preparer_normalisation_transaction_revenu

        document = self._document_revenu(
            pricing_mode="explicit_tax_lines",
            montant_tps="50.00",
            montant_tvq="99.75",
        )
        txn = _creer_transaction(
            datetime.date(2026, 3, 11),
            "Paiement projet site web",
            [
                ("Actifs:Banque:RBC:Cheques", "1149.75"),
                ("Revenus:Consultation", "-1149.75"),
            ],
            payee="Client Web",
        )

        resultat = preparer_normalisation_transaction_revenu(document, txn, score=0.99)

        assert resultat.status == "matched_and_normalized"
        assert "Revenus:Consultation" in resultat.entry_source
        assert "-1000.00 CAD" in resultat.entry_source
        assert "Passifs:TPS-Percue" in resultat.entry_source
        assert "-50.00 CAD" in resultat.entry_source
        assert "Passifs:TVQ-Percue" in resultat.entry_source
        assert "-99.75 CAD" in resultat.entry_source

    def test_tax_included_computes_split(self):
        """Mode taxes incluses -> extraction du HT/TPS/TVQ selon traitement client."""
        from compteqc.quebec.taxes.revenus import calculer_resume_taxes_revenu

        document = self._document_revenu(
            pricing_mode="tax_included",
            sous_total="1149.75",
            total="1149.75",
        )

        resultat = calculer_resume_taxes_revenu(document)

        assert resultat.resume is not None
        assert resultat.resume.sous_total == Decimal("1000.00")
        assert resultat.resume.tps == Decimal("50.00")
        assert resultat.resume.tvq == Decimal("99.75")

    def test_pre_tax_computes_taxes(self):
        """Mode montant HT -> application des taxes sur le sous-total confirme."""
        from compteqc.quebec.taxes.revenus import calculer_resume_taxes_revenu

        document = self._document_revenu(
            pricing_mode="pre_tax",
            sous_total="1000.00",
            total="1000.00",
        )

        resultat = calculer_resume_taxes_revenu(document)

        assert resultat.resume is not None
        assert resultat.resume.total == Decimal("1149.75")
        assert resultat.resume.tps == Decimal("50.00")
        assert resultat.resume.tvq == Decimal("99.75")

    def test_unknown_pricing_mode_blocks_normalization(self):
        """Mode inconnu -> pas d'inference, revue obligatoire."""
        from compteqc.quebec.taxes.revenus import calculer_resume_taxes_revenu

        document = self._document_revenu(pricing_mode="unknown")

        resultat = calculer_resume_taxes_revenu(document)

        assert resultat.status == "matched_needs_review"
        assert resultat.resume is None
        assert "Mode de prix" in resultat.review_reason

    def test_explicit_tax_lines_without_visible_taxes_blocks_normalization(self):
        """Mode lignes explicites sans lignes extraites -> revue obligatoire."""
        from compteqc.quebec.taxes.revenus import calculer_resume_taxes_revenu

        document = self._document_revenu(
            pricing_mode="explicit_tax_lines",
            montant_tps=None,
            montant_tvq=None,
            sous_total="1149.75",
            total="1149.75",
        )

        resultat = calculer_resume_taxes_revenu(document)

        assert resultat.status == "matched_needs_review"
        assert resultat.resume is None
        assert "Aucune ligne TPS/TVQ" in resultat.review_reason

    def test_boi_reimbursement_is_flagged_for_review(self):
        """Un remboursement BOI ne doit pas etre normalise automatiquement."""
        import datetime

        from compteqc.quebec.taxes.revenus import preparer_normalisation_transaction_revenu

        document = self._document_revenu(
            pricing_mode="explicit_tax_lines",
            fournisseur="Boi Lab 003 Inc.",
            montant_tps="10.50",
            montant_tvq="20.95",
            sous_total="210.13",
            total="241.58",
        )
        txn = _creer_transaction(
            datetime.date(2026, 3, 10),
            "Remboursement abonnement Claude Code",
            [
                ("Actifs:Banque:RBC:Cheques", "241.58"),
                ("Revenus:Consultation", "-241.58"),
            ],
            payee="Boi Lab 003 Inc.",
        )
        txn.meta["note"] = "Remboursement client BOI pour une depense liee au mandat."

        resultat = preparer_normalisation_transaction_revenu(document, txn, score=0.98)

        assert resultat.status == "matched_needs_review"
        assert "remboursement" in resultat.review_reason.lower()

    def test_boi_name_alone_does_not_trigger_reimbursement_review(self):
        """La simple presence de BOI dans le nom du client ne doit pas bloquer la normalisation."""
        import datetime

        from compteqc.quebec.taxes.revenus import preparer_normalisation_transaction_revenu

        document = self._document_revenu(
            pricing_mode="explicit_tax_lines",
            fournisseur="Boi Lab 003 Inc.",
            montant_tps="50.00",
            montant_tvq="99.75",
        )
        txn = _creer_transaction(
            datetime.date(2026, 3, 11),
            "Paiement projet site web",
            [
                ("Actifs:Banque:RBC:Cheques", "1149.75"),
                ("Revenus:Consultation", "-1149.75"),
            ],
            payee="Boi Lab 003 Inc.",
        )

        resultat = preparer_normalisation_transaction_revenu(document, txn, score=0.99)

        assert resultat.status == "matched_and_normalized"

    def test_already_normalized_transaction_is_detected(self):
        """Une transaction avec postes taxes explicites n'est pas reecrite une seconde fois."""
        import datetime

        from compteqc.quebec.taxes.revenus import preparer_normalisation_transaction_revenu

        document = self._document_revenu(
            pricing_mode="explicit_tax_lines",
            montant_tps="50.00",
            montant_tvq="99.75",
        )
        txn = _creer_transaction(
            datetime.date(2026, 3, 11),
            "Paiement projet site web",
            [
                ("Actifs:Banque:RBC:Cheques", "1149.75"),
                ("Revenus:Consultation", "-1000.00"),
                ("Passifs:TPS-Percue", "-50.00"),
                ("Passifs:TVQ-Percue", "-99.75"),
            ],
            payee="Client Web",
        )

        resultat = preparer_normalisation_transaction_revenu(document, txn, score=0.99)

        assert resultat.status == "already_normalized"
        assert resultat.resume is not None

    def test_existing_tax_split_mismatch_is_not_treated_as_already_normalized(self):
        """Une transaction taxe mal ventilee doit rester en revue manuelle."""
        import datetime

        from compteqc.quebec.taxes.revenus import preparer_normalisation_transaction_revenu

        document = self._document_revenu(
            pricing_mode="explicit_tax_lines",
            montant_tps="50.00",
            montant_tvq="99.75",
        )
        txn = _creer_transaction(
            datetime.date(2026, 3, 11),
            "Paiement projet site web",
            [
                ("Actifs:Banque:RBC:Cheques", "1149.75"),
                ("Revenus:Consultation", "-1020.00"),
                ("Passifs:TPS-Percue", "-50.00"),
                ("Passifs:TVQ-Percue", "-79.75"),
            ],
            payee="Client Web",
        )

        resultat = preparer_normalisation_transaction_revenu(document, txn, score=0.99)

        assert resultat.status == "matched_needs_review"
        assert "ne concorde pas" in resultat.review_reason

    def test_pre_tax_correspondance_uses_normalized_gross_total(self):
        """Le matching d'un document HT compare le depot sur le total TTC attendu."""
        import datetime

        from compteqc.quebec.taxes.revenus import proposer_correspondances_revenu

        document = self._document_revenu(
            pricing_mode="pre_tax",
            sous_total="1000.00",
            total="1000.00",
        )
        txn = _creer_transaction(
            datetime.date(2026, 3, 11),
            "Paiement projet site web",
            [
                ("Actifs:Banque:RBC:Cheques", "1149.75"),
                ("Revenus:Consultation", "-1149.75"),
            ],
            payee="Client Web",
        )

        correspondances = proposer_correspondances_revenu(document, [txn])

        assert len(correspondances) == 1
        assert correspondances[0].score >= 0.99

    def test_audit_detects_unmatched_document_and_gross_receipt(self):
        """L'audit partage signale depot brut sans taxes et document revenu non apparie."""
        import datetime

        from compteqc.quebec.taxes.revenus import auditer_revenus_taxes

        document = self._document_revenu(pricing_mode="pre_tax", total="1000.00")
        txn = _creer_transaction(
            datetime.date(2026, 3, 11),
            "Paiement projet site web",
            [
                ("Actifs:Banque:RBC:Cheques", "1149.75"),
                ("Revenus:Consultation", "-1149.75"),
            ],
            payee="Client Web",
        )

        audit = auditer_revenus_taxes(
            [txn],
            [document],
            debut=datetime.date(2026, 1, 1),
            fin=datetime.date(2026, 3, 31),
        )

        assert audit.count == 2
        assert any(a.type == "document_revenu_non_apparie" for a in audit.anomalies)
        assert any(a.type == "reception_brute_sans_taxes" for a in audit.anomalies)

    def test_audit_flags_reimbursement_like_revenue_even_when_tax_split_exists(self):
        """Un encaissement taxe qui ressemble a un remboursement doit rester visible."""
        import datetime

        from compteqc.quebec.taxes.revenus import auditer_revenus_taxes

        txn = _creer_transaction(
            datetime.date(2026, 3, 10),
            "Remboursement abonnement Claude Code",
            [
                ("Actifs:Banque:RBC:Cheques", "241.58"),
                ("Revenus:Consultation", "-210.11"),
                ("Passifs:TPS-Percue", "-10.51"),
                ("Passifs:TVQ-Percue", "-20.96"),
            ],
            payee="Boi Lab 003 Inc.",
        )
        txn.meta["note"] = "Remboursement client BOI pour une depense liee au mandat."
        txn.meta["document_fiscal_id"] = "doc-boi"
        txn.meta["normalisation_revenu"] = "oui"

        audit = auditer_revenus_taxes(
            [txn],
            [],
            debut=datetime.date(2026, 1, 1),
            fin=datetime.date(2026, 3, 31),
        )

        assert any(
            a.type == "encaissement_taxe_remboursement_a_revoir"
            for a in audit.anomalies
        )

    def test_audit_flags_manual_normalization_without_document(self):
        """Un split fiscal manuel sans document lie doit rester en revue."""
        import datetime

        from compteqc.quebec.taxes.revenus import auditer_revenus_taxes

        txn = _creer_transaction(
            datetime.date(2026, 3, 11),
            "Paiement projet site web",
            [
                ("Actifs:Banque:RBC:Cheques", "2299.50"),
                ("Revenus:Consultation", "-2000.00"),
                ("Passifs:TPS-Percue", "-100.00"),
                ("Passifs:TVQ-Percue", "-199.50"),
            ],
            payee="CRL",
        )
        txn.meta["normalisation_revenu"] = "oui"
        txn.meta["source_taxes_revenu"] = "confirmation_manuelle_2026-04-05"

        audit = auditer_revenus_taxes(
            [txn],
            [],
            debut=datetime.date(2026, 1, 1),
            fin=datetime.date(2026, 3, 31),
        )

        assert any(a.type == "revenu_normalise_sans_document" for a in audit.anomalies)


class TestPreparationRemise:
    """Tests des helpers de preparation trimestrielle TPS/TVQ."""

    def test_periode_par_defaut_prend_le_dernier_trimestre_complet(self):
        import datetime

        from compteqc.quebec.taxes.remise import construire_periode_remise

        periode = construire_periode_remise(date_reference=datetime.date(2026, 4, 4))

        assert periode.code == "2026-Q1"
        assert periode.debut == datetime.date(2026, 1, 1)
        assert periode.fin == datetime.date(2026, 3, 31)
        assert periode.date_limite == datetime.date(2026, 4, 30)

    def test_preparation_classe_collecte_intrants_et_ajustements(self):
        import datetime

        from compteqc.quebec.taxes.remise import preparer_remise_trimestrielle

        entries = [
            _creer_transaction(
                datetime.date(2026, 1, 31),
                "Facture janvier",
                [
                    ("Actifs:Banque:RBC:Cheques", "1149.75"),
                    ("Revenus:Consultation", "-1000.00"),
                    ("Passifs:TPS-Percue", "-50.00"),
                    ("Passifs:TVQ-Percue", "-99.75"),
                ],
                payee="Client ABC",
            ),
            _creer_transaction(
                datetime.date(2026, 2, 10),
                "Abonnement logiciel",
                [
                    ("Depenses:Bureau:Abonnements-Logiciels", "100.00"),
                    ("Actifs:TPS-Payee", "5.00"),
                    ("Actifs:TVQ-Payee", "9.98"),
                    ("Actifs:Banque:RBC:Cheques", "-114.98"),
                ],
                payee="Fournisseur SaaS",
            ),
            _creer_transaction(
                datetime.date(2026, 3, 15),
                "Paiement remise precedente",
                [
                    ("Passifs:TPS-Percue", "12.00"),
                    ("Passifs:TVQ-Percue", "23.94"),
                    ("Actifs:Banque:RBC:Cheques", "-35.94"),
                ],
                payee="ARC / RQ",
            ),
        ]

        preparation = preparer_remise_trimestrielle(
            entries,
            "2026-Q1",
            date_reference=datetime.date(2026, 4, 4),
        )

        assert preparation.periode.date_limite == datetime.date(2026, 4, 30)
        assert preparation.sommaire.tps_percue == Decimal("50.00")
        assert preparation.sommaire.tvq_percue == Decimal("99.75")
        assert preparation.sommaire.tps_payee == Decimal("5.00")
        assert preparation.sommaire.tvq_payee == Decimal("9.98")
        assert preparation.sommaire.tps_nette == Decimal("45.00")
        assert preparation.sommaire.tvq_nette == Decimal("89.77")
        assert preparation.nb_collecte == 1
        assert preparation.nb_intrants == 1
        assert preparation.nb_ajustements == 1
        assert preparation.lignes_collecte[0].compte_reference == "Revenus:Consultation"
        assert (
            preparation.lignes_intrants[0].compte_reference
            == "Depenses:Bureau:Abonnements-Logiciels"
        )
        assert preparation.lignes_ajustements[0].compte_reference == "Revue manuelle"
        assert any(
            avertissement.titre == "Ajustements ou remises a revoir"
            for avertissement in preparation.avertissements
        )


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
