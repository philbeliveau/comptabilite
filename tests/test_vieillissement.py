"""Tests pour le module de vieillissement (aging) des comptes clients et fournisseurs."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from compteqc.factures.modeles import Facture, InvoiceStatus, LigneFacture
from compteqc.fournisseurs.modeles import (
    FactureFournisseur,
    BillStatus,
    LigneFactureFournisseur,
)
from compteqc.vieillissement import (
    calculer_age_jours,
    classifier_age,
    calculer_vieillissement_ar,
    calculer_vieillissement_ap,
    rapport_position_apar,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _facture_ar(
    numero: str = "FAC-2026-001",
    date_echeance: datetime.date = datetime.date(2026, 3, 31),
    montant_paye: Decimal = Decimal("0"),
    statut: InvoiceStatus = InvoiceStatus.SENT,
    prix: Decimal = Decimal("1000"),
) -> Facture:
    return Facture(
        numero=numero,
        nom_client="Client Test",
        date=datetime.date(2026, 3, 1),
        date_echeance=date_echeance,
        lignes=[
            LigneFacture(
                description="Services",
                quantite=Decimal("1"),
                prix_unitaire=prix,
            )
        ],
        statut=statut,
        montant_paye=montant_paye,
    )


def _facture_ap(
    numero_interne: str = "FOUR-2026-001",
    date_echeance: datetime.date = datetime.date(2026, 3, 31),
    montant_paye: Decimal = Decimal("0"),
    statut: BillStatus = BillStatus.APPROVED,
    montant: Decimal = Decimal("500"),
) -> FactureFournisseur:
    return FactureFournisseur(
        numero_reference="INV-123",
        numero_interne=numero_interne,
        fournisseur="Fournisseur Test",
        date_facture=datetime.date(2026, 3, 1),
        date_echeance=date_echeance,
        lignes=[
            LigneFactureFournisseur(
                description="Fournitures",
                montant=montant,
                categorie_depense="Depenses:Bureau:Fournitures",
            )
        ],
        statut=statut,
        montant_paye=montant_paye,
    )


# ---------------------------------------------------------------------------
# calculer_age_jours
# ---------------------------------------------------------------------------

class TestCalculerAgeJours:
    def test_calculer_age_jours_past_due(self):
        """10 days past due returns 10."""
        ref = datetime.date(2026, 4, 10)
        echeance = datetime.date(2026, 3, 31)
        assert calculer_age_jours(echeance, ref) == 10

    def test_calculer_age_jours_not_yet_due(self):
        """5 days before due returns -5."""
        ref = datetime.date(2026, 3, 26)
        echeance = datetime.date(2026, 3, 31)
        assert calculer_age_jours(echeance, ref) == -5

    def test_calculer_age_jours_due_today(self):
        """Due today returns 0."""
        ref = datetime.date(2026, 3, 31)
        echeance = datetime.date(2026, 3, 31)
        assert calculer_age_jours(echeance, ref) == 0


# ---------------------------------------------------------------------------
# classifier_age
# ---------------------------------------------------------------------------

class TestClassifierAge:
    def test_classifier_age_current(self):
        assert classifier_age(10) == "0-30"

    def test_classifier_age_30_60(self):
        assert classifier_age(45) == "31-60"

    def test_classifier_age_60_90(self):
        assert classifier_age(75) == "61-90"

    def test_classifier_age_90_plus(self):
        assert classifier_age(120) == "91+"


# ---------------------------------------------------------------------------
# calculer_vieillissement_ar
# ---------------------------------------------------------------------------

class TestVieillissementAR:
    def test_vieillissement_ar_empty(self):
        """No invoices returns empty buckets with zero totals."""
        result = calculer_vieillissement_ar([])
        assert result.total_impaye == Decimal("0")
        assert result.nombre_total == 0
        for bucket in ["0-30", "31-60", "61-90", "91+"]:
            assert result.totaux_par_tranche[bucket] == Decimal("0")
            assert result.nombre_par_tranche[bucket] == 0

    def test_vieillissement_ar_single_invoice(self):
        """One invoice lands in correct bucket."""
        f = _facture_ar(date_echeance=datetime.date(2026, 3, 31))
        ref = datetime.date(2026, 4, 10)  # 10 days past due -> 0-30 bucket
        result = calculer_vieillissement_ar([f], date_reference=ref)
        assert result.nombre_total == 1
        assert result.totaux_par_tranche["0-30"] == f.solde
        assert result.total_impaye == f.solde

    def test_vieillissement_ar_multiple_buckets(self):
        """3 invoices across different buckets, subtotals correct."""
        ref = datetime.date(2026, 6, 15)
        f1 = _facture_ar(numero="FAC-001", date_echeance=datetime.date(2026, 6, 1), prix=Decimal("100"))  # 14 days -> 0-30
        f2 = _facture_ar(numero="FAC-002", date_echeance=datetime.date(2026, 5, 1), prix=Decimal("200"))  # 45 days -> 31-60
        f3 = _facture_ar(numero="FAC-003", date_echeance=datetime.date(2026, 3, 1), prix=Decimal("300"))  # 106 days -> 91+
        result = calculer_vieillissement_ar([f1, f2, f3], date_reference=ref)
        assert result.nombre_total == 3
        assert result.nombre_par_tranche["0-30"] == 1
        assert result.nombre_par_tranche["31-60"] == 1
        assert result.nombre_par_tranche["91+"] == 1
        assert result.totaux_par_tranche["0-30"] == f1.solde
        assert result.totaux_par_tranche["31-60"] == f2.solde
        assert result.totaux_par_tranche["91+"] == f3.solde

    def test_vieillissement_ar_excludes_paid(self):
        """Paid invoices not included in aging."""
        f_paid = _facture_ar(statut=InvoiceStatus.PAID, montant_paye=_facture_ar().total)
        f_unpaid = _facture_ar(numero="FAC-002")
        ref = datetime.date(2026, 4, 10)
        result = calculer_vieillissement_ar([f_paid, f_unpaid], date_reference=ref)
        assert result.nombre_total == 1

    def test_vieillissement_ar_partial_payment_uses_solde(self):
        """Partially paid invoice shows outstanding balance, not total."""
        f = _facture_ar(montant_paye=Decimal("500"))
        ref = datetime.date(2026, 4, 10)
        result = calculer_vieillissement_ar([f], date_reference=ref)
        assert result.total_impaye == f.solde
        assert result.total_impaye < f.total


# ---------------------------------------------------------------------------
# calculer_vieillissement_ap
# ---------------------------------------------------------------------------

class TestVieillissementAP:
    def test_vieillissement_ap_single_bill(self):
        """One AP bill lands in correct bucket."""
        b = _facture_ap(date_echeance=datetime.date(2026, 3, 31))
        ref = datetime.date(2026, 4, 10)  # 10 days past due -> 0-30
        result = calculer_vieillissement_ap([b], date_reference=ref)
        assert result.nombre_total == 1
        assert result.totaux_par_tranche["0-30"] == b.solde

    def test_vieillissement_ap_excludes_paid(self):
        """Paid AP bills not included."""
        total = _facture_ap().total
        b_paid = _facture_ap(statut=BillStatus.PAID, montant_paye=total)
        b_unpaid = _facture_ap(numero_interne="FOUR-002")
        ref = datetime.date(2026, 4, 10)
        result = calculer_vieillissement_ap([b_paid, b_unpaid], date_reference=ref)
        assert result.nombre_total == 1


# ---------------------------------------------------------------------------
# rapport_position_apar
# ---------------------------------------------------------------------------

class TestPositionAPAR:
    def test_position_apar_net_calculation(self):
        """AR total - AP total = net position."""
        ar_invoices = [_facture_ar(prix=Decimal("2000"))]
        ap_bills = [_facture_ap(montant=Decimal("500"))]
        ref = datetime.date(2026, 4, 10)
        ar = calculer_vieillissement_ar(ar_invoices, date_reference=ref)
        ap = calculer_vieillissement_ap(ap_bills, date_reference=ref)
        pos = rapport_position_apar(ar, ap)
        assert pos.position_nette == ar.total_impaye - ap.total_impaye
        assert pos.position_nette > Decimal("0")

    def test_position_apar_cash_impact_30_days(self):
        """Only current bucket amounts included in 30-day cash impact."""
        ref = datetime.date(2026, 4, 10)
        # AR: one in 0-30, one in 91+
        ar_current = _facture_ar(numero="FAC-001", date_echeance=datetime.date(2026, 4, 1), prix=Decimal("1000"))
        ar_old = _facture_ar(numero="FAC-002", date_echeance=datetime.date(2026, 1, 1), prix=Decimal("2000"))
        # AP: one in 0-30
        ap_current = _facture_ap(date_echeance=datetime.date(2026, 4, 1), montant=Decimal("300"))

        ar = calculer_vieillissement_ar([ar_current, ar_old], date_reference=ref)
        ap = calculer_vieillissement_ap([ap_current], date_reference=ref)
        pos = rapport_position_apar(ar, ap)

        assert pos.encaissements_30j == ar.totaux_par_tranche["0-30"]
        assert pos.paiements_30j == ap.totaux_par_tranche["0-30"]
        assert pos.flux_net_30j == pos.encaissements_30j - pos.paiements_30j
