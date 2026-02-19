"""Sous-commande d'import de fichiers bancaires pour CompteQC."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from beancount import loader
from beancount.parser import printer
from rich.console import Console
from rich.table import Table

from compteqc.categorisation import MoteurRegles, appliquer_categorisation
from compteqc.categorisation.regles import charger_regles
from compteqc.ingestion import RBCCarteImporter, RBCChequesImporter, RBCOfxImporter, archiver_fichier
from compteqc.ledger.fichiers import ajouter_include, chemin_fichier_mensuel, ecrire_transactions
from compteqc.ledger.git import auto_commit
from compteqc.ledger.validation import charger_comptes_existants, valider_ledger

importer_app = typer.Typer(no_args_is_help=True)
console = Console()


def _detecter_importateur(chemin: str, compte: str):
    """Detecte l'importateur approprie pour le fichier.

    Args:
        chemin: Chemin du fichier a importer.
        compte: Type de compte (CHEQUES, CARTE, AUTO).

    Returns:
        L'importateur detecte.

    Raises:
        typer.Exit: Si aucun importateur ne reconnait le fichier.
    """
    if compte == "CHEQUES":
        imp = RBCChequesImporter()
        if imp.identify(chemin):
            return imp
        console.print(
            "[red]Erreur:[/red] Le fichier ne correspond pas au format CSV cheques RBC.",
            style="bold",
        )
        raise typer.Exit(1)

    if compte == "CARTE":
        imp = RBCCarteImporter()
        if imp.identify(chemin):
            return imp
        console.print(
            "[red]Erreur:[/red] Le fichier ne correspond pas au format CSV carte credit RBC.",
            style="bold",
        )
        raise typer.Exit(1)

    # AUTO: essayer tous les importateurs
    importateurs = [
        RBCChequesImporter(),
        RBCCarteImporter(),
        RBCOfxImporter(account="Actifs:Banque:RBC:Cheques", account_id=""),
    ]

    # Pour OFX, on essaie de parser sans filtre de compte
    path = Path(chemin)
    if path.suffix.lower() in (".ofx", ".qfx"):
        # Parser l'OFX pour recuperer l'account ID
        try:
            from ofxtools.Parser import OFXTree

            tree = OFXTree()
            tree.parse(chemin)
            ofx = tree.convert()
            for stmt in ofx.statements:
                acctid = stmt.account.acctid
                # Determiner le type de compte selon l'OFX
                acct_type = getattr(stmt.account, "accttype", "CHECKING")
                if acct_type in ("CHECKING", "SAVINGS"):
                    return RBCOfxImporter(
                        account="Actifs:Banque:RBC:Cheques", account_id=acctid
                    )
                else:
                    return RBCOfxImporter(
                        account="Passifs:CartesCredit:RBC", account_id=acctid
                    )
        except Exception:
            pass

    # Essayer les importateurs CSV
    for imp in importateurs[:2]:
        if imp.identify(chemin):
            return imp

    console.print(
        "[red]Erreur:[/red] Format de fichier non reconnu.",
        style="bold",
    )
    console.print("Formats supportes :")
    console.print("  - CSV compte-cheques RBC")
    console.print("  - CSV carte de credit RBC")
    console.print("  - OFX/QFX RBC")
    raise typer.Exit(1)


@importer_app.command(name="fichier")
def fichier(
    chemin_fichier: str = typer.Argument(help="Chemin du fichier bancaire a importer"),
    compte: str = typer.Option(
        "AUTO",
        "--compte",
        "-c",
        help="Type de compte : CHEQUES, CARTE, ou AUTO (detection automatique)",
    ),
) -> None:
    """Importer un fichier bancaire dans le ledger.

    Detecte automatiquement le type de fichier (CSV ou OFX) et l'importateur
    correspondant. Categorise les transactions, ecrit dans le ledger, valide
    avec bean-check, et cree un commit git automatique.
    """
    from compteqc.cli.app import get_ledger_path, get_regles_path

    chemin_main = get_ledger_path()
    chemin_regles = get_regles_path()

    # Verifier que le fichier existe
    path = Path(chemin_fichier)
    if not path.exists():
        console.print(f"[red]Erreur:[/red] Fichier introuvable : {chemin_fichier}")
        raise typer.Exit(1)

    # Verifier que le ledger existe
    if not chemin_main.exists():
        console.print(
            f"[red]Erreur:[/red] Ledger introuvable : {chemin_main}\n"
            "Verifiez le chemin avec l'option --ledger."
        )
        raise typer.Exit(1)

    # Detecter l'importateur
    console.print(f"Analyse du fichier [cyan]{path.name}[/cyan]...")
    importateur = _detecter_importateur(str(path), compte.upper())

    # Charger le ledger existant pour deduplication
    entries_existantes, errors, options = loader.load_file(str(chemin_main))

    # Extraire les transactions
    nouvelles = importateur.extract(str(path), entries_existantes)

    if not nouvelles:
        console.print(
            "[yellow]Aucune nouvelle transaction a importer.[/yellow] "
            "Le fichier a peut-etre deja ete importe."
        )
        raise typer.Exit(0)

    # Charger les regles et appliquer la categorisation
    try:
        config_regles = charger_regles(chemin_regles)
    except FileNotFoundError:
        console.print(
            f"[yellow]Avertissement:[/yellow] Fichier de regles introuvable ({chemin_regles}). "
            "Import sans categorisation."
        )
        from compteqc.categorisation.regles import ConfigRegles

        config_regles = ConfigRegles()

    comptes_valides = charger_comptes_existants(chemin_main)
    moteur = MoteurRegles(config_regles, comptes_valides)
    transactions_categorisees = appliquer_categorisation(nouvelles, moteur)

    # Compter les categorisees vs non-classees
    nb_categorisees = sum(
        1
        for t in transactions_categorisees
        if hasattr(t, "meta") and t.meta.get("categorisation") != "non-classe"
    )
    nb_non_classees = len(transactions_categorisees) - nb_categorisees

    # Determiner le fichier mensuel cible (premiere transaction)
    premiere_date = transactions_categorisees[0].date
    ledger_dir = chemin_main.parent
    fichier_mensuel = chemin_fichier_mensuel(
        premiere_date.year, premiere_date.month, ledger_dir
    )

    # Sauvegarder le fichier mensuel pour rollback
    contenu_avant = fichier_mensuel.read_text(encoding="utf-8") if fichier_mensuel.exists() else None

    # Formater les transactions en texte Beancount
    texte_beancount = "\n".join(
        printer.format_entry(txn) for txn in transactions_categorisees
    )

    # Ecrire dans le fichier mensuel
    ecrire_transactions(fichier_mensuel, texte_beancount)

    # Ajouter l'include dans main.beancount si necessaire
    chemin_relatif = str(fichier_mensuel.relative_to(ledger_dir))
    ajouter_include(chemin_main, chemin_relatif)

    # Valider le ledger
    valide, erreurs = valider_ledger(chemin_main)

    if not valide:
        # ROLLBACK : restaurer le fichier mensuel
        console.print("[red]Erreur de validation du ledger ![/red]")
        console.print("Les ecritures ont ete annulees (rollback).")
        console.print()
        for err in erreurs:
            console.print(f"  [red]{err}[/red]")

        if contenu_avant is not None:
            fichier_mensuel.write_text(contenu_avant, encoding="utf-8")
        elif fichier_mensuel.exists():
            fichier_mensuel.unlink()

        raise typer.Exit(1)

    # Archiver le fichier source
    repertoire_processed = Path("data/processed")
    archiver_fichier(path, repertoire_processed, len(transactions_categorisees))

    # Git auto-commit
    repertoire_projet = chemin_main.parent.parent
    nb_doublons = 0  # doublons deja filtres par extract()
    message_commit = (
        f"import({path.name}): {len(transactions_categorisees)} transactions "
        f"({premiere_date.strftime('%Y-%m')})"
    )

    try:
        commit_cree = auto_commit(repertoire_projet, message_commit)
    except ValueError as e:
        console.print(f"[red]Erreur lors du commit :[/red] {e}")
        commit_cree = False

    # Affichage du resume
    console.print()
    tableau = Table(title="Resume de l'import", show_header=True)
    tableau.add_column("Metrique", style="cyan")
    tableau.add_column("Valeur", style="green", justify="right")
    tableau.add_row("Transactions importees", str(len(transactions_categorisees)))
    tableau.add_row("Doublons ignores", str(nb_doublons))
    tableau.add_row("Categorisees", str(nb_categorisees))
    tableau.add_row("Non-classees", str(nb_non_classees))
    tableau.add_row("Fichier cible", str(fichier_mensuel))
    console.print(tableau)

    # Lister les transactions non-classees
    if nb_non_classees > 0:
        console.print()
        console.print(
            f"[yellow]{nb_non_classees} transaction(s) non-classee(s) :[/yellow]"
        )
        table_nc = Table(show_header=True)
        table_nc.add_column("Date", style="dim")
        table_nc.add_column("Montant", justify="right")
        table_nc.add_column("Beneficiaire")
        for txn in transactions_categorisees:
            if hasattr(txn, "meta") and txn.meta.get("categorisation") == "non-classe":
                montant = txn.postings[0].units.number if txn.postings else 0
                table_nc.add_row(
                    str(txn.date),
                    f"{montant:,.2f} CAD",
                    txn.payee or txn.narration or "",
                )
        console.print(table_nc)
        console.print(
            "\nAjoutez des regles dans le fichier de categorisation pour les classer automatiquement."
        )

    if commit_cree:
        console.print(f"\n[green]Commit git cree :[/green] {message_commit}")
    else:
        console.print(
            "\n[yellow]Aucun commit git cree[/yellow] (pas de changements ou erreur)."
        )
