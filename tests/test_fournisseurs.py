"""Tests pour le module de factures fournisseurs (AP) CompteQC."""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from compteqc.fournisseurs.modeles import (
    BillStatus,
    FactureFournisseur,
    LigneFactureFournisseur,
)
from compteqc.fournisseurs.registre import RegistreFournisseurs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _facture_fournisseur_exemple(**kwargs) -> FactureFournisseur:
    """Cree une facture fournisseur d'exemple avec des valeurs par defaut."""
    defaults = dict(
        numero_reference="INV-001",
        numero_interne="FOUR-2026-001",
        fournisseur="Acme Services Inc.",
        date_facture=datetime.date(2026, 1, 15),
        date_echeance=datetime.date(2026, 2, 15),
        lignes=[
            LigneFactureFournisseur(
                description="Services professionnels",
                montant=Decimal("1000"),
                categorie_depense="Depenses:Honoraires-Professionnels:Comptable",
            )
        ],
    )
    defaults.update(kwargs)
    return FactureFournisseur(**defaults)


# ---------------------------------------------------------------------------
# Tests LigneFactureFournisseur
# ---------------------------------------------------------------------------

class TestLigneFactureFournisseur:
    """Tests du modele LigneFactureFournisseur."""

    def test_decimal_coercion(self):
        """Float et string sont convertis en Decimal."""
        ligne = LigneFactureFournisseur(
            description="Test",
            montant=100.50,  # type: ignore[arg-type]
            categorie_depense="Depenses:Divers",
            taux_itc=0.5,  # type: ignore[arg-type]
            taux_itr="0.5",  # type: ignore[arg-type]
        )
        assert isinstance(ligne.montant, Decimal)
        assert ligne.montant == Decimal("100.5")
        assert isinstance(ligne.taux_itc, Decimal)
        assert ligne.taux_itc == Decimal("0.5")
        assert isinstance(ligne.taux_itr, Decimal)
        assert ligne.taux_itr == Decimal("0.5")

    def test_default_tax_flags(self):
        """Drapeaux de taxe et taux ITC/ITR par defaut."""
        ligne = LigneFactureFournisseur(
            description="Test",
            montant=Decimal("100"),
            categorie_depense="Depenses:Divers",
        )
        assert ligne.tps_applicable is True
        assert ligne.tvq_applicable is True
        assert ligne.taux_itc == Decimal("1.0")
        assert ligne.taux_itr == Decimal("1.0")

    def test_custom_itc_itr_rates(self):
        """Taux ITC/ITR personnalises (ex: repas a 50%)."""
        ligne = LigneFactureFournisseur(
            description="Repas client",
            montant=Decimal("80"),
            categorie_depense="Depenses:Repas-Representation",
            taux_itc=Decimal("0.5"),
            taux_itr=Decimal("0.5"),
        )
        assert ligne.taux_itc == Decimal("0.5")
        assert ligne.taux_itr == Decimal("0.5")


# ---------------------------------------------------------------------------
# Tests FactureFournisseur - Tax calculation
# ---------------------------------------------------------------------------

class TestFactureFournisseurTaxCalculation:
    """Tests du calcul des taxes GST/QST."""

    def test_single_line_full_tax(self):
        """Ligne unique avec TPS et TVQ completes."""
        bill = _facture_fournisseur_exemple()
        assert bill.montant_ht == Decimal("1000")
        assert bill.tps == Decimal("50.00")
        assert bill.tvq == Decimal("99.75")
        assert bill.total == Decimal("1149.75")

    def test_multi_line(self):
        """Plusieurs lignes, taxes calculees sur la somme."""
        bill = _facture_fournisseur_exemple(
            lignes=[
                LigneFactureFournisseur(
                    description="Service A",
                    montant=Decimal("600"),
                    categorie_depense="Depenses:Bureau:Abonnements-Logiciels",
                ),
                LigneFactureFournisseur(
                    description="Service B",
                    montant=Decimal("400"),
                    categorie_depense="Depenses:Honoraires-Professionnels:Comptable",
                ),
            ]
        )
        assert bill.montant_ht == Decimal("1000")
        assert bill.tps == Decimal("50.00")
        assert bill.tvq == Decimal("99.75")
        assert bill.total == Decimal("1149.75")

    def test_line_without_tps(self):
        """Ligne sans TPS applicable -> TPS = 0."""
        bill = _facture_fournisseur_exemple(
            lignes=[
                LigneFactureFournisseur(
                    description="Service exempt TPS",
                    montant=Decimal("1000"),
                    categorie_depense="Depenses:Divers",
                    tps_applicable=False,
                ),
            ]
        )
        assert bill.tps == Decimal("0.00")
        assert bill.tvq == Decimal("99.75")
        assert bill.total == Decimal("1099.75")

    def test_line_without_tvq(self):
        """Ligne sans TVQ applicable -> TVQ = 0."""
        bill = _facture_fournisseur_exemple(
            lignes=[
                LigneFactureFournisseur(
                    description="Service exempt TVQ",
                    montant=Decimal("1000"),
                    categorie_depense="Depenses:Divers",
                    tvq_applicable=False,
                ),
            ]
        )
        assert bill.tps == Decimal("50.00")
        assert bill.tvq == Decimal("0.00")
        assert bill.total == Decimal("1050.00")

    def test_no_tax(self):
        """Ligne sans aucune taxe."""
        bill = _facture_fournisseur_exemple(
            lignes=[
                LigneFactureFournisseur(
                    description="Service exempt",
                    montant=Decimal("1000"),
                    categorie_depense="Depenses:Divers",
                    tps_applicable=False,
                    tvq_applicable=False,
                ),
            ]
        )
        assert bill.tps == Decimal("0.00")
        assert bill.tvq == Decimal("0.00")
        assert bill.total == Decimal("1000")


