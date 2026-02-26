"""Tests pour les factures recurrentes -- modeles, registre et generation."""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from compteqc.factures.modeles import Facture, InvoiceStatus, LigneFacture
from compteqc.factures.recurrent import (
    ModeleFactureRecurrente,
    RegistreRecurrents,
    avancer_date,
    generer_factures_recurrentes,
)
from compteqc.factures.registre import RegistreFactures


def _ligne(description: str = "Consultation", prix: str = "5000") -> LigneFacture:
    return LigneFacture(
        description=description,
        quantite=Decimal("1"),
        prix_unitaire=Decimal(prix),
    )


def _modele(
    identifiant: str = "REC-ACME-MENSUEL",
    frequence: str = "mensuel",
    prochaine: datetime.date | None = None,
    actif: bool = True,
) -> ModeleFactureRecurrente:
    return ModeleFactureRecurrente(
        identifiant=identifiant,
        nom_client="Acme Corp",
        lignes=[_ligne()],
        frequence=frequence,
        prochaine_generation=prochaine or datetime.date(2026, 2, 1),
        actif=actif,
    )


class TestModeleFactureRecurrente:
    def test_modele_creation(self) -> None:
        modele = _modele()
        assert modele.identifiant == "REC-ACME-MENSUEL"
        assert modele.nom_client == "Acme Corp"
        assert len(modele.lignes) == 1
        assert modele.frequence == "mensuel"
        assert modele.actif is True
        assert modele.echeance_jours == 30
        assert modele.prochaine_generation == datetime.date(2026, 2, 1)

    def test_frequences_valides(self) -> None:
        for freq in ("mensuel", "bimensuel", "trimestriel", "annuel"):
            modele = _modele(frequence=freq)
            assert modele.frequence == freq


class TestRegistreRecurrents:
    def test_registre_ajouter_et_lister(self, tmp_path: Path) -> None:
        chemin = tmp_path / "modeles.yaml"
        registre = RegistreRecurrents(chemin=chemin)
        modele = _modele()
        registre.ajouter(modele)

        modeles = registre.lister()
        assert len(modeles) == 1
        assert modeles[0].identifiant == "REC-ACME-MENSUEL"

    def test_registre_persistence(self, tmp_path: Path) -> None:
        chemin = tmp_path / "modeles.yaml"
        registre1 = RegistreRecurrents(chemin=chemin)
        registre1.ajouter(_modele())

        # New instance, same file
        registre2 = RegistreRecurrents(chemin=chemin)
        modeles = registre2.lister()
        assert len(modeles) == 1
        assert modeles[0].identifiant == "REC-ACME-MENSUEL"

    def test_registre_doublon_raise(self, tmp_path: Path) -> None:
        chemin = tmp_path / "modeles.yaml"
        registre = RegistreRecurrents(chemin=chemin)
        registre.ajouter(_modele())
        with pytest.raises(ValueError, match="existe deja"):
            registre.ajouter(_modele())


class TestGeneration:
    def test_generer_factures_recurrentes_due(self, tmp_path: Path) -> None:
        chemin_rec = tmp_path / "modeles.yaml"
        chemin_fac = tmp_path / "factures.yaml"
        reg_rec = RegistreRecurrents(chemin=chemin_rec)
        reg_fac = RegistreFactures(chemin=chemin_fac)

        # Template due (prochaine_generation in the past)
        reg_rec.ajouter(_modele(prochaine=datetime.date(2026, 1, 15)))

        factures = generer_factures_recurrentes(
            reg_rec, reg_fac, date_reference=datetime.date(2026, 2, 1)
        )

        assert len(factures) == 1
        assert factures[0].numero == "FAC-2026-001"
        assert factures[0].nom_client == "Acme Corp"
        assert factures[0].statut == InvoiceStatus.DRAFT

        # Template's next date should be advanced
        modele_updated = reg_rec.obtenir("REC-ACME-MENSUEL")
        assert modele_updated is not None
        assert modele_updated.prochaine_generation == datetime.date(2026, 2, 15)

        # Invoice should be in the factures registry
        assert reg_fac.obtenir("FAC-2026-001") is not None

    def test_generer_factures_recurrentes_not_due(self, tmp_path: Path) -> None:
        chemin_rec = tmp_path / "modeles.yaml"
        chemin_fac = tmp_path / "factures.yaml"
        reg_rec = RegistreRecurrents(chemin=chemin_rec)
        reg_fac = RegistreFactures(chemin=chemin_fac)

        # Template not due yet (future date)
        reg_rec.ajouter(_modele(prochaine=datetime.date(2026, 3, 1)))

        factures = generer_factures_recurrentes(
            reg_rec, reg_fac, date_reference=datetime.date(2026, 2, 1)
        )
        assert len(factures) == 0

    def test_generer_avance_date_mensuel(self) -> None:
        result = avancer_date("mensuel", datetime.date(2026, 2, 1))
        assert result == datetime.date(2026, 3, 1)

    def test_generer_avance_date_trimestriel(self) -> None:
        result = avancer_date("trimestriel", datetime.date(2026, 2, 1))
        assert result == datetime.date(2026, 5, 1)

    def test_generer_avance_date_bimensuel(self) -> None:
        result = avancer_date("bimensuel", datetime.date(2026, 2, 1))
        assert result == datetime.date(2026, 2, 15)

    def test_generer_avance_date_annuel(self) -> None:
        result = avancer_date("annuel", datetime.date(2026, 2, 1))
        assert result == datetime.date(2027, 2, 1)

    def test_generer_echeance_net30(self, tmp_path: Path) -> None:
        chemin_rec = tmp_path / "modeles.yaml"
        chemin_fac = tmp_path / "factures.yaml"
        reg_rec = RegistreRecurrents(chemin=chemin_rec)
        reg_fac = RegistreFactures(chemin=chemin_fac)

        reg_rec.ajouter(_modele(prochaine=datetime.date(2026, 2, 1)))

        factures = generer_factures_recurrentes(
            reg_rec, reg_fac, date_reference=datetime.date(2026, 2, 1)
        )
        assert len(factures) == 1
        assert factures[0].date_echeance == datetime.date(2026, 3, 3)  # Feb 1 + 30 days

    def test_template_inactif_skip(self, tmp_path: Path) -> None:
        chemin_rec = tmp_path / "modeles.yaml"
        chemin_fac = tmp_path / "factures.yaml"
        reg_rec = RegistreRecurrents(chemin=chemin_rec)
        reg_fac = RegistreFactures(chemin=chemin_fac)

        reg_rec.ajouter(_modele(actif=False, prochaine=datetime.date(2026, 1, 1)))

        factures = generer_factures_recurrentes(
            reg_rec, reg_fac, date_reference=datetime.date(2026, 2, 1)
        )
        assert len(factures) == 0


