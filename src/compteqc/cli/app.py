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
from compteqc.cli.facture import facture_app  # noqa: E402
from compteqc.cli.receipt import receipt_app  # noqa: E402
from compteqc.cli.reviser import reviser_app  # noqa: E402

app.add_typer(importer_app, name="importer", help="Importer des fichiers bancaires")
app.add_typer(paie_app, name="paie", help="Gestion de la paie")
app.add_typer(rapport_app, name="rapport", help="Rapports financiers (balance, resultats, bilan)")
app.add_typer(reviser_app, name="reviser", help="Reviser les transactions en attente")
app.add_typer(facture_app, name="facture", help="Gestion des factures")
app.add_typer(receipt_app, name="recu", help="Gestion des recus et documents")
app.command(name="soldes", help="Afficher les soldes de tous les comptes")(soldes)
app.command(name="revue", help="Afficher les transactions non-classees")(revue)

# --- Echeances sub-app ---
echeances_app = typer.Typer(
    name="echeances",
    help="Echeances fiscales et rappels de production",
    no_args_is_help=True,
)
app.add_typer(echeances_app, name="echeances", help="Echeances fiscales et rappels de production")


@echeances_app.command(name="calendrier")
def echeances_calendrier(
    annee: Optional[int] = typer.Option(None, "--annee", "-a", help="Annee fiscale (defaut: annee courante)"),
    fin_mois: Optional[int] = typer.Option(12, "--fin-mois", help="Mois de fin d'exercice (defaut: 12)"),
    fin_jour: Optional[int] = typer.Option(31, "--fin-jour", help="Jour de fin d'exercice (defaut: 31)"),
) -> None:
    """Afficher le calendrier des echeances fiscales."""
    import datetime

    from rich.table import Table

    from compteqc.echeances.calendrier import (
        calculer_echeances,
        obtenir_alertes,
    )

    if annee is None:
        annee = datetime.date.today().year

    fin_exercice = datetime.date(annee, fin_mois or 12, fin_jour or 31)
    echeances = calculer_echeances(fin_exercice)
    alertes = obtenir_alertes(echeances)

    # Index alertes par echeance pour lookup rapide
    alerte_map = {id(a.echeance): a for a in alertes}
    # Re-map par date+type+desc
    alerte_lookup: dict[tuple, str] = {}
    for a in alertes:
        key = (a.echeance.type, a.echeance.date_limite, a.echeance.description)
        alerte_lookup[key] = (a.jours_restants, a.urgence)

    table = Table(title=f"Echeances fiscales - Exercice {fin_exercice}")
    table.add_column("Type", style="bold")
    table.add_column("Date limite")
    table.add_column("Description")
    table.add_column("Jours restants", justify="right")
    table.add_column("Urgence")

    couleur_map = {
        "critique": "red",
        "urgent": "yellow",
        "normal": "blue",
        "info": "dim",
    }

    aujourd_hui = datetime.date.today()
    for ech in echeances:
        jours = (ech.date_limite - aujourd_hui).days
        key = (ech.type, ech.date_limite, ech.description)
        info = alerte_lookup.get(key)
        if info:
            jours_r, urgence = info
            couleur = couleur_map.get(urgence, "")
            table.add_row(
                ech.type.value,
                str(ech.date_limite),
                ech.description,
                f"[{couleur}]{jours_r}[/{couleur}]",
                f"[{couleur}]{urgence}[/{couleur}]",
            )
        else:
            table.add_row(
                ech.type.value,
                str(ech.date_limite),
                ech.description,
                str(jours) if jours >= 0 else "passe",
                "",
            )

    console.print(table)


@echeances_app.command(name="remises")
def echeances_remises(
    annee: Optional[int] = typer.Option(None, "--annee", "-a", help="Annee a analyser (defaut: annee courante)"),
) -> None:
    """Afficher l'etat des remises de paie par mois."""
    import datetime

    from beancount import loader
    from rich.table import Table

    from compteqc.echeances.remises import suivi_remises

    if annee is None:
        annee = datetime.date.today().year

    chemin_main = get_ledger_path()
    if not chemin_main.exists():
        console.print(f"[red]Ledger introuvable: {chemin_main}[/red]")
        raise typer.Exit(1)

    entries, _, _ = loader.load_file(str(chemin_main))
    remises = suivi_remises(entries, annee)

    table = Table(title=f"Remises de paie - {annee}")
    table.add_column("Mois", justify="right")
    table.add_column("Retenues dues", justify="right")
    table.add_column("Cotisations dues", justify="right")
    table.add_column("Total du", justify="right")
    table.add_column("Total remis", justify="right")
    table.add_column("Solde", justify="right")

    mois_noms = [
        "", "Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre",
    ]

    for r in remises:
        style = "red" if r.solde > 0 else ""
        table.add_row(
            mois_noms[r.mois],
            f"{r.retenues_dues:,.2f}",
            f"{r.cotisations_dues:,.2f}",
            f"{r.total_du:,.2f}",
            f"{r.total_remis:,.2f}",
            f"[{style}]{r.solde:,.2f}[/{style}]" if style else f"{r.solde:,.2f}",
        )

    console.print(table)


@echeances_app.command(name="rappels")
def echeances_rappels(
    fin_mois: Optional[int] = typer.Option(12, "--fin-mois", help="Mois de fin d'exercice (defaut: 12)"),
    fin_jour: Optional[int] = typer.Option(31, "--fin-jour", help="Jour de fin d'exercice (defaut: 31)"),
) -> None:
    """Afficher les rappels actifs (echeances dans les 30 prochains jours)."""
    import datetime

    from compteqc.echeances.calendrier import (
        calculer_echeances,
        formater_rappels_cli,
        obtenir_alertes,
    )

    annee = datetime.date.today().year
    fin_exercice = datetime.date(annee, fin_mois or 12, fin_jour or 31)
    echeances = calculer_echeances(fin_exercice)
    alertes = obtenir_alertes(echeances)
    rappels = formater_rappels_cli(alertes)

    if rappels:
        console.print(rappels)
    else:
        console.print("[green]Aucune echeance dans les 30 prochains jours.[/green]")


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
