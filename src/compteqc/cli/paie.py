"""Commandes CLI pour la gestion de la paie.

Usage:
    cqc paie lancer 5000 --dry-run
    cqc paie lancer 5000 --periode 3 --salary-offset 1000
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Optional

import typer
from beancount.parser import printer
from rich.console import Console
from rich.table import Table

from compteqc.quebec.paie.journal import generer_transaction_paie
from compteqc.quebec.paie.moteur import calculer_paie

app = typer.Typer()
console = Console()


def _compter_periodes_existantes(chemin_ledger: str, annee: int) -> int:
    """Compte le nombre de periodes de paie deja enregistrees."""
    try:
        from beancount import loader
        from beancount.core import data

        entries, _errors, _options = loader.load_file(chemin_ledger)
        count = 0
        for entry in entries:
            if not isinstance(entry, data.Transaction):
                continue
            if entry.date.year != annee:
                continue
            if entry.tags and "paie" in entry.tags:
                count += 1
        return count
    except Exception:
        return 0


@app.command("lancer")
def lancer(
    montant_brut: str = typer.Argument(
        ..., help="Montant du salaire brut pour cette periode",
    ),
    periode: Optional[int] = typer.Option(
        None, "--periode", "-p",
        help="Numero de periode (auto-detect si non fourni)",
    ),
    nb_periodes: int = typer.Option(
        26, "--nb-periodes", help="Nombre de periodes par annee",
    ),
    annee: int = typer.Option(
        2026, "--annee", "-a", help="Annee fiscale",
    ),
    salary_offset: Optional[str] = typer.Option(
        None, "--salary-offset",
        help="Montant a appliquer contre le pret actionnaire",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulation sans ecriture au ledger",
    ),
    ledger: str = typer.Option(
        "ledger/main.beancount", "--ledger", "-l",
        help="Chemin vers le fichier main.beancount",
    ),
) -> None:
    """Lancer un calcul de paie complet et generer l'ecriture au ledger."""
    brut = Decimal(montant_brut)

    # Auto-detect period number
    if periode is None:
        periode = _compter_periodes_existantes(ledger, annee) + 1

    # Calculate payroll
    resultat = calculer_paie(
        brut=brut,
        numero_periode=periode,
        chemin_ledger=ledger,
        annee=annee,
        nb_periodes=nb_periodes,
    )

    # Display breakdown
    _afficher_ventilation(resultat)

    # Handle salary offset
    offset_decimal = None
    if salary_offset is not None:
        offset_decimal = Decimal(salary_offset)
        if offset_decimal > resultat.net:
            console.print(
                f"\n[red]Erreur: salary-offset ({offset_decimal}) "
                f"depasse le salaire net ({resultat.net})[/red]"
            )
            raise typer.Exit(code=1)
        _afficher_offset(offset_decimal, resultat.net)

    if dry_run:
        console.print(
            "\n[yellow][Mode simulation -- aucune ecriture au ledger][/yellow]"
        )
        # Show what the transaction would look like
        import datetime

        txn = generer_transaction_paie(
            datetime.date.today(), resultat, salary_offset=offset_decimal,
        )
        console.print("\n[dim]Transaction Beancount (apercu):[/dim]")
        console.print(printer.format_entry(txn))
        return

    # Generate and write transaction
    import datetime

    from compteqc.ledger.fichiers import (
        ajouter_include,
        chemin_fichier_mensuel,
        ecrire_transactions,
    )

    date_paie = datetime.date.today()
    txn = generer_transaction_paie(
        date_paie, resultat, salary_offset=offset_decimal,
    )
    txn_text = printer.format_entry(txn)

    # Write to monthly file
    ledger_path = Path(ledger)
    base_dir = ledger_path.parent
    fichier_mensuel = chemin_fichier_mensuel(
        date_paie.year, date_paie.month, base_dir,
    )
    ecrire_transactions(fichier_mensuel, txn_text)

    # Ensure include exists in main
    chemin_relatif = f"{date_paie.year}/{date_paie.month:02d}.beancount"
    ajouter_include(ledger_path, chemin_relatif)

    console.print(
        f"\n[green]Paie #{periode} enregistree dans "
        f"{fichier_mensuel}[/green]"
    )
    console.print(txn_text)


def _afficher_ventilation(resultat) -> None:
    """Affiche la ventilation complete de la paie avec Rich."""
    table = Table(
        title=f"Paie #{resultat.numero_periode} - Brut: {resultat.brut} CAD",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Element", style="cyan")
    table.add_column("Montant", justify="right")

    # Retenues employe
    table.add_section()
    table.add_row("[bold]Retenues employe[/bold]", "")
    table.add_row("  QPP Base", f"{resultat.qpp_base}")
    table.add_row("  QPP Supp. 1", f"{resultat.qpp_supp1}")
    table.add_row("  QPP Supp. 2", f"{resultat.qpp_supp2}")
    table.add_row("  RQAP", f"{resultat.rqap}")
    table.add_row("  AE", f"{resultat.ae}")
    table.add_row("  Impot federal", f"{resultat.impot_federal}")
    table.add_row("  Impot Quebec", f"{resultat.impot_quebec}")
    table.add_row(
        "[bold]Total retenues[/bold]",
        f"[bold red]{resultat.total_retenues}[/bold red]",
    )

    # Cotisations employeur
    table.add_section()
    table.add_row("[bold]Cotisations employeur[/bold]", "")
    rrq = (
        resultat.qpp_base_employeur
        + resultat.qpp_supp1_employeur
        + resultat.qpp_supp2_employeur
    )
    table.add_row("  RRQ (QPP) Employeur", f"{rrq}")
    table.add_row("  RQAP Employeur", f"{resultat.rqap_employeur}")
    table.add_row("  AE Employeur", f"{resultat.ae_employeur}")
    table.add_row("  FSS", f"{resultat.fss}")
    table.add_row("  CNESST", f"{resultat.cnesst}")
    table.add_row("  Normes du travail", f"{resultat.normes_travail}")
    table.add_row(
        "[bold]Total cotisations employeur[/bold]",
        f"[bold]{resultat.total_cotisations_employeur}[/bold]",
    )

    # Net
    table.add_section()
    table.add_row(
        "[bold green]Salaire net[/bold green]",
        f"[bold green]{resultat.net}[/bold green]",
    )

    console.print(table)


def _afficher_offset(offset: Decimal, net: Decimal) -> None:
    """Affiche la section de compensation du pret actionnaire."""
    table = Table(title="Compensation pret actionnaire", show_header=True)
    table.add_column("Element", style="cyan")
    table.add_column("Montant", justify="right")

    table.add_row("Compensation pret actionnaire", f"-{offset}")
    table.add_row(
        "[bold]Depot bancaire net[/bold]",
        f"[bold green]{net - offset}[/bold green]",
    )

    console.print(table)
