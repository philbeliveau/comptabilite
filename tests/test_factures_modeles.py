"""Tests pour les ameliorations du modele Facture.

Paiements partiels, derivation automatique du statut, compte de revenu configurable,
ecritures journal par compte de revenu, et enregistrement de paiement au registre.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from compteqc.factures.modeles import (
    Facture,
    InvoiceStatus,
    LigneFacture,
    determiner_statut,
)
from compteqc.factures.journal import (
    generer_ecriture_facture,
    generer_ecriture_paiement,
    generer_ecriture_paiement_partiel,
)
from compteqc.factures.registre import RegistreFactures


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _facture(**kwargs) -> Facture:
    """Cree une facture d'exemple avec valeurs par defaut."""
    defaults = dict(
        numero="FAC-2026-001",
        nom_client="Acme Inc.",
        adresse_client="123 Rue Test, Montreal",
        date=datetime.date(2026, 3, 1),
        date_echeance=datetime.date(2026, 3, 31),
        lignes=[
            LigneFacture(
                description="Services de consultation",
                quantite=Decimal("10"),
                prix_unitaire=Decimal("100.00"),
            )
        ],
    )
    defaults.update(kwargs)
    return Facture(**defaults)


# ---------------------------------------------------------------------------
# Partial payment fields
# ---------------------------------------------------------------------------

class TestPartialPayment:
    def test_facture_montant_paye_default_zero(self):
        f = _facture()
        assert f.montant_paye == Decimal("0")
        assert f.solde == f.total

    def test_facture_solde_after_partial_payment(self):
        f = _facture(montant_paye=Decimal("500"))
        # total = 1000 * 1.14975 = 1149.75
        assert f.solde == f.total - Decimal("500")

    def test_facture_est_paye_integralement(self):
        f = _facture()
        total = f.total
        f2 = _facture(montant_paye=total)
        assert f2.est_paye_integralement is True
        assert f.est_paye_integralement is False


# ---------------------------------------------------------------------------
# Status derivation
# ---------------------------------------------------------------------------

class TestDeterminerStatut:
    def test_determiner_statut_paid(self):
        """Fully paid invoice returns PAID regardless of due date."""
        f = _facture(montant_paye=_facture().total, statut=InvoiceStatus.SENT)
        assert determiner_statut(f) == InvoiceStatus.PAID

    def test_determiner_statut_partial(self):
        """Partially paid, not overdue returns PARTIAL."""
        f = _facture(
            montant_paye=Decimal("100"),
            statut=InvoiceStatus.SENT,
        )
        # Use a reference date before due date
        assert determiner_statut(f, date_reference=datetime.date(2026, 3, 15)) == InvoiceStatus.PARTIAL

    def test_determiner_statut_overdue(self):
        """Unpaid, past due returns OVERDUE."""
        f = _facture(statut=InvoiceStatus.SENT)
        past_due = datetime.date(2026, 4, 15)
        assert determiner_statut(f, date_reference=past_due) == InvoiceStatus.OVERDUE

    def test_determiner_statut_overdue_partial(self):
        """Partially paid AND past due returns OVERDUE."""
        f = _facture(
            montant_paye=Decimal("100"),
            statut=InvoiceStatus.SENT,
        )
        past_due = datetime.date(2026, 4, 15)
        assert determiner_statut(f, date_reference=past_due) == InvoiceStatus.OVERDUE

    def test_determiner_statut_draft(self):
        """Draft with no payment stays DRAFT."""
        f = _facture(statut=InvoiceStatus.DRAFT)
        assert determiner_statut(f) == InvoiceStatus.DRAFT

    def test_determiner_statut_sent(self):
        """Sent, not due, no payment stays SENT."""
        f = _facture(statut=InvoiceStatus.SENT)
        before_due = datetime.date(2026, 3, 15)
        assert determiner_statut(f, date_reference=before_due) == InvoiceStatus.SENT


# ---------------------------------------------------------------------------
# Configurable revenue account
# ---------------------------------------------------------------------------

class TestCompteRevenu:
    def test_ligne_facture_compte_revenu_default(self):
        ligne = LigneFacture(
            description="Test",
            quantite=Decimal("1"),
            prix_unitaire=Decimal("100"),
        )
        assert ligne.compte_revenu == "Revenus:Consultation"

    def test_ligne_facture_compte_revenu_custom(self):
        ligne = LigneFacture(
            description="Test",
            quantite=Decimal("1"),
            prix_unitaire=Decimal("100"),
            compte_revenu="Revenus:Produit-Logiciel",
        )
        assert ligne.compte_revenu == "Revenus:Produit-Logiciel"


# ---------------------------------------------------------------------------
# Journal entries with per-line revenue
# ---------------------------------------------------------------------------

class TestJournalRevenu:
    def test_generer_ecriture_facture_uses_per_line_revenue(self):
        f = _facture(lignes=[
            LigneFacture(
                description="Logiciel",
                quantite=Decimal("1"),
                prix_unitaire=Decimal("1000"),
                compte_revenu="Revenus:Produit-Logiciel",
            )
        ])
        ecriture = generer_ecriture_facture(f)
        assert "Revenus:Produit-Logiciel" in ecriture
        assert "Revenus:Consultation" not in ecriture

    def test_generer_ecriture_facture_mixed_revenue(self):
        """Invoice with 2 lines, different revenue accounts, generates 2 credit lines."""
        f = _facture(lignes=[
            LigneFacture(
                description="Consultation",
                quantite=Decimal("10"),
                prix_unitaire=Decimal("100"),
                compte_revenu="Revenus:Consultation",
            ),
            LigneFacture(
                description="Logiciel",
                quantite=Decimal("1"),
                prix_unitaire=Decimal("500"),
                compte_revenu="Revenus:Produit-Logiciel",
            ),
        ])
        ecriture = generer_ecriture_facture(f)
        assert "Revenus:Consultation" in ecriture
        assert "Revenus:Produit-Logiciel" in ecriture

    def test_generer_ecriture_paiement_partial(self):
        """Partial payment entry uses the payment amount, not facture.total."""
        f = _facture()
        ecriture = generer_ecriture_paiement_partiel(f, Decimal("500"), datetime.date(2026, 3, 15))
        assert "500" in ecriture
        assert "Actifs:ComptesClients" in ecriture
        assert "Actifs:Banque:RBC:Cheques" in ecriture


# ---------------------------------------------------------------------------
# Registry partial payment
# ---------------------------------------------------------------------------

class TestRegistrePaiement:
    def test_registre_enregistrer_paiement_partial(self, tmp_path):
        chemin = tmp_path / "registre.yaml"
        reg = RegistreFactures(chemin=chemin)
        f = _facture()
        reg.ajouter(f)

        updated = reg.enregistrer_paiement("FAC-2026-001", Decimal("500"))
        assert updated.montant_paye == Decimal("500")
        assert updated.solde == updated.total - Decimal("500")
        assert updated.statut == InvoiceStatus.PARTIAL

    def test_registre_lister_impayees(self, tmp_path):
        chemin = tmp_path / "registre.yaml"
        reg = RegistreFactures(chemin=chemin)

        f1 = _facture(numero="FAC-2026-001")
        f2 = _facture(numero="FAC-2026-002", montant_paye=_facture().total)
        reg.ajouter(f1)
        reg.ajouter(f2)

        impayees = reg.lister_impayees()
        assert len(impayees) == 1
        assert impayees[0].numero == "FAC-2026-001"
