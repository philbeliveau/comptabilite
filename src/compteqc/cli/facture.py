"""Sous-commandes CLI pour la gestion des factures."""

from __future__ import annotations

import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from compteqc.factures.modeles import (
    ConfigFacturation,
    Facture,
    InvoiceStatus,
    LigneFacture,
)
from compteqc.factures.registre import RegistreFactures

facture_app = typer.Typer(no_args_is_help=True)
console = Console()


def _get_config_path() -> Path:
    """Retourne le chemin du fichier de configuration de facturation."""
    from compteqc.cli.app import get_ledger_path

    return get_ledger_path().parent / "factures" / "config.yaml"


def _charger_config() -> ConfigFacturation:
    """Charge la configuration de facturation depuis le YAML."""
    config_path = _get_config_path()
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        default = ConfigFacturation()
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                default.model_dump(mode="json"),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        console.print(
            f"[yellow]Fichier de configuration cree: {config_path}[/yellow]\n"
            "[yellow]Veuillez remplir vos informations d'entreprise.[/yellow]"
        )
        return default

    with open(config_path, encoding="utf-8") as f:
        donnees = yaml.safe_load(f)
    return ConfigFacturation.model_validate(donnees or {})


def _get_registre() -> RegistreFactures:
    """Retourne le registre de factures."""
    from compteqc.cli.app import get_ledger_path

    chemin = get_ledger_path().parent / "factures" / "registre.yaml"
    return RegistreFactures(chemin=chemin)


