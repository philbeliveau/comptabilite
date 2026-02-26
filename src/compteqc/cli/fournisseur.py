"""Sous-commandes CLI pour la gestion des factures fournisseurs (AP)."""

from __future__ import annotations

import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from compteqc.fournisseurs.modeles import (
    BillStatus,
    FactureFournisseur,
    LigneFactureFournisseur,
)
from compteqc.fournisseurs.registre import RegistreFournisseurs

fournisseur_app = typer.Typer(no_args_is_help=True)
console = Console()


def _get_registre() -> RegistreFournisseurs:
    """Retourne le registre de factures fournisseurs."""
    from compteqc.cli.app import get_ledger_path

    chemin = get_ledger_path().parent / "fournisseurs" / "registre.yaml"
    return RegistreFournisseurs(chemin=chemin)


def _statut_style(statut: BillStatus) -> str:
    """Retourne le style Rich pour un statut de facture fournisseur."""
    styles = {
        BillStatus.RECEIVED: "yellow",
        BillStatus.APPROVED: "blue",
        BillStatus.PAID: "green",
        BillStatus.PARTIAL: "cyan",
        BillStatus.DISPUTED: "red bold",
    }
    return styles.get(statut, "")


def _formater_montant(montant: Decimal) -> str:
    """Formate un montant avec 2 decimales."""
    return f"{montant:,.2f} $"


def _appendice_beancount(ecriture: str) -> None:
    """Ajoute une ecriture Beancount au fichier mensuel."""
    from compteqc.cli.app import get_ledger_path

    ledger_dir = get_ledger_path().parent
    aujourdhui = datetime.date.today()
    fichier_mensuel = ledger_dir / f"{aujourdhui.year}-{aujourdhui.month:02d}.beancount"

    # Creer le fichier s'il n'existe pas avec les options requises
    if not fichier_mensuel.exists():
        header = (
            f'; Transactions {aujourdhui.year}-{aujourdhui.month:02d}\n'
            'option "name_assets" "Actifs"\n'
            'option "name_liabilities" "Passifs"\n'
            'option "name_equity" "Capital"\n'
            'option "name_income" "Revenus"\n'
            'option "name_expenses" "Depenses"\n\n'
        )
        fichier_mensuel.write_text(header, encoding="utf-8")

    with open(fichier_mensuel, "a", encoding="utf-8") as f:
        f.write(f"\n{ecriture}\n")

    console.print(f"  Ecriture ajoutee a {fichier_mensuel}")


@fournisseur_app.command(name="add")
def ajouter(
    fournisseur: str = typer.Option(
        ..., "--fournisseur", "-f", prompt="Nom du fournisseur"
    ),
    reference: str = typer.Option(
        ..., "--reference", "-r", prompt="Numero de reference (facture du fournisseur)"
    ),
    description: str = typer.Option(
        ..., "--description", "-d", prompt="Description"
    ),
    montant: str = typer.Option(
        ..., "--montant", "-m", prompt="Montant (avant taxes)"
    ),
    categorie: str = typer.Option(
        ...,
        "--categorie",
        "-c",
        prompt="Categorie de depense (ex: Depenses:Bureau:Abonnements-Logiciels)",
    ),
    echeance_jours: int = typer.Option(
        30, "--echeance", "-e", help="Jours avant echeance"
    ),
    tps: bool = typer.Option(True, "--tps/--no-tps", help="TPS applicable"),
    tvq: bool = typer.Option(True, "--tvq/--no-tvq", help="TVQ applicable"),
    notes: str = typer.Option("", "--notes", "-n", help="Notes"),
) -> None:
    """Ajouter une facture fournisseur."""
    from compteqc.fournisseurs.journal import generer_ecriture_facture_fournisseur

    try:
        montant_decimal = Decimal(montant)
    except InvalidOperation:
        console.print("[red]Erreur: montant invalide[/red]")
        raise typer.Exit(1)

    if montant_decimal <= 0:
        console.print("[red]Erreur: le montant doit etre positif[/red]")
        raise typer.Exit(1)

    registre = _get_registre()
    aujourdhui = datetime.date.today()
    numero_interne = registre.prochain_numero(aujourdhui.year)

    ligne = LigneFactureFournisseur(
        description=description,
        montant=montant_decimal,
        categorie_depense=categorie,
        tps_applicable=tps,
        tvq_applicable=tvq,
    )

    facture = FactureFournisseur(
        numero_reference=reference,
        numero_interne=numero_interne,
        fournisseur=fournisseur,
        date_facture=aujourdhui,
        date_echeance=aujourdhui + datetime.timedelta(days=echeance_jours),
        lignes=[ligne],
        notes=notes,
    )

    # Afficher apercu
    console.print(f"\n[bold]Apercu de la facture fournisseur {numero_interne}[/bold]")
    console.print(f"  Fournisseur: {fournisseur}")
    console.print(f"  Reference: {reference}")
    console.print(f"  {description}: {_formater_montant(montant_decimal)}")
    console.print(f"  Sous-total: {_formater_montant(facture.montant_ht)}")
    console.print(f"  TPS (5%): {_formater_montant(facture.tps)}")
    console.print(f"  TVQ (9,975%): {_formater_montant(facture.tvq)}")
    console.print(f"  [bold]Total: {_formater_montant(facture.total)}[/bold]")

    registre.ajouter(facture)
    console.print(f"\n[green]Facture fournisseur {numero_interne} creee (received)[/green]")

    # Generer ecriture Beancount
    ecriture = generer_ecriture_facture_fournisseur(facture)
    _appendice_beancount(ecriture)


