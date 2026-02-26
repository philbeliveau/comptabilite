"""Tests pour les outils MCP AP/AR (apar.py)."""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from compteqc.fournisseurs.modeles import (
    FactureFournisseur,
    LigneFactureFournisseur,
    BillStatus,
)
from compteqc.factures.modeles import Facture, LigneFacture, InvoiceStatus
from compteqc.vieillissement import ResumeVieillissement
from compteqc.mcp.tools.apar import (
    ap_list, ap_add, ap_pay, ar_aging, ap_aging, apar_summary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ctx():
    """Mock MCP context with AppContext."""
    ctx = MagicMock()
    app = MagicMock()
    app.read_only = False
    app.reload = MagicMock()
    ctx.request_context.lifespan_context = app
    return ctx


@pytest.fixture
def mock_ctx_readonly():
    """Mock MCP context in read-only mode."""
    ctx = MagicMock()
    app = MagicMock()
    app.read_only = True
    ctx.request_context.lifespan_context = app
    return ctx


def _make_ap_bill(
    numero_interne: str = "FOUR-2026-001",
    fournisseur: str = "Cabinet Comptable XYZ",
    numero_reference: str = "INV-2026-042",
    montant: str = "1000.00",
    statut: BillStatus = BillStatus.RECEIVED,
    montant_paye: str = "0",
    date_facture: str = "2026-01-15",
    date_echeance: str = "2026-02-14",
) -> FactureFournisseur:
    return FactureFournisseur(
        numero_reference=numero_reference,
        numero_interne=numero_interne,
        fournisseur=fournisseur,
        date_facture=datetime.date.fromisoformat(date_facture),
        date_echeance=datetime.date.fromisoformat(date_echeance),
        lignes=[
            LigneFactureFournisseur(
                description=f"Facture {numero_reference}",
                montant=Decimal(montant),
                categorie_depense="Depenses:Honoraires-Professionnels:Comptable",
            )
        ],
        statut=statut,
        montant_paye=Decimal(montant_paye),
    )


def _make_ar_invoice(
    numero: str = "FAC-2026-001",
    nom_client: str = "Client ABC",
    montant: str = "5000.00",
    statut: InvoiceStatus = InvoiceStatus.SENT,
    montant_paye: str = "0",
    date: str = "2026-01-01",
    date_echeance: str = "2026-01-31",
) -> Facture:
    return Facture(
        numero=numero,
        nom_client=nom_client,
        date=datetime.date.fromisoformat(date),
        date_echeance=datetime.date.fromisoformat(date_echeance),
        lignes=[
            LigneFacture(
                description="Consultation",
                quantite=Decimal("1"),
                prix_unitaire=Decimal(montant),
            )
        ],
        statut=statut,
        montant_paye=Decimal(montant_paye),
    )


# ---------------------------------------------------------------------------
# TestAPList
# ---------------------------------------------------------------------------

class TestAPList:
    """Tests pour ap_list."""

    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.lister")
    def test_list_all(self, mock_lister, mock_init):
        bill1 = _make_ap_bill(numero_interne="FOUR-2026-001", fournisseur="Vendor A")
        bill2 = _make_ap_bill(numero_interne="FOUR-2026-002", fournisseur="Vendor B")
        mock_lister.return_value = [bill1, bill2]

        result = ap_list()
        assert result["nb_factures"] == 2
        assert result["tronque"] is False
        assert result["factures"][0]["fournisseur"] == "Vendor A"
        assert result["factures"][1]["fournisseur"] == "Vendor B"

    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.lister")
    def test_list_by_statut(self, mock_lister, mock_init):
        bill = _make_ap_bill(statut=BillStatus.RECEIVED)
        mock_lister.return_value = [bill]

        result = ap_list(statut="received")
        mock_lister.assert_called_with(statut=BillStatus.RECEIVED)
        assert result["nb_factures"] == 1

    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.lister")
    def test_list_by_fournisseur(self, mock_lister, mock_init):
        bill1 = _make_ap_bill(fournisseur="Cabinet Comptable XYZ")
        bill2 = _make_ap_bill(fournisseur="Fournisseur Autre")
        mock_lister.return_value = [bill1, bill2]

        result = ap_list(fournisseur="comptable")
        assert result["nb_factures"] == 1
        assert result["factures"][0]["fournisseur"] == "Cabinet Comptable XYZ"

    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    def test_list_invalid_statut(self, mock_init):
        result = ap_list(statut="invalid_status")
        assert "erreur" in result
        assert "Statut invalide" in result["erreur"]


# ---------------------------------------------------------------------------
# TestAPAdd
# ---------------------------------------------------------------------------

class TestAPAdd:
    """Tests pour ap_add."""

    @patch("compteqc.fournisseurs.journal.generer_ecriture_facture_fournisseur")
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.prochain_numero")
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.ajouter")
    def test_add_success(self, mock_ajouter, mock_prochain, mock_init, mock_journal, mock_ctx):
        mock_prochain.return_value = "FOUR-2026-001"
        mock_journal.return_value = '2026-01-15 * "Test"\n  Depenses:Test  1000.00 CAD'

        with patch("builtins.open", mock_open()):
            result = ap_add(
                fournisseur="Cabinet Comptable XYZ",
                numero_reference="INV-2026-042",
                montant_ht="1000.00",
                categorie_depense="Depenses:Honoraires-Professionnels:Comptable",
                date_facture="2026-01-15",
                date_echeance="2026-02-14",
                ctx=mock_ctx,
            )

        assert result["succes"] is True
        assert result["numero_interne"] == "FOUR-2026-001"
        assert result["fournisseur"] == "Cabinet Comptable XYZ"
        mock_ajouter.assert_called_once()
        mock_ctx.request_context.lifespan_context.reload.assert_called_once()

    def test_add_read_only(self, mock_ctx_readonly):
        result = ap_add(
            fournisseur="Test",
            numero_reference="INV-001",
            montant_ht="100.00",
            categorie_depense="Depenses:Test",
            date_facture="2026-01-01",
            date_echeance="2026-01-31",
            ctx=mock_ctx_readonly,
        )
        assert "erreur" in result
        assert "lecture seule" in result["erreur"]

    @patch("compteqc.fournisseurs.journal.generer_ecriture_facture_fournisseur")
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.prochain_numero")
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.ajouter")
    def test_add_with_partial_itc(self, mock_ajouter, mock_prochain, mock_init, mock_journal, mock_ctx):
        mock_prochain.return_value = "FOUR-2026-001"
        mock_journal.return_value = '2026-01-15 * "Test"\n  Depenses:Test  100.00 CAD'

        with patch("builtins.open", mock_open()):
            result = ap_add(
                fournisseur="Restaurant ABC",
                numero_reference="REC-001",
                montant_ht="100.00",
                categorie_depense="Depenses:Repas",
                date_facture="2026-01-15",
                date_echeance="2026-02-14",
                taux_itc="0.5",
                taux_itr="0.5",
                ctx=mock_ctx,
            )

        assert result["succes"] is True
        # Verify the bill was created with correct ITC/ITR rates
        call_args = mock_ajouter.call_args
        bill = call_args[0][0]
        assert bill.lignes[0].taux_itc == Decimal("0.5")
        assert bill.lignes[0].taux_itr == Decimal("0.5")


# ---------------------------------------------------------------------------
# TestAPPay
# ---------------------------------------------------------------------------

class TestAPPay:
    """Tests pour ap_pay."""

    @patch("compteqc.fournisseurs.journal.generer_ecriture_paiement_fournisseur")
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.obtenir")
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.mettre_a_jour_statut")
    def test_pay_full(self, mock_maj, mock_obtenir, mock_init, mock_journal, mock_ctx):
        bill = _make_ap_bill(montant="1000.00", montant_paye="0")
        mock_obtenir.return_value = bill
        mock_journal.return_value = '2026-02-14 * "Paiement"\n  Passifs:CF  1149.75 CAD'

        with patch("builtins.open", mock_open()):
            result = ap_pay(
                numero_interne="FOUR-2026-001",
                date_paiement="2026-02-14",
                ctx=mock_ctx,
            )

        assert result["succes"] is True
        assert result["statut"] == "paid"
        assert result["nouveau_solde"] == "0.00"

    @patch("compteqc.fournisseurs.journal.generer_ecriture_paiement_fournisseur")
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.obtenir")
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.mettre_a_jour_statut")
    def test_pay_partial(self, mock_maj, mock_obtenir, mock_init, mock_journal, mock_ctx):
        bill = _make_ap_bill(montant="1000.00", montant_paye="0")
        mock_obtenir.return_value = bill
        mock_journal.return_value = '2026-02-14 * "Paiement partiel"'

        with patch("builtins.open", mock_open()):
            result = ap_pay(
                numero_interne="FOUR-2026-001",
                montant="500.00",
                date_paiement="2026-02-14",
                ctx=mock_ctx,
            )

        assert result["succes"] is True
        assert result["statut"] == "partial"
        # total = 1000 + 50 (TPS) + 99.75 (TVQ) = 1149.75; solde = 1149.75 - 500 = 649.75
        assert result["nouveau_solde"] == "649.75"

    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.obtenir")
    def test_pay_not_found(self, mock_obtenir, mock_init, mock_ctx):
        mock_obtenir.return_value = None

        result = ap_pay(numero_interne="FOUR-2026-999", ctx=mock_ctx)
        assert "erreur" in result
        assert "introuvable" in result["erreur"]

    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.obtenir")
    def test_pay_exceeds_solde(self, mock_obtenir, mock_init, mock_ctx):
        bill = _make_ap_bill(montant="1000.00", montant_paye="0")
        mock_obtenir.return_value = bill

        result = ap_pay(
            numero_interne="FOUR-2026-001",
            montant="9999.00",
            ctx=mock_ctx,
        )
        assert "erreur" in result
        assert "depasse" in result["erreur"]

    def test_pay_read_only(self, mock_ctx_readonly):
        result = ap_pay(numero_interne="FOUR-2026-001", ctx=mock_ctx_readonly)
        assert "erreur" in result
        assert "lecture seule" in result["erreur"]


# ---------------------------------------------------------------------------
# TestARAging
# ---------------------------------------------------------------------------

class TestARAging:
    """Tests pour ar_aging."""

    @patch("compteqc.vieillissement.calculer_vieillissement_ar")
    @patch("compteqc.factures.registre.RegistreFactures.__init__", return_value=None)
    @patch("compteqc.factures.registre.RegistreFactures.lister")
    def test_aging_report(self, mock_lister, mock_init, mock_aging):
        resume = ResumeVieillissement()
        resume.totaux_par_tranche["0-30"] = Decimal("5000.00")
        resume.totaux_par_tranche["31-60"] = Decimal("2000.00")
        resume.total_impaye = Decimal("7000.00")
        resume.nombre_total = 3

        mock_lister.return_value = []
        mock_aging.return_value = resume

        result = ar_aging(date_reference="2026-02-15")
        assert result["type"] == "AR"
        assert result["date_reference"] == "2026-02-15"
        assert result["tranches"]["0-30"] == "5,000.00"
        assert result["tranches"]["31-60"] == "2,000.00"
        assert result["total"] == "7,000.00"
        assert result["nb_factures_impayees"] == 3

    @patch("compteqc.vieillissement.calculer_vieillissement_ar")
    @patch("compteqc.factures.registre.RegistreFactures.__init__", return_value=None)
    @patch("compteqc.factures.registre.RegistreFactures.lister")
    def test_aging_custom_date(self, mock_lister, mock_init, mock_aging):
        resume = ResumeVieillissement()
        mock_lister.return_value = []
        mock_aging.return_value = resume

        result = ar_aging(date_reference="2026-03-01")
        assert result["date_reference"] == "2026-03-01"
        mock_aging.assert_called_once()
        call_kwargs = mock_aging.call_args
        assert call_kwargs[1]["date_reference"] == datetime.date(2026, 3, 1)


# ---------------------------------------------------------------------------
# TestAPAging
# ---------------------------------------------------------------------------

class TestAPAging:
    """Tests pour ap_aging."""

    @patch("compteqc.vieillissement.calculer_vieillissement_ap")
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.lister")
    def test_aging_report(self, mock_lister, mock_init, mock_aging):
        resume = ResumeVieillissement()
        resume.totaux_par_tranche["0-30"] = Decimal("3000.00")
        resume.totaux_par_tranche["91+"] = Decimal("500.00")
        resume.total_impaye = Decimal("3500.00")
        resume.nombre_total = 2

        mock_lister.return_value = []
        mock_aging.return_value = resume

        result = ap_aging(date_reference="2026-02-15")
        assert result["type"] == "AP"
        assert result["tranches"]["0-30"] == "3,000.00"
        assert result["tranches"]["91+"] == "500.00"
        assert result["total"] == "3,500.00"
        assert result["nb_factures_impayees"] == 2

    @patch("compteqc.vieillissement.calculer_vieillissement_ap")
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.lister")
    def test_aging_empty(self, mock_lister, mock_init, mock_aging):
        resume = ResumeVieillissement()
        mock_lister.return_value = []
        mock_aging.return_value = resume

        result = ap_aging(date_reference="2026-02-15")
        assert result["total"] == "0.00"
        assert result["nb_factures_impayees"] == 0
        for bucket_val in result["tranches"].values():
            assert bucket_val == "0.00"


# ---------------------------------------------------------------------------
# TestAPARSummary
# ---------------------------------------------------------------------------

class TestAPARSummary:
    """Tests pour apar_summary."""

    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.lister_impayees")
    @patch("compteqc.factures.registre.RegistreFactures.__init__", return_value=None)
    @patch("compteqc.factures.registre.RegistreFactures.lister")
    def test_summary_with_data(self, mock_ar_lister, mock_ar_init, mock_ap_impayees, mock_ap_init):
        # AR: 2 unpaid invoices
        ar1 = _make_ar_invoice(
            numero="FAC-2026-001", montant="5000.00",
            date_echeance="2026-02-20",  # within 30 days from ref
        )
        ar2 = _make_ar_invoice(
            numero="FAC-2026-002", montant="3000.00",
            date_echeance="2026-01-15",  # overdue from ref date
        )
        mock_ar_lister.return_value = [ar1, ar2]

        # AP: 1 unpaid bill
        ap1 = _make_ap_bill(
            numero_interne="FOUR-2026-001", montant="1000.00",
            date_echeance="2026-02-28",  # within 30 days from ref
        )
        mock_ap_impayees.return_value = [ap1]

        result = apar_summary(date_reference="2026-02-15")

        assert result["date_reference"] == "2026-02-15"
        assert result["ar"]["nb_factures"] == 2
        assert result["ap"]["nb_factures"] == 1
        ar_total = ar1.solde + ar2.solde
        ap_total = ap1.solde
        assert result["position_nette"] == f"{ar_total - ap_total:,.2f}"

    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.__init__", return_value=None)
    @patch("compteqc.fournisseurs.registre.RegistreFournisseurs.lister_impayees")
    @patch("compteqc.factures.registre.RegistreFactures.__init__", return_value=None)
    @patch("compteqc.factures.registre.RegistreFactures.lister")
    def test_summary_empty(self, mock_ar_lister, mock_ar_init, mock_ap_impayees, mock_ap_init):
        mock_ar_lister.return_value = []
        mock_ap_impayees.return_value = []

        result = apar_summary(date_reference="2026-02-15")
        assert result["ar"]["nb_factures"] == 0
        assert result["ap"]["nb_factures"] == 0
        assert result["position_nette"] == "0.00"
        assert result["impact_cash_30j"]["flux_net"] == "0.00"
