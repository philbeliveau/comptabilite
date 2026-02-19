"""Commandes CLI pour la gestion des recus et documents."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

receipt_app = typer.Typer(name="recu", help="Gestion des recus et documents")
console = Console()


@receipt_app.command(name="telecharger")
def telecharger(
    chemin: str = typer.Argument(help="Chemin vers le fichier du recu (image ou PDF)"),
) -> None:
    """Telecharger un recu, extraire les donnees et proposer des correspondances."""
    from beancount import loader
    from beancount.core import data as beancount_data

    from compteqc.cli.app import get_ledger_path
    from compteqc.documents.beancount_link import ecrire_directive, generer_directive_document
    from compteqc.documents.extraction import extraire_recu
    from compteqc.documents.matching import proposer_correspondances
    from compteqc.documents.upload import renommer_recu, telecharger_recu

    source = Path(chemin)
    ledger_path = get_ledger_path()
    ledger_dir = ledger_path.parent

    # 1. Telecharger
    try:
        stored_path = telecharger_recu(source, ledger_dir)
        console.print(f"[green]Fichier telecharge: {stored_path}[/green]")
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Erreur: {e}[/red]")
        raise typer.Exit(1)

    # 2. Extraction via Claude Vision
    console.print("[dim]Extraction des donnees via Claude Vision...[/dim]")
    try:
        donnees = extraire_recu(stored_path)
    except Exception as e:
        console.print(f"[red]Erreur d'extraction: {e}[/red]")
        raise typer.Exit(1)

    # 3. Afficher les donnees extraites
    table = Table(title="Donnees extraites du recu")
    table.add_column("Champ", style="cyan")
    table.add_column("Valeur", style="white")

    table.add_row("Fournisseur", donnees.fournisseur)
    table.add_row("Date", donnees.date)
    table.add_row("Sous-total", f"{donnees.sous_total} $")
    table.add_row("TPS (5%)", f"{donnees.montant_tps} $" if donnees.montant_tps else "N/A")
    table.add_row("TVQ (9.975%)", f"{donnees.montant_tvq} $" if donnees.montant_tvq else "N/A")
    table.add_row("Total", f"{donnees.total} $")
    table.add_row("Confiance", f"{donnees.confiance:.0%}")

    console.print(table)

    # 4. Avertissement si faible confiance
    if donnees.confiance < 0.5:
        console.print(
            "[bold yellow]Qualite insuffisante -- verifiez les donnees manuellement[/bold yellow]"
        )

    # 5. Renommer avec les donnees extraites
    stored_path = renommer_recu(stored_path, donnees)
    console.print(f"Fichier renomme: {stored_path.name}")

    # 6. Proposer des correspondances
    if not ledger_path.exists():
        console.print("[yellow]Ledger introuvable, aucune correspondance proposee.[/yellow]")
        return

    entries, _, _ = loader.load_file(str(ledger_path))
    correspondances = proposer_correspondances(donnees, entries)

    if not correspondances:
        console.print("[yellow]Aucune correspondance trouvee dans le ledger.[/yellow]")
        return

    table_match = Table(title="Correspondances proposees")
    table_match.add_column("#", style="cyan")
    table_match.add_column("Date", style="white")
    table_match.add_column("Narration", style="white")
    table_match.add_column("Montant", style="green")
    table_match.add_column("Score", style="yellow")

    for idx, c in enumerate(correspondances[:3], 1):
        indicateur = " *" if c.score >= 0.8 else ""
        table_match.add_row(
            str(idx),
            str(c.date),
            c.narration[:50],
            f"{c.montant} $",
            f"{c.score:.0%}{indicateur}",
        )

    console.print(table_match)

    # 7. Demander selection
    choix = typer.prompt(
        "Numero de correspondance (ou 's' pour passer)",
        default="s",
    )

    if choix.lower() == "s":
        console.print("Aucune correspondance selectionnee.")
        return

    try:
        idx_choisi = int(choix) - 1
        if 0 <= idx_choisi < len(correspondances[:3]):
            match = correspondances[idx_choisi]

            # Trouver le compte de la transaction
            txn = [e for e in entries if isinstance(e, beancount_data.Transaction)][
                match.transaction_index
            ]
            compte = txn.postings[0].account if txn.postings else "Depenses:Non-Classe"

            # Generer et ecrire la directive
            chemin_rel = str(stored_path.relative_to(ledger_dir))
            directive = generer_directive_document(match.date, compte, chemin_rel)
            ecrire_directive(directive, ledger_dir, match.date.year, match.date.month)

            console.print(f"[green]Directive document ecrite: {directive}[/green]")
        else:
            console.print("[red]Numero invalide.[/red]")
    except ValueError:
        console.print("[red]Entree invalide.[/red]")

    console.print(f"\nFichier stocke: {stored_path}")


@receipt_app.command(name="lister")
def lister(
    annee: Optional[int] = typer.Option(None, "--annee", "-a", help="Filtrer par annee"),
    mois: Optional[int] = typer.Option(None, "--mois", "-m", help="Filtrer par mois"),
) -> None:
    """Lister les documents recus stockes dans le ledger."""
    from compteqc.cli.app import get_ledger_path

    ledger_dir = get_ledger_path().parent
    docs_dir = ledger_dir / "documents"

    if not docs_dir.exists():
        console.print("[yellow]Aucun document stocke.[/yellow]")
        return

    table = Table(title="Documents stockes")
    table.add_column("Fichier", style="cyan")
    table.add_column("Fournisseur", style="white")
    table.add_column("Date", style="white")
    table.add_column("Lie", style="green")

    # Collecter les fichiers
    fichiers: list[Path] = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.pdf"):
        fichiers.extend(docs_dir.rglob(ext))

    # Filtrer par annee/mois si specifie
    for f in sorted(fichiers):
        parts = f.relative_to(docs_dir).parts
        if len(parts) >= 2:
            file_annee = int(parts[0])
            file_mois = int(parts[1])
            if annee and file_annee != annee:
                continue
            if mois and file_mois != mois:
                continue

        # Extraire fournisseur du nom de fichier (format: YYYY-MM-DD.vendor.ext)
        nom = f.stem
        parts_nom = nom.split(".", 1)
        fournisseur = parts_nom[1] if len(parts_nom) > 1 else "?"
        date_str = parts_nom[0] if parts_nom else "?"

        # Verifier si lie (directive document existe) -- simplifie
        lie = "?"  # Necessiterait parser le ledger

        table.add_row(f.name, fournisseur, date_str, lie)

    if not fichiers:
        console.print("[yellow]Aucun document trouve pour la periode specifiee.[/yellow]")
        return

    console.print(table)


@receipt_app.command(name="lier")
def lier(
    chemin_fichier: str = typer.Argument(help="Chemin du document a lier"),
    compte: str = typer.Argument(help="Compte Beancount associe"),
    date_str: str = typer.Option(
        ..., "--date", "-d", help="Date de la directive (YYYY-MM-DD)"
    ),
) -> None:
    """Lier manuellement un document a un compte Beancount."""
    import datetime

    from compteqc.cli.app import get_ledger_path
    from compteqc.documents.beancount_link import ecrire_directive, generer_directive_document

    ledger_dir = get_ledger_path().parent

    try:
        date_directive = datetime.date.fromisoformat(date_str)
    except ValueError:
        console.print(f"[red]Date invalide: {date_str}. Format attendu: YYYY-MM-DD[/red]")
        raise typer.Exit(1)

    chemin = Path(chemin_fichier)
    try:
        chemin_rel = str(chemin.relative_to(ledger_dir))
    except ValueError:
        chemin_rel = chemin_fichier

    directive = generer_directive_document(date_directive, compte, chemin_rel)
    ecrire_directive(directive, ledger_dir, date_directive.year, date_directive.month)

    console.print(f"[green]Directive document ecrite: {directive}[/green]")
