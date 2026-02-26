"""Sous-commandes CLI pour les rapports de vieillissement AR/AP."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from compteqc.vieillissement import (
    BUCKETS,
    ResumeVieillissement,
    calculer_vieillissement_ap,
    calculer_vieillissement_ar,
    rapport_position_apar,
)

aging_app = typer.Typer(no_args_is_help=True)
console = Console()


def _get_registre_factures():
    """Retourne le registre de factures clients (AR)."""
    from compteqc.cli.app import get_ledger_path
    from compteqc.factures.registre import RegistreFactures

    chemin = get_ledger_path().parent / "factures" / "registre.yaml"
    return RegistreFactures(chemin=chemin)


def _get_registre_fournisseurs():
    """Retourne le registre de factures fournisseurs (AP)."""
    from compteqc.cli.app import get_ledger_path
    from compteqc.fournisseurs.registre import RegistreFournisseurs

    chemin = get_ledger_path().parent / "fournisseurs" / "registre.yaml"
    return RegistreFournisseurs(chemin=chemin)


def _formater_montant(montant: Decimal) -> str:
    """Formate un montant avec 2 decimales."""
    return f"{montant:,.2f} $"


def _couleur_tranche(tranche: str) -> str:
    """Retourne la couleur Rich pour une tranche de vieillissement."""
    return {
        "0-30": "green",
        "31-60": "yellow",
        "61-90": "dark_orange",
        "91+": "red",
    }.get(tranche, "")


def _parse_date_ref(date_ref: str | None) -> datetime.date:
    """Parse une date de reference ou retourne aujourd'hui."""
    if date_ref:
        return datetime.date.fromisoformat(date_ref)
    return datetime.date.today()


def _afficher_resume(resume: ResumeVieillissement, titre: str) -> None:
    """Affiche le resume par tranche pour un rapport de vieillissement."""
    console.print(f"\n[bold]{titre}[/bold]")

    labels = {
        "0-30": "Courant (0-30 jours):",
        "31-60": "31-60 jours:",
        "61-90": "61-90 jours:",
        "91+": "91+ jours:",
    }

    for bucket in BUCKETS:
        montant = resume.totaux_par_tranche[bucket]
        nombre = resume.nombre_par_tranche[bucket]
        couleur = _couleur_tranche(bucket)
        label = labels[bucket]
        console.print(
            f"  [{couleur}]{label:<28}{_formater_montant(montant):>14}  "
            f"({nombre} factures)[/{couleur}]"
        )

    console.print("  " + "-" * 48)
    console.print(
        f"  [bold]{'Total impaye:':<28}{_formater_montant(resume.total_impaye):>14}  "
        f"({resume.nombre_total} factures)[/bold]"
    )


@aging_app.command(name="ar")
def aging_ar(
    date_ref: Optional[str] = typer.Option(
        None,
        "--date",
        "-d",
        help="Date de reference (AAAA-MM-JJ, defaut: aujourd'hui)",
    ),
) -> None:
    """Rapport de vieillissement des comptes clients (AR)."""
    date_reference = _parse_date_ref(date_ref)

    registre = _get_registre_factures()
    factures = registre.lister()

    resume = calculer_vieillissement_ar(factures, date_reference)

    if not resume.lignes:
        console.print("[green]Aucune facture client impayee.[/green]")
        return

    # Detail table
    tableau = Table(
        title=f"Vieillissement AR au {date_reference}", show_header=True
    )
    tableau.add_column("Client")
    tableau.add_column("Facture", style="cyan")
    tableau.add_column("Date")
    tableau.add_column("Echeance")
    tableau.add_column("Total", justify="right")
    tableau.add_column("Paye", justify="right")
    tableau.add_column("Solde", justify="right")
    tableau.add_column("Jours", justify="right")
    tableau.add_column("Tranche")

    for ligne in resume.lignes:
        couleur = _couleur_tranche(ligne.tranche)
        tableau.add_row(
            ligne.nom,
            ligne.identifiant,
            str(ligne.date_document),
            str(ligne.date_echeance),
            _formater_montant(ligne.total),
            _formater_montant(ligne.paye),
            f"[{couleur}]{_formater_montant(ligne.solde)}[/{couleur}]",
            f"[{couleur}]{ligne.jours_echus}[/{couleur}]",
            f"[{couleur}]{ligne.tranche}[/{couleur}]",
        )

    console.print(tableau)

    _afficher_resume(resume, "Resume du vieillissement AR")


