"""Sous-commandes de rapport pour CompteQC (soldes, balance, resultats, bilan, revue)."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

rapport_app = typer.Typer(no_args_is_help=True)
console = Console()


def soldes(
    compte: Optional[str] = typer.Option(
        None,
        "--compte",
        "-c",
        help="Filtre sur le nom du compte (regex partiel)",
    ),
) -> None:
    """Afficher les soldes de tous les comptes avec solde non-nul."""
    console.print("[dim]Commande soldes -- sera implementee dans la tache 2.[/dim]")


@rapport_app.command(name="balance")
def balance() -> None:
    """Afficher la balance de verification (trial balance)."""
    console.print("[dim]Commande balance -- sera implementee dans la tache 2.[/dim]")


@rapport_app.command(name="resultats")
def resultats(
    debut: Optional[str] = typer.Option(None, "--debut", help="Date de debut (AAAA-MM-JJ)"),
    fin: Optional[str] = typer.Option(None, "--fin", help="Date de fin (AAAA-MM-JJ)"),
) -> None:
    """Afficher l'etat des resultats (revenus et depenses)."""
    console.print("[dim]Commande resultats -- sera implementee dans la tache 2.[/dim]")


@rapport_app.command(name="bilan")
def bilan() -> None:
    """Afficher le bilan (actifs, passifs, capitaux propres)."""
    console.print("[dim]Commande bilan -- sera implementee dans la tache 2.[/dim]")


def revue() -> None:
    """Afficher les transactions non-classees pour revision."""
    console.print("[dim]Commande revue -- sera implementee dans la tache 2.[/dim]")