def _statut_style(statut: InvoiceStatus) -> str:
    """Retourne le style Rich pour un statut de facture."""
    styles = {
        InvoiceStatus.DRAFT: "dim",
        InvoiceStatus.SENT: "yellow",
        InvoiceStatus.PAID: "green",
        InvoiceStatus.OVERDUE: "red bold",
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


@facture_app.command(name="creer")
def creer(
    client: str = typer.Option(..., "--client", "-c", prompt="Nom du client"),
    adresse: str = typer.Option("", "--adresse", "-a", prompt="Adresse du client"),
    description: str = typer.Option(
        ..., "--description", "-d", prompt="Description du service"
    ),
    quantite: str = typer.Option("1", "--quantite", "-q", prompt="Quantite"),
    prix: str = typer.Option(..., "--prix", "-p", prompt="Prix unitaire"),
    echeance_jours: int = typer.Option(
        30, "--echeance", "-e", help="Jours avant echeance"
    ),
    notes: str = typer.Option("", "--notes", "-n", help="Notes additionnelles"),
) -> None:
    """Creer une nouvelle facture."""
    from compteqc.factures.journal import generer_ecriture_facture

    try:
        prix_decimal = Decimal(prix)
        quantite_decimal = Decimal(quantite)
    except InvalidOperation:
        console.print("[red]Erreur: montant ou quantite invalide[/red]")
        raise typer.Exit(1)

    registre = _get_registre()
    aujourdhui = datetime.date.today()
    numero = registre.prochain_numero(aujourdhui.year)

    ligne = LigneFacture(
        description=description,
        quantite=quantite_decimal,
        prix_unitaire=prix_decimal,
    )

    facture = Facture(
        numero=numero,
        nom_client=client,
        adresse_client=adresse,
        date=aujourdhui,
        date_echeance=aujourdhui + datetime.timedelta(days=echeance_jours),
        lignes=[ligne],
        notes=notes,
    )

    # Afficher apercu
    console.print(f"\n[bold]Apercu de la facture {numero}[/bold]")
    console.print(f"  Client: {client}")
    console.print(f"  {description}: {quantite} x {_formater_montant(prix_decimal)}")
    console.print(f"  Sous-total: {_formater_montant(facture.sous_total)}")
    console.print(f"  TPS (5%): {_formater_montant(facture.tps)}")
    console.print(f"  TVQ (9,975%): {_formater_montant(facture.tvq)}")
    console.print(f"  [bold]Total: {_formater_montant(facture.total)}[/bold]")

    registre.ajouter(facture)
    console.print(f"\n[green]Facture {numero} creee (brouillon)[/green]")

    # Generer ecriture AR
    ecriture = generer_ecriture_facture(facture)
    _appendice_beancount(ecriture)


@facture_app.command(name="lister")
def lister(
    statut: Optional[str] = typer.Option(
        None, "--statut", "-s", help="Filtrer par statut (draft, sent, paid, overdue)"
    ),
) -> None:
    """Lister les factures."""
    registre = _get_registre()

    filtre_statut = None
    if statut:
        try:
            filtre_statut = InvoiceStatus(statut.lower())
        except ValueError:
            console.print(f"[red]Statut invalide: {statut}[/red]")
            console.print("Statuts valides: draft, sent, paid, overdue")
            raise typer.Exit(1)

    factures = registre.lister(statut=filtre_statut)

    if not factures:
        console.print("[yellow]Aucune facture trouvee.[/yellow]")
        return

    tableau = Table(title="Factures", show_header=True)
    tableau.add_column("Numero", style="cyan")
    tableau.add_column("Client")
    tableau.add_column("Date")
    tableau.add_column("Echeance")
    tableau.add_column("Total", justify="right")
    tableau.add_column("Statut")

    for f in factures:
        style = _statut_style(f.statut)
        tableau.add_row(
            f.numero,
            f.nom_client,
            str(f.date),
            str(f.date_echeance),
            _formater_montant(f.total),
            f"[{style}]{f.statut.value.upper()}[/{style}]",
        )

    console.print(tableau)


@facture_app.command(name="voir")
def voir(
    numero: str = typer.Argument(help="Numero de la facture"),
) -> None:
    """Afficher les details d'une facture."""
    registre = _get_registre()
    facture = registre.obtenir(numero)

    if facture is None:
        console.print(f"[red]Facture {numero} introuvable[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Facture {facture.numero}[/bold]")
    console.print(f"  Client: {facture.nom_client}")
    if facture.adresse_client:
        console.print(f"  Adresse: {facture.adresse_client}")
    console.print(f"  Date: {facture.date}")
    console.print(f"  Echeance: {facture.date_echeance}")
    style = _statut_style(facture.statut)
    console.print(f"  Statut: [{style}]{facture.statut.value.upper()}[/{style}]")
    if facture.date_paiement:
        console.print(f"  Date de paiement: {facture.date_paiement}")

    console.print("\n  [bold]Lignes:[/bold]")
    for ligne in facture.lignes:
        console.print(
            f"    {ligne.description}: {ligne.quantite} x "
            f"{_formater_montant(ligne.prix_unitaire)} = "
            f"{_formater_montant(ligne.sous_total)}"
        )

    console.print(f"\n  Sous-total: {_formater_montant(facture.sous_total)}")
    console.print(f"  TPS (5%): {_formater_montant(facture.tps)}")
    console.print(f"  TVQ (9,975%): {_formater_montant(facture.tvq)}")
    console.print(f"  [bold]Total: {_formater_montant(facture.total)}[/bold]")

    if facture.notes:
        console.print(f"\n  Notes: {facture.notes}")


@facture_app.command(name="pdf")
def pdf(
    numero: str = typer.Argument(help="Numero de la facture"),
) -> None:
    """Generer le PDF d'une facture."""
    from compteqc.factures.generateur import generer_pdf

    registre = _get_registre()
    facture = registre.obtenir(numero)

    if facture is None:
        console.print(f"[red]Facture {numero} introuvable[/red]")
        raise typer.Exit(1)

    config = _charger_config()

    from compteqc.cli.app import get_ledger_path

    output_dir = get_ledger_path().parent / "factures" / "pdf"
    chemin = generer_pdf(facture, config, output_dir)
    console.print(f"[green]PDF genere: {chemin}[/green]")


@facture_app.command(name="envoyer")
def envoyer(
    numero: str = typer.Argument(help="Numero de la facture"),
) -> None:
    """Marquer une facture comme envoyee."""
    registre = _get_registre()
    facture = registre.obtenir(numero)

    if facture is None:
        console.print(f"[red]Facture {numero} introuvable[/red]")
        raise typer.Exit(1)

    registre.mettre_a_jour_statut(numero, InvoiceStatus.SENT)
    console.print(f"[green]Facture {numero} marquee comme ENVOYEE[/green]")


@facture_app.command(name="payer")
def payer(
    numero: str = typer.Argument(help="Numero de la facture"),
    date: Optional[str] = typer.Option(
        None, "--date", "-d", help="Date de paiement (AAAA-MM-JJ)"
    ),
) -> None:
    """Marquer une facture comme payee et generer l'ecriture de paiement."""
    from compteqc.factures.journal import generer_ecriture_paiement

    registre = _get_registre()
    facture = registre.obtenir(numero)

    if facture is None:
        console.print(f"[red]Facture {numero} introuvable[/red]")
        raise typer.Exit(1)

    date_paiement = datetime.date.fromisoformat(date) if date else datetime.date.today()

    facture_payee = registre.mettre_a_jour_statut(
        numero, InvoiceStatus.PAID, date_paiement=date_paiement
    )
    console.print(f"[green]Facture {numero} marquee comme PAYEE ({date_paiement})[/green]")

    # Generer ecriture de paiement
    ecriture = generer_ecriture_paiement(facture_payee)
    _appendice_beancount(ecriture)


@facture_app.command(name="relances")
def relances() -> None:
    """Afficher les factures en souffrance (envoyees et depassant l'echeance)."""
    registre = _get_registre()
    aujourdhui = datetime.date.today()

    factures_envoyees = registre.lister(statut=InvoiceStatus.SENT)
    en_retard = [f for f in factures_envoyees if f.date_echeance < aujourdhui]

    # Aussi inclure celles deja marquees OVERDUE
    factures_overdue = registre.lister(statut=InvoiceStatus.OVERDUE)

    # Marquer automatiquement les envoyees en retard comme OVERDUE
    for f in en_retard:
        registre.mettre_a_jour_statut(f.numero, InvoiceStatus.OVERDUE)

    toutes_en_retard = en_retard + factures_overdue

    if not toutes_en_retard:
        console.print("[green]Aucune facture en souffrance.[/green]")
        return

    tableau = Table(title="Factures en souffrance", show_header=True)
    tableau.add_column("Numero", style="cyan")
    tableau.add_column("Client")
    tableau.add_column("Echeance", style="red")
    tableau.add_column("Jours de retard", justify="right", style="red bold")
    tableau.add_column("Total", justify="right")

    for f in toutes_en_retard:
        jours = (aujourdhui - f.date_echeance).days
        tableau.add_row(
            f.numero,
            f.nom_client,
            str(f.date_echeance),
            str(jours),
            _formater_montant(f.total),
        )

    console.print(tableau)
