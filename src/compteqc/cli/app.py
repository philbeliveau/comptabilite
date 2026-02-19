"""Application CLI principale CompteQC."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

import compteqc

app = typer.Typer(
    name="cqc",
    help="CompteQC - Comptabilite pour consultant IT au Quebec",
    no_args_is_help=True,
)

console = Console()

# Options globales stockees via le callback
_ledger_path: Path = Path("ledger/main.beancount")
_regles_path: Path = Path("rules/categorisation.yaml")


def get_ledger_path() -> Path:
    """Retourne le chemin du fichier main.beancount."""
    return _ledger_path


def get_regles_path() -> Path:
    """Retourne le chemin du fichier de regles."""
    return _regles_path


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"CompteQC version {compteqc.__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ledger: Optional[str] = typer.Option(
        "ledger/main.beancount",
        "--ledger",
        "-l",
        help="Chemin vers le fichier main.beancount",
    ),
    regles: Optional[str] = typer.Option(
        "rules/categorisation.yaml",
        "--regles",
        "-r",
        help="Chemin vers le fichier de regles de categorisation",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Afficher la version de CompteQC",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """CompteQC - Systeme comptable pour consultant IT incorpore au Quebec."""
    global _ledger_path, _regles_path
    if ledger:
        _ledger_path = Path(ledger)
    if regles:
        _regles_path = Path(regles)


# Import et enregistrement des sous-commandes
from compteqc.cli.importer import importer_app  # noqa: E402
from compteqc.cli.paie import app as paie_app  # noqa: E402
from compteqc.cli.rapports import rapport_app, revue, soldes  # noqa: E402

app.add_typer(importer_app, name="importer", help="Importer des fichiers bancaires")
app.add_typer(paie_app, name="paie", help="Gestion de la paie")
app.add_typer(rapport_app, name="rapport", help="Rapports financiers (balance, resultats, bilan)")
app.command(name="soldes", help="Afficher les soldes de tous les comptes")(soldes)
app.command(name="revue", help="Afficher les transactions non-classees")(revue)
