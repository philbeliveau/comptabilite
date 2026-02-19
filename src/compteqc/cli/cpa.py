"""Sous-commandes CLI pour le package CPA et la verification."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

cpa_app = typer.Typer(
    name="cpa",
    help="Export CPA et rapports",
    no_args_is_help=True,
)

console = Console()


@cpa_app.command(name="export")
def cpa_export(
    annee: int = typer.Option(..., "--annee", "-a", help="Annee fiscale"),
    sortie: Optional[str] = typer.Option(
        None, "--sortie", "-s", help="Repertoire de sortie (defaut: ledger/exports/)"
    ),
    ledger: Optional[str] = typer.Option(
        None, "--ledger", "-l", help="Chemin vers le fichier main.beancount"
    ),
) -> None:
    """Generer le package CPA complet (ZIP avec tous les rapports)."""
    from pathlib import Path

    from beancount import loader

    from compteqc.cli.app import get_ledger_path
    from compteqc.rapports.cpa_package import CpaPackageError, generer_package_cpa

    chemin_ledger = Path(ledger) if ledger else get_ledger_path()
    if not chemin_ledger.exists():
        console.print(f"[red]Ledger introuvable: {chemin_ledger}[/red]")
        raise typer.Exit(1)

    output_dir = Path(sortie) if sortie else Path("ledger/exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]Generation du package CPA {annee}...[/bold]")

    entries, _, _ = loader.load_file(str(chemin_ledger))

    try:
        zip_path = generer_package_cpa(
            entries=entries,
            annee=annee,
            output_dir=output_dir,
            console_out=console,
        )
        console.print(f"\n[green]Package CPA genere:[/green] {zip_path}")
    except CpaPackageError as e:
        console.print(f"\n[red]ERREUR FATALE:[/red] {e}")
        raise typer.Exit(1) from e


@cpa_app.command(name="verifier")
def cpa_verifier(
    annee: int = typer.Option(..., "--annee", "-a", help="Annee fiscale"),
    ledger: Optional[str] = typer.Option(
        None, "--ledger", "-l", help="Chemin vers le fichier main.beancount"
    ),
) -> None:
    """Executer le checklist de fin d'exercice (sans generer de rapports)."""
    from pathlib import Path

    from beancount import loader

    from compteqc.cli.app import get_ledger_path
    from compteqc.rapports.cpa_package import afficher_checklist
    from compteqc.echeances.verification import verifier_fin_exercice

    chemin_ledger = Path(ledger) if ledger else get_ledger_path()
    if not chemin_ledger.exists():
        console.print(f"[red]Ledger introuvable: {chemin_ledger}[/red]")
        raise typer.Exit(1)

    entries, _, _ = loader.load_file(str(chemin_ledger))

    console.print(f"[bold]Verification fin d'exercice {annee}...[/bold]")
    resultats = verifier_fin_exercice(entries, annee)
    afficher_checklist(resultats, console)

    # Summary
    warnings = [r for r in resultats if r.severite.value == "warning"]
    errors = [r for r in resultats if r.severite.value == "error"]
    if errors:
        console.print(f"\n[red]{len(errors)} erreur(s) fatale(s) detectee(s).[/red]")
    elif warnings:
        console.print(f"\n[yellow]{len(warnings)} avertissement(s).[/yellow]")
    else:
        console.print("\n[green]Toutes les verifications passent.[/green]")
