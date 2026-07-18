"""Commandes de suivi des finances personnelles pour planification salariale."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from compteqc.personal_spending import (
    analyser_depenses_personnelles,
    ecrire_rapport_depenses_personnelles,
)


personnel_app = typer.Typer(
    name="personnel",
    help="Suivi des depenses personnelles pour planification de salaire",
    no_args_is_help=True,
)
console = Console()


@personnel_app.command(name="depenses")
def depenses_personnelles(
    fichiers: list[Path] = typer.Argument(
        ...,
        help="CSV personnels RBC a analyser",
    ),
    output_dir: Optional[Path] = typer.Option(
        Path("data/personal-spending"),
        "--output-dir",
        "-o",
        help="Dossier de sortie pour les rapports",
    ),
) -> None:
    """Analyser les depenses personnelles recurrentes pour planifier la paie."""
    summary = analyser_depenses_personnelles(fichiers)
    paths = ecrire_rapport_depenses_personnelles(summary, output_dir or Path("data/personal-spending"))

    table = Table(title="Depenses personnelles recurrentes")
    table.add_column("Mois")
    table.add_column("Brut", justify="right")
    table.add_column("Offset logement", justify="right")
    table.add_column("Net", justify="right")
    for month, amount in summary.monthly_recurring.items():
        offset = summary.monthly_offsets.get(month, 0)
        net = summary.monthly_net_recurring.get(month, amount)
        table.add_row(month, f"{amount:,.2f} $", f"{offset:,.2f} $", f"{net:,.2f} $")
    table.add_row(
        "Moyenne",
        f"[bold]{summary.recurring_monthly_average:,.2f} $[/bold]",
        "",
        f"[bold]{summary.net_recurring_monthly_average:,.2f} $[/bold]",
    )

    console.print(table)
    console.print("\n[bold]Fichiers generes[/bold]")
    for name, path in paths.items():
        console.print(f"- {name}: {path}")