# ─── CLI Tests ─────────────────────────────────────────────────────


import compteqc.cli.app as cli_app_mod
from typer.testing import CliRunner

from compteqc.cli.facture import facture_app

runner = CliRunner()


@pytest.fixture()
def isolated_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up an isolated ledger directory for CLI tests."""
    ledger_dir = tmp_path / "ledger"
    ledger_dir.mkdir()
    main_beancount = ledger_dir / "main.beancount"
    main_beancount.write_text("; main\n", encoding="utf-8")
    monkeypatch.setattr(cli_app_mod, "_ledger_path", main_beancount)
    return ledger_dir


class TestCLI:
    def test_cli_template_add(self, isolated_ledger: Path) -> None:
        result = runner.invoke(
            facture_app,
            [
                "template-add",
                "--id", "REC-TEST-MENSUEL",
                "--client", "Test Client",
                "--description", "Consultation mensuelle",
                "--prix", "5000",
                "--frequence", "mensuel",
                "--prochaine", "2026-03-01",
            ],
        )
        assert result.exit_code == 0
        assert "REC-TEST-MENSUEL" in result.output
        assert "cree" in result.output

        # Verify template was persisted
        reg = RegistreRecurrents(
            chemin=isolated_ledger / "factures" / "modeles-recurrents.yaml"
        )
        modele = reg.obtenir("REC-TEST-MENSUEL")
        assert modele is not None
        assert modele.nom_client == "Test Client"

    def test_cli_template_list(self, isolated_ledger: Path) -> None:
        # Create a template first
        runner.invoke(
            facture_app,
            [
                "template-add",
                "--id", "REC-LIST-TEST",
                "--client", "List Client",
                "--description", "Service",
                "--prix", "3000",
                "--prochaine", "2026-04-01",
            ],
        )

        result = runner.invoke(facture_app, ["template-list"])
        assert result.exit_code == 0
        assert "REC-LIST-TEST" in result.output
        assert "List Client" in result.output

    def test_cli_generate_recurring(self, isolated_ledger: Path) -> None:
        # Create a template with past date
        runner.invoke(
            facture_app,
            [
                "template-add",
                "--id", "REC-GEN-TEST",
                "--client", "Gen Client",
                "--description", "Retainer",
                "--prix", "8000",
                "--prochaine", "2026-01-15",
            ],
        )

        result = runner.invoke(
            facture_app,
            ["generate-recurring", "--date", "2026-02-01"],
        )
        assert result.exit_code == 0
        assert "1 facture(s) generee(s)" in result.output
        assert "FAC-2026-001" in result.output

        # Verify facture was created in the registry
        reg_fac = RegistreFactures(
            chemin=isolated_ledger / "factures" / "registre.yaml"
        )
        facture = reg_fac.obtenir("FAC-2026-001")
        assert facture is not None
        assert facture.nom_client == "Gen Client"

        # Verify Beancount entry was appended
        beancount_files = list(isolated_ledger.glob("*.beancount"))
        assert any(
            "Facture FAC-2026-001" in f.read_text(encoding="utf-8")
            for f in beancount_files
            if f.name != "main.beancount"
        )

    def test_cli_generate_recurring_dry_run(self, isolated_ledger: Path) -> None:
        # Create a template with past date
        runner.invoke(
            facture_app,
            [
                "template-add",
                "--id", "REC-DRY-TEST",
                "--client", "Dry Client",
                "--description", "Service",
                "--prix", "2000",
                "--prochaine", "2026-01-01",
            ],
        )

        result = runner.invoke(
            facture_app,
            ["generate-recurring", "--date", "2026-02-01", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "dry-run" in result.output
        assert "REC-DRY-TEST" in result.output

        # Verify NO facture was created
        reg_fac = RegistreFactures(
            chemin=isolated_ledger / "factures" / "registre.yaml"
        )
        assert len(reg_fac.lister()) == 0
