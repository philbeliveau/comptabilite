"""Tests pour le module de rapprochement automatique (auto-matching).

Teste le matching entre transactions bancaires et factures AR/AP ouvertes.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from compteqc.models.transaction import TransactionNormalisee
from compteqc.factures.modeles import Facture, InvoiceStatus, LigneFacture
from compteqc.fournisseurs.modeles import (
    BillStatus,
    FactureFournisseur,
    LigneFactureFournisseur,
)
from compteqc.rapprochement import (
    SuggestionRapprochement,
    calculer_similarite,
    suggerer_rapprochement_ap,
    suggerer_rapprochement_ar,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _facture_ar(
    numero: str = "FAC-2026-001",
    nom_client: str = "Acme Corp",
    montant_ht: Decimal = Decimal("1000.00"),
    statut: InvoiceStatus = InvoiceStatus.SENT,
    montant_paye: Decimal = Decimal("0"),
) -> Facture:
    """Cree une facture AR avec un seul poste produisant le montant HT desire.

    Le total sera montant_ht + TPS (5%) + TVQ (9.975%) = montant_ht * 1.14975.
    """
    return Facture(
        numero=numero,
        nom_client=nom_client,
        date=datetime.date(2026, 1, 15),
        date_echeance=datetime.date(2026, 2, 15),
        lignes=[
            LigneFacture(
                description="Services de consultation",
                quantite=Decimal("1"),
                prix_unitaire=montant_ht,
            )
        ],
        statut=statut,
        montant_paye=montant_paye,
    )


def _facture_ap(
    numero_interne: str = "FOUR-2026-001",
    fournisseur: str = "Bureau en Gros",
    montant: Decimal = Decimal("1000.00"),
    statut: BillStatus = BillStatus.APPROVED,
    montant_paye: Decimal = Decimal("0"),
) -> FactureFournisseur:
    """Cree une facture fournisseur AP."""
    return FactureFournisseur(
        numero_reference="INV-001",
        numero_interne=numero_interne,
        fournisseur=fournisseur,
        date_facture=datetime.date(2026, 1, 10),
        date_echeance=datetime.date(2026, 2, 10),
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


def _transaction(
    montant: str = "1149.75",
    beneficiaire: str = "Virement Acme",
    description: str = "Paiement consultation",
) -> TransactionNormalisee:
    """Cree une transaction normalisee."""
    return TransactionNormalisee(
        date=datetime.date(2026, 2, 15),
        montant=Decimal(montant),
        beneficiaire=beneficiaire,
        description=description,
        source="rbc-cheques-csv",
    )


# ---------------------------------------------------------------------------
# Tests AR matching
# ---------------------------------------------------------------------------

class TestRapprochementAR:
    """Tests pour suggerer_rapprochement_ar."""

    def test_ar_exact_amount_match(self) -> None:
        """Deposit matching invoice total should produce confidence >= 0.7."""
        facture = _facture_ar(montant_ht=Decimal("1000.00"))
        txn = _transaction(montant=str(facture.total), beneficiaire="Client XYZ")

        suggestions = suggerer_rapprochement_ar(txn, [facture])
        assert len(suggestions) == 1
        assert suggestions[0].confiance >= 0.7
        assert suggestions[0].type_match == "ar"
        assert suggestions[0].reference == "FAC-2026-001"

    def test_ar_amount_match_with_client_name(self) -> None:
        """Deposit with client name in description should produce confidence >= 0.9."""
        facture = _facture_ar(nom_client="Acme Corp", montant_ht=Decimal("1000.00"))
        txn = _transaction(
            montant=str(facture.total),
            beneficiaire="Acme Corp",
            description="Paiement Acme Corp",
        )

        suggestions = suggerer_rapprochement_ar(txn, [facture])
        assert len(suggestions) == 1
        assert suggestions[0].confiance >= 0.9

    def test_ar_no_match_different_amount(self) -> None:
        """No match when deposit amount differs significantly."""
        facture = _facture_ar(montant_ht=Decimal("1000.00"))
        txn = _transaction(montant="500.00")

        suggestions = suggerer_rapprochement_ar(txn, [facture])
        assert len(suggestions) == 0

    def test_ar_close_amount_tolerance(self) -> None:
        """Deposit within $0.02 tolerance should still match."""
        facture = _facture_ar(montant_ht=Decimal("1000.00"))
        montant_proche = facture.total - Decimal("0.01")
        txn = _transaction(montant=str(montant_proche))

        suggestions = suggerer_rapprochement_ar(txn, [facture])
        assert len(suggestions) == 1
        assert suggestions[0].confiance >= 0.7

    def test_ar_skip_paid_invoices(self) -> None:
        """Paid invoices should not be suggested."""
        facture = _facture_ar(statut=InvoiceStatus.PAID)
        txn = _transaction(montant=str(facture.total))

        suggestions = suggerer_rapprochement_ar(txn, [facture])
        assert len(suggestions) == 0

    def test_ar_multiple_matches_sorted_by_confidence(self) -> None:
        """Multiple matches should be sorted by confidence descending."""
        f1 = _facture_ar(
            numero="FAC-2026-001",
            nom_client="Acme Corp",
            montant_ht=Decimal("1000.00"),
        )
        f2 = _facture_ar(
            numero="FAC-2026-002",
            nom_client="Unrelated Inc",
            montant_ht=Decimal("1000.00"),
        )
        # Both have same total, but txn mentions Acme -> f1 should rank higher
        txn = _transaction(
            montant=str(f1.total),
            beneficiaire="Acme Corp",
            description="Paiement Acme",
        )

        suggestions = suggerer_rapprochement_ar(txn, [f1, f2])
        assert len(suggestions) >= 2
        assert suggestions[0].reference == "FAC-2026-001"
        assert suggestions[0].confiance >= suggestions[1].confiance

    def test_ar_negative_amount_ignored(self) -> None:
        """Negative transactions (withdrawals) return empty for AR matching."""
        facture = _facture_ar(montant_ht=Decimal("1000.00"))
        txn = _transaction(montant="-1149.75")

        suggestions = suggerer_rapprochement_ar(txn, [facture])
        assert len(suggestions) == 0

    def test_ar_uses_solde_when_partial_payment(self) -> None:
        """When invoice has partial payment, match against solde, not total."""
        facture = _facture_ar(
            montant_ht=Decimal("1000.00"),
            montant_paye=Decimal("500.00"),
            statut=InvoiceStatus.PARTIAL,
        )
        # Solde = total - 500
        txn = _transaction(montant=str(facture.solde))

        suggestions = suggerer_rapprochement_ar(txn, [facture])
        assert len(suggestions) == 1
        assert suggestions[0].montant_attendu == facture.solde


# ---------------------------------------------------------------------------
# Tests AP matching
# ---------------------------------------------------------------------------

class TestRapprochementAP:
    """Tests pour suggerer_rapprochement_ap."""

    def test_ap_exact_amount_match(self) -> None:
        """Withdrawal matching bill total should produce confidence >= 0.7."""
        bill = _facture_ap(montant=Decimal("1000.00"))
        txn = _transaction(montant=str(-bill.total), beneficiaire="Fournisseur")

        suggestions = suggerer_rapprochement_ap(txn, [bill])
        assert len(suggestions) == 1
        assert suggestions[0].confiance >= 0.7
        assert suggestions[0].type_match == "ap"

    def test_ap_amount_match_with_vendor_name(self) -> None:
        """Withdrawal with vendor name in description -> confidence >= 0.9."""
        bill = _facture_ap(fournisseur="Bureau en Gros", montant=Decimal("1000.00"))
        txn = _transaction(
            montant=str(-bill.total),
            beneficiaire="Bureau en Gros",
            description="Paiement Bureau en Gros",
        )

        suggestions = suggerer_rapprochement_ap(txn, [bill])
        assert len(suggestions) == 1
        assert suggestions[0].confiance >= 0.9

    def test_ap_no_match_different_amount(self) -> None:
        """No match when withdrawal amount differs."""
        bill = _facture_ap(montant=Decimal("1000.00"))
        txn = _transaction(montant="-500.00")

        suggestions = suggerer_rapprochement_ap(txn, [bill])
        assert len(suggestions) == 0

    def test_ap_positive_amount_ignored(self) -> None:
        """Positive transactions (deposits) return empty for AP matching."""
        bill = _facture_ap(montant=Decimal("1000.00"))
        txn = _transaction(montant="1149.75")

        suggestions = suggerer_rapprochement_ap(txn, [bill])
        assert len(suggestions) == 0

    def test_ap_skip_paid_bills(self) -> None:
        """Paid bills should not be suggested."""
        bill = _facture_ap(statut=BillStatus.PAID, montant=Decimal("1000.00"))
        txn = _transaction(montant=str(-bill.total))

        suggestions = suggerer_rapprochement_ap(txn, [bill])
        assert len(suggestions) == 0


# ---------------------------------------------------------------------------
# Tests string similarity
# ---------------------------------------------------------------------------

class TestSimilarite:
    """Tests pour calculer_similarite."""

    def test_similarite_exact(self) -> None:
        """Identical strings produce similarity of 1.0."""
        assert calculer_similarite("Acme Corp", "Acme Corp") == 1.0

    def test_similarite_partial(self) -> None:
        """Similar strings produce similarity > 0.5."""
        score = calculer_similarite("ACME CORPORATION", "Acme Corp")
        assert score > 0.5

    def test_similarite_unrelated(self) -> None:
        """Unrelated strings produce similarity < 0.3."""
        score = calculer_similarite("Random Text XYZ", "Acme Corp")
        assert score < 0.3


# ---------------------------------------------------------------------------
# Integration tests for _afficher_rapprochements
# ---------------------------------------------------------------------------

class TestAfficherRapprochements:
    """Tests pour l'integration du rapprochement dans le pipeline d'import."""

    def test_import_shows_ar_suggestions(self, tmp_path: Path) -> None:
        """With an unpaid invoice and matching deposit, suggestions appear in output."""
        from io import StringIO

        from rich.console import Console

        from compteqc.cli.importer import _afficher_rapprochements
        from compteqc.factures.registre import RegistreFactures

        # Create a registre with an unpaid invoice
        registre_path = tmp_path / "ledger" / "factures" / "registre.yaml"
        registre_path.parent.mkdir(parents=True, exist_ok=True)
        registre = RegistreFactures(registre_path)
        facture = _facture_ar(
            nom_client="Acme Corp",
            montant_ht=Decimal("1000.00"),
            statut=InvoiceStatus.SENT,
        )
        registre.ajouter(facture)

        # Create a TransactionNormalisee matching the invoice total
        txn = _transaction(
            montant=str(facture.total),
            beneficiaire="Acme Corp",
            description="Paiement consultation Acme",
        )

        output = StringIO()
        test_console = Console(file=output, width=120)

        # Call _afficher_rapprochements with explicit registre path
        _afficher_rapprochements(
            [txn],
            test_console,
            chemin_registre_ar=registre_path,
        )

        result = output.getvalue()
        assert "Rapprochements AR" in result or "FAC-2026-001" in result

    def test_import_no_suggestions_when_no_invoices(self, tmp_path: Path) -> None:
        """With no invoice registry, no errors and no suggestions shown."""
        from io import StringIO

        from rich.console import Console

        from compteqc.cli.importer import _afficher_rapprochements

        txn = _transaction(montant="1000.00", beneficiaire="Some Vendor")

        output = StringIO()
        test_console = Console(file=output, width=120)

        # Point to a non-existent registre -- should not raise
        nonexistent = tmp_path / "nonexistent" / "registre.yaml"
        _afficher_rapprochements(
            [txn],
            test_console,
            chemin_registre_ar=nonexistent,
        )

        result = output.getvalue()
        # No suggestions table should appear
        assert "Rapprochements AR" not in result
