"""Sous-commandes de rapport pour CompteQC (soldes, balance, resultats, bilan, revue)."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import typer
from beancount import loader
from beancount.core import data
from rich.console import Console
from rich.table import Table

rapport_app = typer.Typer(no_args_is_help=True)
console = Console()


def _charger_ledger(chemin_main):
    """Charge le ledger et retourne (entries, errors, options)."""
    from pathlib import Path

    path = Path(chemin_main)
    if not path.exists():
        console.print(f"[red]Erreur:[/red] Ledger introuvable : {chemin_main}")
        raise typer.Exit(1)
    return loader.load_file(str(path))


def _calculer_soldes(entries) -> dict[str, Decimal]:
    """Calcule les soldes de chaque compte a partir des transactions.

    Returns:
        Dictionnaire {nom_compte: solde_CAD}.
    """
    soldes_dict: dict[str, Decimal] = {}
    for entry in entries:
        if isinstance(entry, data.Transaction):
            for posting in entry.postings:
                if posting.units:
                    acct = posting.account
                    soldes_dict[acct] = soldes_dict.get(acct, Decimal("0")) + posting.units.number
    return soldes_dict


def _formater_montant(montant: Decimal) -> str:
    """Formate un montant en CAD avec 2 decimales et separateur de milliers."""
    return f"{montant:,.2f}"


def soldes(
    compte: Optional[str] = typer.Option(
        None,
        "--compte",
        "-c",
        help="Filtre sur le nom du compte (sous-chaine)",
    ),
) -> None:
    """Afficher les soldes de tous les comptes avec solde non-nul."""
    from compteqc.cli.app import get_ledger_path

    entries, errors, options = _charger_ledger(get_ledger_path())
    soldes_dict = _calculer_soldes(entries)

    # Filtrer les comptes avec solde non-nul
    comptes_filtres = {
        k: v for k, v in sorted(soldes_dict.items()) if v != Decimal("0")
    }

    if compte:
        filtre_upper = compte.upper()
        comptes_filtres = {
            k: v for k, v in comptes_filtres.items() if filtre_upper in k.upper()
        }

    if not comptes_filtres:
        console.print("[yellow]Aucun compte avec solde non-nul.[/yellow]")
        return

    tableau = Table(title="Soldes des comptes", show_header=True)
    tableau.add_column("Compte", style="cyan", min_width=40)
    tableau.add_column("Solde (CAD)", justify="right", style="green")

    for nom, montant in comptes_filtres.items():
        style = "green" if montant >= 0 else "red"
        tableau.add_row(nom, f"[{style}]{_formater_montant(montant)}[/{style}]")

    console.print(tableau)


@rapport_app.command(name="balance")
def balance() -> None:
    """Afficher la balance de verification (trial balance).

    Affiche tous les comptes groupes par categorie avec verification
    que le total des debits egale le total des credits.
    """
    from compteqc.cli.app import get_ledger_path

    entries, errors, options = _charger_ledger(get_ledger_path())
    soldes_dict = _calculer_soldes(entries)

    comptes_avec_solde = {k: v for k, v in sorted(soldes_dict.items()) if v != Decimal("0")}

    if not comptes_avec_solde:
        console.print("[yellow]Aucune transaction dans le ledger.[/yellow]")
        return

    # Grouper par categorie de premier niveau
    categories = ["Actifs", "Passifs", "Capital", "Revenus", "Depenses"]
    tableau = Table(title="Balance de verification", show_header=True)
    tableau.add_column("Compte", style="cyan", min_width=40)
    tableau.add_column("Debit", justify="right", style="green")
    tableau.add_column("Credit", justify="right", style="red")

    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for categorie in categories:
        comptes_cat = {
            k: v for k, v in comptes_avec_solde.items() if k.startswith(categorie)
        }
        if not comptes_cat:
            continue

        tableau.add_row(f"[bold]{categorie}[/bold]", "", "")
        for nom, montant in sorted(comptes_cat.items()):
            if montant > 0:
                tableau.add_row(f"  {nom}", _formater_montant(montant), "")
                total_debit += montant
            else:
                tableau.add_row(f"  {nom}", "", _formater_montant(abs(montant)))
                total_credit += abs(montant)

    tableau.add_section()
    tableau.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{_formater_montant(total_debit)}[/bold]",
        f"[bold]{_formater_montant(total_credit)}[/bold]",
    )

    console.print(tableau)

    if total_debit != total_credit:
        diff = total_debit - total_credit
        console.print(
            f"\n[red]AVERTISSEMENT : La balance ne balance pas ! "
            f"Difference : {_formater_montant(diff)} CAD[/red]"
        )
    else:
        console.print("\n[green]Balance equilibree.[/green]")


@rapport_app.command(name="resultats")
def resultats(
    debut: Optional[str] = typer.Option(None, "--debut", help="Date de debut (AAAA-MM-JJ)"),
    fin: Optional[str] = typer.Option(None, "--fin", help="Date de fin (AAAA-MM-JJ)"),
) -> None:
    """Afficher l'etat des resultats (revenus et depenses).

    Par defaut, affiche toutes les transactions. Utiliser --debut et --fin
    pour filtrer par periode.
    """
    import datetime

    from compteqc.cli.app import get_ledger_path

    entries, errors, options = _charger_ledger(get_ledger_path())

    # Filtrer par dates si specifie
    date_debut = datetime.date.fromisoformat(debut) if debut else None
    date_fin = datetime.date.fromisoformat(fin) if fin else None

    revenus: dict[str, Decimal] = {}
    depenses: dict[str, Decimal] = {}

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        if date_debut and entry.date < date_debut:
            continue
        if date_fin and entry.date > date_fin:
            continue

        for posting in entry.postings:
            if posting.units is None:
                continue
            acct = posting.account
            montant = posting.units.number
            if acct.startswith("Revenus"):
                revenus[acct] = revenus.get(acct, Decimal("0")) + montant
            elif acct.startswith("Depenses"):
                depenses[acct] = depenses.get(acct, Decimal("0")) + montant

    if not revenus and not depenses:
        console.print("[yellow]Aucune transaction de revenus ou depenses.[/yellow]")
        return

    tableau = Table(title="Etat des resultats", show_header=True)
    tableau.add_column("Poste", style="cyan", min_width=40)
    tableau.add_column("Montant (CAD)", justify="right")

    # Revenus (en beancount, les revenus sont negatifs car credit)
    total_revenus = Decimal("0")
    tableau.add_row("[bold green]REVENUS[/bold green]", "")
    for nom, montant in sorted(revenus.items()):
        # Afficher les revenus en positif (inverser le signe beancount)
        montant_affiche = -montant
        total_revenus += montant_affiche
        tableau.add_row(f"  {nom}", f"[green]{_formater_montant(montant_affiche)}[/green]")
    tableau.add_row(
        "[bold]Total revenus[/bold]",
        f"[bold green]{_formater_montant(total_revenus)}[/bold green]",
    )

    tableau.add_section()

    # Depenses (positives en beancount)
    total_depenses = Decimal("0")
    tableau.add_row("[bold red]DEPENSES[/bold red]", "")
    for nom, montant in sorted(depenses.items()):
        total_depenses += montant
        tableau.add_row(f"  {nom}", f"[red]{_formater_montant(montant)}[/red]")
    tableau.add_row(
        "[bold]Total depenses[/bold]",
        f"[bold red]{_formater_montant(total_depenses)}[/bold red]",
    )

    tableau.add_section()

    # Resultat net
    resultat_net = total_revenus - total_depenses
    style = "green" if resultat_net >= 0 else "red"
    tableau.add_row(
        "[bold]RESULTAT NET[/bold]",
        f"[bold {style}]{_formater_montant(resultat_net)}[/bold {style}]",
    )

    console.print(tableau)


@rapport_app.command(name="bilan")
def bilan() -> None:
    """Afficher le bilan (actifs, passifs, capitaux propres).

    Verifie l'equation comptable : Actifs = Passifs + Capitaux propres.
    """
    from compteqc.cli.app import get_ledger_path

    entries, errors, options = _charger_ledger(get_ledger_path())
    soldes_dict = _calculer_soldes(entries)

    actifs: dict[str, Decimal] = {}
    passifs: dict[str, Decimal] = {}
    capitaux: dict[str, Decimal] = {}

    for acct, montant in soldes_dict.items():
        if montant == Decimal("0"):
            continue
        if acct.startswith("Actifs"):
            actifs[acct] = montant
        elif acct.startswith("Passifs"):
            passifs[acct] = montant
        elif acct.startswith("Capital"):
            capitaux[acct] = montant

    # Inclure le resultat net (Revenus - Depenses) dans les capitaux propres
    resultat_net = Decimal("0")
    for acct, montant in soldes_dict.items():
        if acct.startswith("Revenus"):
            resultat_net -= montant  # Revenus sont negatifs en beancount
        elif acct.startswith("Depenses"):
            resultat_net -= montant  # Depenses sont positives, on les soustrait

    if not actifs and not passifs and not capitaux and resultat_net == 0:
        console.print("[yellow]Aucune donnee pour generer le bilan.[/yellow]")
        return

    tableau = Table(title="Bilan", show_header=True)
    tableau.add_column("Poste", style="cyan", min_width=40)
    tableau.add_column("Montant (CAD)", justify="right")

    # Actifs
    total_actifs = Decimal("0")
    tableau.add_row("[bold]ACTIFS[/bold]", "")
    for nom, montant in sorted(actifs.items()):
        total_actifs += montant
        tableau.add_row(f"  {nom}", _formater_montant(montant))
    tableau.add_row(
        "[bold]Total actifs[/bold]",
        f"[bold]{_formater_montant(total_actifs)}[/bold]",
    )

    tableau.add_section()

    # Passifs
    total_passifs = Decimal("0")
    tableau.add_row("[bold]PASSIFS[/bold]", "")
    for nom, montant in sorted(passifs.items()):
        # Passifs sont negatifs en beancount, afficher en positif
        total_passifs += abs(montant)
        tableau.add_row(f"  {nom}", _formater_montant(abs(montant)))
    tableau.add_row(
        "[bold]Total passifs[/bold]",
        f"[bold]{_formater_montant(total_passifs)}[/bold]",
    )

    # Capitaux propres
    total_capitaux = Decimal("0")
    tableau.add_row("[bold]CAPITAUX PROPRES[/bold]", "")
    for nom, montant in sorted(capitaux.items()):
        total_capitaux += abs(montant)
        tableau.add_row(f"  {nom}", _formater_montant(abs(montant)))
    if resultat_net != 0:
        total_capitaux += resultat_net
        tableau.add_row("  Resultat net de l'exercice", _formater_montant(resultat_net))
    tableau.add_row(
        "[bold]Total capitaux propres[/bold]",
        f"[bold]{_formater_montant(total_capitaux)}[/bold]",
    )

    tableau.add_section()

    total_passifs_capitaux = total_passifs + total_capitaux
    tableau.add_row(
        "[bold]TOTAL PASSIFS + CAPITAUX[/bold]",
        f"[bold]{_formater_montant(total_passifs_capitaux)}[/bold]",
    )

    console.print(tableau)

    # Verifier l'equation comptable
    if total_actifs == total_passifs_capitaux:
        console.print(
            "\n[green]Equation comptable verifiee : Actifs = Passifs + Capitaux propres[/green]"
        )
    else:
        diff = total_actifs - total_passifs_capitaux
        console.print(
            f"\n[red]AVERTISSEMENT : L'equation comptable ne balance pas ! "
            f"Difference : {_formater_montant(diff)} CAD[/red]"
        )


def revue() -> None:
    """Afficher les transactions non-classees pour revision.

    Liste toutes les transactions dont un posting est vers Depenses:Non-Classe.
    """
    from compteqc.cli.app import get_ledger_path

    entries, errors, options = _charger_ledger(get_ledger_path())

    non_classees = []
    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        for posting in entry.postings:
            if posting.account == "Depenses:Non-Classe":
                non_classees.append((entry, posting))
                break

    if not non_classees:
        console.print("[green]Aucune transaction non-classee. Tout est categorise ![/green]")
        return

    tableau = Table(title="Transactions non-classees", show_header=True)
    tableau.add_column("Date", style="dim")
    tableau.add_column("Montant (CAD)", justify="right")
    tableau.add_column("Beneficiaire", style="cyan")
    tableau.add_column("Narration")

    total = Decimal("0")
    for txn, posting in non_classees:
        montant = posting.units.number if posting.units else Decimal("0")
        total += abs(montant)
        tableau.add_row(
            str(txn.date),
            _formater_montant(abs(montant)),
            txn.payee or "",
            txn.narration or "",
        )

    console.print(tableau)
    console.print(
        f"\n[yellow]{len(non_classees)} transaction(s) non-classee(s) "
        f"pour un total de {_formater_montant(total)} CAD.[/yellow]"
    )
    console.print(
        "Ajoutez des regles dans le fichier de categorisation pour les classer automatiquement."
    )