@fournisseur_app.command(name="list")
def lister(
    statut: Optional[str] = typer.Option(
        None,
        "--statut",
        "-s",
        help="Filtrer par statut (received, approved, paid, partial, disputed)",
    ),
) -> None:
    """Lister les factures fournisseurs."""
    registre = _get_registre()

    filtre_statut = None
    if statut:
        try:
            filtre_statut = BillStatus(statut.lower())
        except ValueError:
            console.print(f"[red]Statut invalide: {statut}[/red]")
            console.print(
                "Statuts valides: received, approved, paid, partial, disputed"
            )
            raise typer.Exit(1)

    factures = registre.lister(statut=filtre_statut)

    if not factures:
        console.print("[yellow]Aucune facture fournisseur trouvee.[/yellow]")
        return

    tableau = Table(title="Factures fournisseurs", show_header=True)
    tableau.add_column("N. interne", style="cyan")
    tableau.add_column("Fournisseur")
    tableau.add_column("Reference")
    tableau.add_column("Date facture")
    tableau.add_column("Echeance")
    tableau.add_column("Total", justify="right")
    tableau.add_column("Paye", justify="right")
    tableau.add_column("Solde", justify="right")
    tableau.add_column("Statut")

    for f in factures:
        style = _statut_style(f.statut)
        tableau.add_row(
            f.numero_interne,
            f.fournisseur,
            f.numero_reference,
            str(f.date_facture),
            str(f.date_echeance),
            _formater_montant(f.total),
            _formater_montant(f.montant_paye),
            _formater_montant(f.solde),
            f"[{style}]{f.statut.value.upper()}[/{style}]",
        )

    console.print(tableau)