# ---------------------------------------------------------------------------
# Tests FactureFournisseur - Solde
# ---------------------------------------------------------------------------

class TestFactureFournisseurSolde:
    """Tests du calcul du solde."""

    def test_solde_no_payment(self):
        """Solde egal au total quand aucun paiement."""
        bill = _facture_fournisseur_exemple()
        assert bill.solde == bill.total
        assert bill.solde == Decimal("1149.75")

    def test_solde_partial_payment(self):
        """Solde apres paiement partiel."""
        bill = _facture_fournisseur_exemple(montant_paye=Decimal("500"))
        assert bill.solde == Decimal("649.75")

    def test_solde_full_payment(self):
        """Solde = 0 apres paiement complet."""
        bill = _facture_fournisseur_exemple(montant_paye=Decimal("1149.75"))
        assert bill.solde == Decimal("0")


# ---------------------------------------------------------------------------
# Tests RegistreFournisseurs
# ---------------------------------------------------------------------------

class TestRegistreFournisseurs:
    """Tests du registre de factures fournisseurs."""

    def test_ajouter_and_obtenir(self, tmp_path: Path):
        """Ajout et recuperation d'une facture fournisseur."""
        registre = RegistreFournisseurs(chemin=tmp_path / "registre.yaml")
        bill = _facture_fournisseur_exemple()
        registre.ajouter(bill)

        result = registre.obtenir("FOUR-2026-001")
        assert result is not None
        assert result.numero_interne == "FOUR-2026-001"
        assert result.fournisseur == "Acme Services Inc."
        assert result.total == bill.total

    def test_ajouter_duplicate_raises(self, tmp_path: Path):
        """Ajout en double leve ValueError."""
        registre = RegistreFournisseurs(chemin=tmp_path / "registre.yaml")
        registre.ajouter(_facture_fournisseur_exemple())

        with pytest.raises(ValueError, match="existe deja"):
            registre.ajouter(_facture_fournisseur_exemple())

    def test_lister_all(self, tmp_path: Path):
        """Liste toutes les factures fournisseurs."""
        registre = RegistreFournisseurs(chemin=tmp_path / "registre.yaml")
        registre.ajouter(_facture_fournisseur_exemple(numero_interne="FOUR-2026-001"))
        registre.ajouter(_facture_fournisseur_exemple(
            numero_interne="FOUR-2026-002",
            numero_reference="INV-002",
            fournisseur="Vendor B",
        ))

        all_bills = registre.lister()
        assert len(all_bills) == 2

    def test_lister_by_statut(self, tmp_path: Path):
        """Filtrage par statut."""
        registre = RegistreFournisseurs(chemin=tmp_path / "registre.yaml")
        registre.ajouter(_facture_fournisseur_exemple(numero_interne="FOUR-2026-001"))
        registre.ajouter(_facture_fournisseur_exemple(
            numero_interne="FOUR-2026-002",
            numero_reference="INV-002",
            statut=BillStatus.APPROVED,
        ))

        received = registre.lister(statut=BillStatus.RECEIVED)
        assert len(received) == 1
        assert received[0].numero_interne == "FOUR-2026-001"

        approved = registre.lister(statut=BillStatus.APPROVED)
        assert len(approved) == 1
        assert approved[0].numero_interne == "FOUR-2026-002"

    def test_lister_impayees(self, tmp_path: Path):
        """Liste les factures non payees (RECEIVED, APPROVED, PARTIAL) et exclut PAID, DISPUTED."""
        registre = RegistreFournisseurs(chemin=tmp_path / "registre.yaml")
        registre.ajouter(_facture_fournisseur_exemple(
            numero_interne="FOUR-2026-001", statut=BillStatus.RECEIVED,
        ))
        registre.ajouter(_facture_fournisseur_exemple(
            numero_interne="FOUR-2026-002", numero_reference="INV-002",
            statut=BillStatus.APPROVED,
        ))
        registre.ajouter(_facture_fournisseur_exemple(
            numero_interne="FOUR-2026-003", numero_reference="INV-003",
            statut=BillStatus.PARTIAL,
        ))
        registre.ajouter(_facture_fournisseur_exemple(
            numero_interne="FOUR-2026-004", numero_reference="INV-004",
            statut=BillStatus.PAID,
        ))
        registre.ajouter(_facture_fournisseur_exemple(
            numero_interne="FOUR-2026-005", numero_reference="INV-005",
            statut=BillStatus.DISPUTED,
        ))

        impayees = registre.lister_impayees()
        assert len(impayees) == 3
        numeros = {b.numero_interne for b in impayees}
        assert numeros == {"FOUR-2026-001", "FOUR-2026-002", "FOUR-2026-003"}

    def test_mettre_a_jour_statut(self, tmp_path: Path):
        """Mise a jour du statut avec date de paiement."""
        registre = RegistreFournisseurs(chemin=tmp_path / "registre.yaml")
        registre.ajouter(_facture_fournisseur_exemple())

        date_paie = datetime.date(2026, 2, 1)
        updated = registre.mettre_a_jour_statut(
            "FOUR-2026-001",
            BillStatus.PAID,
            date_paiement=date_paie,
            montant_paye=Decimal("1149.75"),
            methode_paiement="virement",
        )
        assert updated.statut == BillStatus.PAID
        assert updated.date_paiement == date_paie
        assert updated.montant_paye == Decimal("1149.75")
        assert updated.methode_paiement == "virement"

    def test_mettre_a_jour_statut_not_found(self, tmp_path: Path):
        """Mise a jour d'une facture inexistante leve ValueError."""
        registre = RegistreFournisseurs(chemin=tmp_path / "registre.yaml")

        with pytest.raises(ValueError, match="introuvable"):
            registre.mettre_a_jour_statut("FOUR-9999-001", BillStatus.PAID)

    def test_persistence_survives_reload(self, tmp_path: Path):
        """Les factures persistent apres rechargement du registre."""
        chemin = tmp_path / "registre.yaml"
        registre1 = RegistreFournisseurs(chemin=chemin)
        registre1.ajouter(_facture_fournisseur_exemple())

        # Recharger depuis le fichier
        registre2 = RegistreFournisseurs(chemin=chemin)
        result = registre2.obtenir("FOUR-2026-001")
        assert result is not None
        assert result.fournisseur == "Acme Services Inc."
        assert result.total == Decimal("1149.75")


