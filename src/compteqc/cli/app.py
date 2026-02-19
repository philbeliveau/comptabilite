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
from compteqc.cli.reviser import reviser_app  # noqa: E402

app.add_typer(importer_app, name="importer", help="Importer des fichiers bancaires")
app.add_typer(paie_app, name="paie", help="Gestion de la paie")
app.add_typer(rapport_app, name="rapport", help="Rapports financiers (balance, resultats, bilan)")
app.add_typer(reviser_app, name="reviser", help="Reviser les transactions en attente")
app.command(name="soldes", help="Afficher les soldes de tous les comptes")(soldes)
app.command(name="revue", help="Afficher les transactions non-classees")(revue)


@app.command(name="retrain")
def retrain() -> None:
    """Re-entrainer le modele ML depuis les transactions approuvees."""
    from beancount import loader
    from beancount.core import data as beancount_data

    from compteqc.categorisation.ml import PredicteurML

    chemin_main = get_ledger_path()
    if not chemin_main.exists():
        console.print(f"[red]Ledger introuvable: {chemin_main}[/red]")
        raise typer.Exit(1)

    entries, _, _ = loader.load_file(str(chemin_main))

    # Extraire les donnees d'entrainement (transactions approuvees, non pending)
    donnees = []
    for entry in entries:
        if not isinstance(entry, beancount_data.Transaction):
            continue
        if entry.flag != "*":
            continue
        if "pending" in (entry.tags or set()):
            continue
        payee = entry.payee or ""
        narration = entry.narration or ""
        for posting in entry.postings:
            if (
                posting.account.startswith("Depenses:")
                and posting.account != "Depenses:Non-Classe"
            ):
                donnees.append((payee, narration, posting.account))
                break

    if not donnees:
        console.print("[yellow]Aucune donnee d'entrainement trouvee.[/yellow]")
        return

    predicteur = PredicteurML()
    predicteur.entrainer(donnees)

    if predicteur.est_entraine:
        comptes = set(c for _, _, c in donnees)
        console.print(
            f"[green]Modele ML entraine sur {len(donnees)} transactions, "
            f"{len(comptes)} comptes distincts[/green]"
        )

        # Sauvegarder le modele
        import joblib

        chemin_modele = Path("data/ml/modele.pkl")
        chemin_modele.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(predicteur, chemin_modele)
        console.print(f"Modele sauvegarde: {chemin_modele}")
    else:
        console.print(
            f"[yellow]Donnees insuffisantes pour l'entrainement: "
            f"{len(donnees)} transactions (minimum {PredicteurML.MIN_TRAINING_SIZE})[/yellow]"
        )