@aging_app.command(name="ap")
def aging_ap(
    date_ref: Optional[str] = typer.Option(
        None,
        "--date",
        "-d",
        help="Date de reference (AAAA-MM-JJ, defaut: aujourd'hui)",
    ),
) -> None:
    """Rapport de vieillissement des comptes fournisseurs (AP)."""
    date_reference = _parse_date_ref(date_ref)

    registre = _get_registre_fournisseurs()
    factures = registre.lister()

    resume = calculer_vieillissement_ap(factures, date_reference)

    if not resume.lignes:
        console.print("[green]Aucune facture fournisseur impayee.[/green]")
        return

    # Detail table
    tableau = Table(
        title=f"Vieillissement AP au {date_reference}", show_header=True
    )
    tableau.add_column("Fournisseur")
    tableau.add_column("N. interne", style="cyan")
    tableau.add_column("Reference")
    tableau.add_column("Date")
    tableau.add_column("Echeance")
    tableau.add_column("Total", justify="right")
    tableau.add_column("Paye", justify="right")
    tableau.add_column("Solde", justify="right")
    tableau.add_column("Jours", justify="right")
    tableau.add_column("Tranche")

    # Need reference from original factures for display
    factures_par_id = {f.numero_interne: f for f in factures}

    for ligne in resume.lignes:
        couleur = _couleur_tranche(ligne.tranche)
        facture_orig = factures_par_id.get(ligne.identifiant)
        ref = facture_orig.numero_reference if facture_orig else ""
        tableau.add_row(
            ligne.nom,
            ligne.identifiant,
            ref,
            str(ligne.date_document),
            str(ligne.date_echeance),
            _formater_montant(ligne.total),
            _formater_montant(ligne.paye),
            f"[{couleur}]{_formater_montant(ligne.solde)}[/{couleur}]",
            f"[{couleur}]{ligne.jours_echus}[/{couleur}]",
            f"[{couleur}]{ligne.tranche}[/{couleur}]",
        )

    console.print(tableau)

    _afficher_resume(resume, "Resume du vieillissement AP")


@aging_app.command(name="summary")
def aging_summary(
    date_ref: Optional[str] = typer.Option(
        None,
        "--date",
        "-d",
        help="Date de reference (AAAA-MM-JJ, defaut: aujourd'hui)",
    ),
) -> None:
    """Position combinee AP/AR avec impact tresorerie."""
    date_reference = _parse_date_ref(date_ref)

    registre_ar = _get_registre_factures()
    registre_ap = _get_registre_fournisseurs()

    factures_ar = registre_ar.lister()
    factures_ap = registre_ap.lister()

    resume_ar = calculer_vieillissement_ar(factures_ar, date_reference)
    resume_ap = calculer_vieillissement_ap(factures_ap, date_reference)
    position = rapport_position_apar(resume_ar, resume_ap)

    console.print(f"\n[bold]Position AP/AR au {date_reference}[/bold]")
    console.print("=" * 50)

    console.print(
        f"\n  Total Comptes clients (AR):   "
        f"{_formater_montant(position.ar.total_impaye):>14}  "
        f"({position.ar.nombre_total} factures)"
    )
    console.print(
        f"  Total Comptes fourniss (AP):  "
        f"{_formater_montant(position.ap.total_impaye):>14}  "
        f"({position.ap.nombre_total} factures)"
    )
    console.print("  " + "-" * 48)

    # Color position nette based on sign
    couleur_nette = "green" if position.position_nette >= 0 else "red"
    console.print(
        f"  [{couleur_nette}]{'Position nette (AR - AP):':<32}"
        f"{_formater_montant(position.position_nette):>14}[/{couleur_nette}]"
    )

    console.print(f"\n  [bold]Impact tresorerie 30 jours:[/bold]")
    console.print(
        f"    Encaissements prevus:       "
        f"{_formater_montant(position.encaissements_30j):>14}"
    )
    console.print(
        f"    Paiements prevus:           "
        f"{_formater_montant(position.paiements_30j):>14}"
    )

    couleur_flux = "green" if position.flux_net_30j >= 0 else "red"
    console.print(
        f"    [{couleur_flux}]{'Flux net:':<28}"
        f"{_formater_montant(position.flux_net_30j):>14}[/{couleur_flux}]"
    )