# ---------------------------------------------------------------------------
# Tests ProchainNumero
# ---------------------------------------------------------------------------

class TestProchainNumero:
    """Tests de la numerotation sequentielle FOUR-YYYY-NNN."""

    def test_first_number(self, tmp_path: Path):
        """Premier numero pour un registre vide."""
        registre = RegistreFournisseurs(chemin=tmp_path / "registre.yaml")
        assert registre.prochain_numero(2026) == "FOUR-2026-001"

    def test_sequential(self, tmp_path: Path):
        """Numerotation sequentielle apres ajout."""
        registre = RegistreFournisseurs(chemin=tmp_path / "registre.yaml")
        registre.ajouter(_facture_fournisseur_exemple(numero_interne="FOUR-2026-001"))
        assert registre.prochain_numero(2026) == "FOUR-2026-002"

        registre.ajouter(_facture_fournisseur_exemple(
            numero_interne="FOUR-2026-002",
            numero_reference="INV-002",
        ))
        assert registre.prochain_numero(2026) == "FOUR-2026-003"

    def test_different_year(self, tmp_path: Path):
        """Factures d'une annee differente n'affectent pas la numerotation."""
        registre = RegistreFournisseurs(chemin=tmp_path / "registre.yaml")
        registre.ajouter(_facture_fournisseur_exemple(
            numero_interne="FOUR-2025-001",
        ))
        registre.ajouter(_facture_fournisseur_exemple(
            numero_interne="FOUR-2025-002",
            numero_reference="INV-002",
        ))

        # 2026 doit commencer a 001 malgre les factures 2025
        assert registre.prochain_numero(2026) == "FOUR-2026-001"
        # 2025 doit continuer a 003
        assert registre.prochain_numero(2025) == "FOUR-2025-003"
