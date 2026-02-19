"""Tests pour le module de facturation CompteQC."""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from compteqc.factures.modeles import (
    ConfigFacturation,
    Facture,
    InvoiceStatus,
    LigneFacture,
)
from compteqc.factures.registre import RegistreFactures
from compteqc.factures.journal import generer_ecriture_facture, generer_ecriture_paiement


def _weasyprint_available() -> bool:
    """Verifie si WeasyPrint et ses dependances systeme sont disponibles."""
    try:
        import weasyprint  # noqa: F401
        return True
    except (ImportError, OSError):
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _facture_exemple(**kwargs) -> Facture:
    """Cree une facture d'exemple avec des valeurs par defaut."""
    defaults = dict(
        numero="FAC-2026-001",
        nom_client="Acme Inc.",
        adresse_client="123 Rue Test, Montreal",
        date=datetime.date(2026, 3, 1),
        date_echeance=datetime.date(2026, 3, 31),
        lignes=[
            LigneFacture(
                description="Services de consultation",
                quantite=Decimal("40"),
                prix_unitaire=Decimal("250.00"),
            )
        ],
    )
    defaults.update(kwargs)
    return Facture(**defaults)


# ---------------------------------------------------------------------------
# Tests du modele
# ---------------------------------------------------------------------------

class TestFactureTaxCalculation:
    """Tests du calcul des taxes GST/QST."""

    def test_facture_tax_calculation(self):
        """Verifie GST 5% + QST 9.975% sur facture de 10 000$."""
        facture = _facture_exemple(
            lignes=[
                LigneFacture(
                    description="Consultation",
                    quantite=Decimal("1"),
                    prix_unitaire=Decimal("10000"),
                )
            ]
        )
        assert facture.sous_total == Decimal("10000.00")
        assert facture.tps == Decimal("500.00")
        assert facture.tvq == Decimal("997.50")
        assert facture.total == Decimal("11497.50")

    def test_facture_no_tax_line(self):
        """Ligne avec tps_applicable=False exclue du calcul TPS."""
        facture = _facture_exemple(
            lignes=[
                LigneFacture(
                    description="Service exempt",
                    quantite=Decimal("1"),
                    prix_unitaire=Decimal("1000"),
                    tps_applicable=False,
                    tvq_applicable=False,
                ),
                LigneFacture(
                    description="Service taxable",
                    quantite=Decimal("1"),
                    prix_unitaire=Decimal("1000"),
                ),
            ]
        )
        assert facture.sous_total == Decimal("2000.00")
        # TPS seulement sur la ligne taxable (1000 * 5% = 50)
        assert facture.tps == Decimal("50.00")
        # TVQ seulement sur la ligne taxable (1000 * 9.975% = 99.75)
        assert facture.tvq == Decimal("99.75")
        assert facture.total == Decimal("2149.75")

    def test_facture_multiple_lines(self):
        """Facture avec plusieurs lignes calcule correctement le total."""
        facture = _facture_exemple(
            lignes=[
                LigneFacture(
                    description="Consultation",
                    quantite=Decimal("40"),
                    prix_unitaire=Decimal("250"),
                ),
                LigneFacture(
                    description="Developpement",
                    quantite=Decimal("20"),
                    prix_unitaire=Decimal("300"),
                ),
            ]
        )
        # 40*250=10000, 20*300=6000 => sous_total=16000
        assert facture.sous_total == Decimal("16000.00")
        assert facture.tps == Decimal("800.00")
        assert facture.tvq == Decimal("1596.00")


# ---------------------------------------------------------------------------
# Tests du registre
# ---------------------------------------------------------------------------

class TestRegistreFactures:
    """Tests de persistance YAML du registre."""

    def test_registre_ajouter_et_obtenir(self, tmp_path: Path):
        """Round-trip: ajouter puis obtenir une facture."""
        registre = RegistreFactures(chemin=tmp_path / "registre.yaml")
        facture = _facture_exemple()
        registre.ajouter(facture)

        # Recharger depuis le fichier
        registre2 = RegistreFactures(chemin=tmp_path / "registre.yaml")
        result = registre2.obtenir("FAC-2026-001")
        assert result is not None
        assert result.numero == "FAC-2026-001"
        assert result.nom_client == "Acme Inc."
        assert result.total == facture.total

    def test_registre_prochain_numero(self, tmp_path: Path):
        """Numerotation sequentielle par annee."""
        registre = RegistreFactures(chemin=tmp_path / "registre.yaml")
        assert registre.prochain_numero(2026) == "FAC-2026-001"

        registre.ajouter(_facture_exemple(numero="FAC-2026-001"))
        assert registre.prochain_numero(2026) == "FAC-2026-002"

        registre.ajouter(_facture_exemple(numero="FAC-2026-002", nom_client="Client B"))
        assert registre.prochain_numero(2026) == "FAC-2026-003"

        # Annee differente recommence a 001
        assert registre.prochain_numero(2027) == "FAC-2027-001"

    def test_registre_no_duplicate(self, tmp_path: Path):
        """Ajouter un numero duplique leve ValueError."""
        registre = RegistreFactures(chemin=tmp_path / "registre.yaml")
        registre.ajouter(_facture_exemple())

        with pytest.raises(ValueError, match="existe deja"):
            registre.ajouter(_facture_exemple())

    def test_registre_lister_par_statut(self, tmp_path: Path):
        """Filtrage par statut."""
        registre = RegistreFactures(chemin=tmp_path / "registre.yaml")
        registre.ajouter(_facture_exemple(numero="FAC-2026-001"))
        registre.ajouter(
            _facture_exemple(numero="FAC-2026-002", nom_client="B", statut=InvoiceStatus.SENT)
        )

        drafts = registre.lister(statut=InvoiceStatus.DRAFT)
        assert len(drafts) == 1
        assert drafts[0].numero == "FAC-2026-001"

        sent = registre.lister(statut=InvoiceStatus.SENT)
        assert len(sent) == 1

        all_invoices = registre.lister()
        assert len(all_invoices) == 2

    def test_statut_transitions(self, tmp_path: Path):
        """Cycle de vie: draft -> sent -> paid."""
        registre = RegistreFactures(chemin=tmp_path / "registre.yaml")
        registre.ajouter(_facture_exemple())

        # draft -> sent
        f = registre.mettre_a_jour_statut("FAC-2026-001", InvoiceStatus.SENT)
        assert f.statut == InvoiceStatus.SENT

        # sent -> paid
        date_paie = datetime.date(2026, 3, 15)
        f = registre.mettre_a_jour_statut(
            "FAC-2026-001", InvoiceStatus.PAID, date_paiement=date_paie
        )
        assert f.statut == InvoiceStatus.PAID
        assert f.date_paiement == date_paie