@fournisseur_app.command(name="voir")
def voir(
    numero: str = typer.Argument(
        help="Numero interne de la facture fournisseur (ex: FOUR-2026-001)"
    ),
) -> None:
    """Afficher les details d'une facture fournisseur."""
    registre = _get_registre()
    facture = registre.obtenir(numero)

    if facture is None:
        console.print(f"[red]Facture fournisseur {numero} introuvable[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Facture fournisseur {facture.numero_interne}[/bold]")
    console.print(f"  Fournisseur: {facture.fournisseur}")
    console.print(f"  Reference: {facture.numero_reference}")
    console.print(f"  Date facture: {facture.date_facture}")
    console.print(f"  Echeance: {facture.date_echeance}")
    style = _statut_style(facture.statut)
    console.print(f"  Statut: [{style}]{facture.statut.value.upper()}[/{style}]")
    if facture.date_paiement:
        console.print(f"  Date de paiement: {facture.date_paiement}")
    if facture.methode_paiement:
        console.print(f"  Methode de paiement: {facture.methode_paiement}")

    console.print("\n  [bold]Lignes:[/bold]")
    for ligne in facture.lignes:
        console.print(
            f"    {ligne.description}: {_formater_montant(ligne.montant)}"
            f"  [{ligne.categorie_depense}]"
        )
        taxes = []
        if ligne.tps_applicable:
            taxes.append("TPS")
        if ligne.tvq_applicable:
            taxes.append("TVQ")
        if taxes:
            console.print(f"      Taxes: {', '.join(taxes)}")

    console.print(f"\n  Sous-total HT: {_formater_montant(facture.montant_ht)}")
    console.print(f"  TPS (5%): {_formater_montant(facture.tps)}")
    console.print(f"  TVQ (9,975%): {_formater_montant(facture.tvq)}")
    console.print(f"  [bold]Total: {_formater_montant(facture.total)}[/bold]")

    if facture.montant_paye > 0:
        console.print(f"\n  Montant paye: {_formater_montant(facture.montant_paye)}")
        console.print(f"  Solde: {_formater_montant(facture.solde)}")

    if facture.notes:
        console.print(f"\n  Notes: {facture.notes}")


@fournisseur_app.command(name="pay")
def payer(
    numero: str = typer.Argument(help="Numero interne (ex: FOUR-2026-001)"),
    montant: Optional[str] = typer.Option(
        None,
        "--montant",
        "-m",
        help="Montant du paiement (defaut: solde complet)",
    ),
    methode: str = typer.Option(
        "virement",
        "--methode",
        help="Methode de paiement (virement, cheque, carte-credit)",
    ),
    date: Optional[str] = typer.Option(
        None, "--date", "-d", help="Date de paiement (AAAA-MM-JJ)"
    ),
) -> None:
    """Enregistrer un paiement sur une facture fournisseur."""
    from compteqc.fournisseurs.journal import generer_ecriture_paiement_fournisseur

    registre = _get_registre()
    facture = registre.obtenir(numero)

    if facture is None:
        console.print(f"[red]Facture fournisseur {numero} introuvable[/red]")
        raise typer.Exit(1)

    if facture.statut == BillStatus.PAID:
        console.print(f"[yellow]Facture {numero} est deja entierement payee[/yellow]")
        raise typer.Exit(1)

    # Determine payment amount
    if montant is None:
        montant_decimal = facture.solde
    else:
        try:
            montant_decimal = Decimal(montant)
        except InvalidOperation:
            console.print("[red]Erreur: montant invalide[/red]")
            raise typer.Exit(1)

    if montant_decimal <= 0:
        console.print("[red]Erreur: le montant doit etre positif[/red]")
        raise typer.Exit(1)

    if montant_decimal > facture.solde:
        console.print(
            f"[red]Erreur: le montant ({_formater_montant(montant_decimal)}) "
            f"depasse le solde ({_formater_montant(facture.solde)})[/red]"
        )
        raise typer.Exit(1)

    # Determine payment date
    date_paiement = (
        datetime.date.fromisoformat(date) if date else datetime.date.today()
    )

    # Determine new status
    nouveau_paye = facture.montant_paye + montant_decimal
    if nouveau_paye >= facture.total:
        nouveau_statut = BillStatus.PAID
    else:
        nouveau_statut = BillStatus.PARTIAL

    # Update registry
    facture_maj = registre.mettre_a_jour_statut(
        numero,
        nouveau_statut,
        date_paiement=date_paiement,
        montant_paye=nouveau_paye,
        methode_paiement=methode,
    )

    # Generate Beancount payment entry
    ecriture = generer_ecriture_paiement_fournisseur(
        facture, montant=montant_decimal, methode=methode, date_paiement=date_paiement
    )
    _appendice_beancount(ecriture)

    # Print confirmation
    type_paiement = "complet" if nouveau_statut == BillStatus.PAID else "partiel"
    console.print(
        f"\n[green]Paiement {type_paiement} de {_formater_montant(montant_decimal)} "
        f"enregistre pour {numero}[/green]"
    )
    if facture_maj.solde > 0:
        console.print(f"  Solde restant: {_formater_montant(facture_maj.solde)}")
    else:
        console.print("  Facture entierement payee")