# ---------------------------------------------------------------------------
# Tests du journal Beancount
# ---------------------------------------------------------------------------

class TestJournalBeancount:
    """Tests des ecritures Beancount."""

    def test_generer_ecriture_facture_balanced(self):
        """L'ecriture AR debit == credit (somme = 0)."""
        facture = _facture_exemple(
            lignes=[
                LigneFacture(
                    description="Consultation",
                    quantite=Decimal("1"),
                    prix_unitaire=Decimal("10000"),
                )
            ]
        )
        ecriture = generer_ecriture_facture(facture)

        # Extraire les montants
        montants = []
        for line in ecriture.split("\n"):
            parts = line.strip().split()
            for i, p in enumerate(parts):
                if p == "CAD" and i > 0:
                    montants.append(Decimal(parts[i - 1]))

        assert sum(montants) == Decimal("0")
        assert "Actifs:ComptesClients" in ecriture
        assert "Revenus:Consultation" in ecriture
        assert "Passifs:TPS-Percue" in ecriture
        assert "Passifs:TVQ-Percue" in ecriture

    def test_generer_ecriture_paiement_balanced(self):
        """L'ecriture de paiement debit == credit (somme = 0)."""
        facture = _facture_exemple(
            date_paiement=datetime.date(2026, 3, 15),
            lignes=[
                LigneFacture(
                    description="Consultation",
                    quantite=Decimal("1"),
                    prix_unitaire=Decimal("5000"),
                )
            ],
        )
        ecriture = generer_ecriture_paiement(facture)

        montants = []
        for line in ecriture.split("\n"):
            parts = line.strip().split()
            for i, p in enumerate(parts):
                if p == "CAD" and i > 0:
                    montants.append(Decimal(parts[i - 1]))

        assert sum(montants) == Decimal("0")
        assert "Actifs:Banque:RBC:Cheques" in ecriture
        assert "Actifs:ComptesClients" in ecriture
        assert "2026-03-15" in ecriture


# ---------------------------------------------------------------------------
# Tests du generateur PDF
# ---------------------------------------------------------------------------

class TestGenerateurPDF:
    """Tests de la generation PDF."""

    @pytest.mark.skipif(
        not _weasyprint_available(),
        reason="WeasyPrint system dependencies (pango/gobject) not available",
    )
    def test_generer_pdf_creates_file(self, tmp_path: Path):
        """Le PDF est cree et commence par %PDF."""
        from compteqc.factures.generateur import generer_pdf

        facture = _facture_exemple()
        config = ConfigFacturation(
            nom_entreprise="Test Corp",
            numero_tps="123456789RT0001",
            numero_tvq="1234567890TQ0001",
        )

        output = generer_pdf(facture, config, tmp_path)
        assert output.exists()
        assert output.name == "FAC-2026-001.pdf"

        # Verifier que c'est un vrai PDF
        content = output.read_bytes()
        assert content[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Tests CLI
# ---------------------------------------------------------------------------

class TestCLIFacture:
    """Tests des commandes CLI facture."""

    def test_cli_facture_lister(self, tmp_path: Path):
        """La commande lister affiche un tableau."""
        from typer.testing import CliRunner

        from compteqc.cli.facture import facture_app

        # Creer un registre avec une facture
        registre_path = tmp_path / "factures" / "registre.yaml"
        registre = RegistreFactures(chemin=registre_path)
        registre.ajouter(_facture_exemple())

        runner = CliRunner()

        # Monkey-patch _get_registre pour utiliser notre tmp_path
        import compteqc.cli.facture as facture_mod
        original = facture_mod._get_registre

        def mock_registre():
            return RegistreFactures(chemin=registre_path)

        facture_mod._get_registre = mock_registre
        try:
            result = runner.invoke(facture_app, ["lister"])
            assert result.exit_code == 0
            assert "FAC-2026-001" in result.output
            assert "Acme Inc." in result.output
        finally:
            facture_mod._get_registre = original
