"""Sous-commande de revision des transactions en attente pour CompteQC.

Permet de lister, approuver, rejeter ou recategoriser les transactions
classees par IA et en attente de revision humaine.
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path

import typer
from beancount.core import data
from beancount.parser import printer
from rich.console import Console
from rich.table import Table

from compteqc.categorisation.feedback import (
    ajouter_regle_auto,
    enregistrer_correction,
)
from compteqc.categorisation.pending import (
    approuver_transactions,
    lire_pending,
    rejeter_transactions,
)
from compteqc.ledger.fichiers import (
    ajouter_include,
    chemin_fichier_mensuel,
    ecrire_transactions,
)
from compteqc.ledger.git import auto_commit

logger = logging.getLogger(__name__)

reviser_app = typer.Typer(no_args_is_help=True)
console = Console()

CHEMIN_HISTORIQUE_DEFAUT = Path("data/corrections/historique.json")


def _get_paths() -> tuple[Path, Path, Path, Path]:
    """Retourne les chemins ledger, pending, regles, historique."""
    from compteqc.cli.app import get_ledger_path, get_regles_path

    chemin_main = get_ledger_path()
    ledger_dir = chemin_main.parent
    chemin_pending = ledger_dir / "pending.beancount"
    chemin_regles = get_regles_path()

    return chemin_main, chemin_pending, chemin_regles, CHEMIN_HISTORIQUE_DEFAUT


def _confiance_float(txn: data.Transaction) -> float:
    """Extrait la confiance d'une transaction pending."""
    raw = txn.meta.get("confiance", "0.0")
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def _est_obligatoire(txn: data.Transaction) -> bool:
    """Determine si la revision est obligatoire (<80% confiance)."""
    return _confiance_float(txn) < 0.80


def _confiance_style(confiance: float) -> str:
    """Retourne le style Rich pour un niveau de confiance."""
    if confiance < 0.80:
        return "red"
    if confiance <= 0.95:
        return "yellow"
    return "green"


def _parse_indices(indices_str: str, total: int) -> list[int]:
    """Parse une chaine d'indices en liste d'indices 0-based.

    Accepte: "1,3,5", "1-5", "all", "optionnel" (tous 80-95%).
    Les indices de l'utilisateur sont 1-based, convertis en 0-based.
    """
    indices_str = indices_str.strip().lower()

    if indices_str == "all":
        return list(range(total))

    # "optionnel" est gere par l'appelant (besoin des transactions)
    if indices_str == "optionnel":
        return []  # Sentinel, gere par l'appelant

    result = []
    for part in indices_str.split(","):
        part = part.strip()
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start = int(start_str)
            end = int(end_str)
            result.extend(range(start - 1, end))  # 1-based to 0-based
        else:
            result.append(int(part) - 1)  # 1-based to 0-based

    return [i for i in result if 0 <= i < total]


@reviser_app.command(name="liste")
def liste(
    vendeur: str | None = typer.Option(
        None, "--vendeur", help="Filtrer par sous-chaine du vendeur"
    ),
    confiance_min: float | None = typer.Option(
        None, "--confiance-min", help="Confiance minimum"
    ),
    confiance_max: float | None = typer.Option(
        None, "--confiance-max", help="Confiance maximum"
    ),
    obligatoire: bool = typer.Option(
        False, "--obligatoire", help="Afficher seulement les revisions obligatoires (<80%)"
    ),
) -> None:
    """Afficher les transactions en attente de revision."""
    _, chemin_pending, _, _ = _get_paths()

    pending = lire_pending(chemin_pending)

    if not pending:
        console.print("Aucune transaction en attente de revision.")
        return

    # Appliquer les filtres
    filtered = pending
    if vendeur:
        v_upper = vendeur.upper()
        filtered = [
            t for t in filtered
            if v_upper in (t.payee or "").upper() or v_upper in (t.narration or "").upper()
        ]
    if confiance_min is not None:
        filtered = [t for t in filtered if _confiance_float(t) >= confiance_min]
    if confiance_max is not None:
        filtered = [t for t in filtered if _confiance_float(t) <= confiance_max]
    if obligatoire:
        filtered = [t for t in filtered if _est_obligatoire(t)]

    if not filtered:
        console.print("Aucune transaction correspondant aux filtres.")
        return

    # Separer obligatoires et optionnelles
    obligatoires = [t for t in filtered if _est_obligatoire(t)]
    optionnelles = [t for t in filtered if not _est_obligatoire(t)]

    tableau = Table(title="Transactions en attente de revision")
    tableau.add_column("#", style="dim", width=4)
    tableau.add_column("Date", width=10)
    tableau.add_column("Montant", justify="right", width=12)
    tableau.add_column("Beneficiaire", width=25)
    tableau.add_column("Compte propose", width=30)
    tableau.add_column("Conf.", width=6)
    tableau.add_column("Source", width=6)
    tableau.add_column("Drapeaux", width=10)

    row_num = 0

    def _ajouter_ligne(txn: data.Transaction) -> None:
        nonlocal row_num
        row_num += 1

        conf = _confiance_float(txn)
        conf_pct = f"{conf * 100:.0f}%"
        style = _confiance_style(conf)

        # Montant (premier posting est le credit bancaire, negatif; second est le debit)
        montant_str = ""
        for posting in txn.postings:
            if posting.account.startswith("Depenses:") or posting.account.startswith("Actifs:"):
                if (
                    posting.account.startswith("Depenses:")
                    or not posting.account.startswith("Actifs:Banque")
                ):
                    montant_str = f"{posting.units.number:,.2f}"
                    break
        if not montant_str and txn.postings:
            montant_str = f"{txn.postings[0].units.number:,.2f}"

        montant_style = "red" if montant_str.startswith("-") else ""

        beneficiaire = (txn.payee or txn.narration or "")[:25]
        compte = txn.meta.get("compte_propose", "")
        source = txn.meta.get("source_ia", "")

        drapeaux = []
        if txn.meta.get("capex") == "oui":
            drapeaux.append("CAPEX")
        if _est_obligatoire(txn):
            drapeaux.append("!")

        tableau.add_row(
            str(row_num),
            str(txn.date),
            f"[{montant_style}]{montant_str}[/{montant_style}]" if montant_style else montant_str,
            beneficiaire,
            compte,
            f"[{style}]{conf_pct}[/{style}]",
            source,
            " ".join(drapeaux),
        )

    # Ajouter les obligatoires d'abord
    for txn in obligatoires:
        _ajouter_ligne(txn)

    if obligatoires and optionnelles:
        tableau.add_row("---", "---", "---", "---", "---", "---", "---", "---")

    for txn in optionnelles:
        _ajouter_ligne(txn)

    console.print(tableau)

    nb_oblig = len(obligatoires)
    nb_opt = len(optionnelles)
    console.print(
        f"\n{len(filtered)} transactions en attente "
        f"({nb_oblig} obligatoires, {nb_opt} optionnelles)"
    )


@reviser_app.command(name="approuver")
def approuver(
    indices: str = typer.Argument(
        help="Indices des transactions (ex: 1,3,5 ou 1-5 ou all ou optionnel)"
    ),
) -> None:
    """Approuver des transactions en attente."""
    chemin_main, chemin_pending, _, _ = _get_paths()

    pending = lire_pending(chemin_pending)
    if not pending:
        console.print("Aucune transaction en attente.")
        return

    if indices.strip().lower() == "optionnel":
        # Approuver toutes les optionnelles (80-95%)
        idx_list = [
            i for i, t in enumerate(pending)
            if not _est_obligatoire(t)
        ]
    else:
        idx_list = _parse_indices(indices, len(pending))

    if not idx_list:
        console.print("Aucune transaction selectionnee.")
        return

    nb = approuver_transactions(chemin_pending, chemin_main, idx_list)

    if nb > 0:
        # Git auto-commit
        repertoire_projet = chemin_main.parent.parent
        try:
            auto_commit(repertoire_projet, f"reviser: approuve {nb} transactions")
        except (ValueError, Exception) as e:
            logger.warning("Erreur lors du commit: %s", e)

        console.print(
            f"[green]{nb} transaction(s) approuvee(s) et deplacee(s) vers le ledger.[/green]"
        )
    else:
        console.print(
            "[yellow]Aucune transaction approuvee.[/yellow] "
            "Verification du ledger echouee ou indices invalides."
        )


@reviser_app.command(name="rejeter")
def rejeter(
    indices: str = typer.Argument(
        help="Indices des transactions (ex: 1,3,5 ou 1-5)"
    ),
) -> None:
    """Rejeter des transactions en attente (les supprimer)."""
    chemin_main, chemin_pending, _, _ = _get_paths()

    pending = lire_pending(chemin_pending)
    if not pending:
        console.print("Aucune transaction en attente.")
        return

    idx_list = _parse_indices(indices, len(pending))
    if not idx_list:
        console.print("Aucune transaction selectionnee.")
        return

    nb = rejeter_transactions(chemin_pending, idx_list)

    if nb > 0:
        repertoire_projet = chemin_main.parent.parent
        try:
            auto_commit(repertoire_projet, f"reviser: rejete {nb} transactions")
        except (ValueError, Exception) as e:
            logger.warning("Erreur lors du commit: %s", e)

        console.print(f"[red]{nb} transaction(s) rejetee(s).[/red]")
    else:
        console.print("[yellow]Aucune transaction rejetee.[/yellow]")


@reviser_app.command(name="recategoriser")
def recategoriser(
    indice: int = typer.Argument(help="Numero de la transaction (1-based)"),
    compte: str = typer.Argument(help="Nouveau compte comptable"),
    note: str | None = typer.Option(
        None, "--note", "-n", help="Note optionnelle"
    ),
) -> None:
    """Recategoriser une transaction en attente."""
    chemin_main, chemin_pending, chemin_regles, chemin_historique = _get_paths()

    pending = lire_pending(chemin_pending)
    if not pending:
        console.print("Aucune transaction en attente.")
        return

    idx = indice - 1  # 1-based to 0-based
    if idx < 0 or idx >= len(pending):
        console.print(f"[red]Indice invalide: {indice}. Plage valide: 1-{len(pending)}[/red]")
        return

    # Valider le compte
    from compteqc.ledger.validation import charger_comptes_existants

    comptes_valides = charger_comptes_existants(chemin_main)
    if comptes_valides and compte not in comptes_valides:
        console.print(f"[red]Compte invalide: {compte}[/red]")
        console.print("Comptes commencant par Depenses: disponibles:")
        for c in sorted(comptes_valides):
            if c.startswith("Depenses:"):
                console.print(f"  {c}")
        return

    txn = pending[idx]
    vendeur = txn.payee or txn.narration or ""
    compte_original = txn.meta.get("compte_propose")

    # Enregistrer la correction et verifier si une regle doit etre generee
    regle = enregistrer_correction(
        chemin_historique,
        vendeur,
        compte,
        compte_original=compte_original,
        note=note,
    )

    if regle is not None:
        ajouter_regle_auto(chemin_regles, regle)
        console.print(
            f"[cyan]Nouvelle regle auto-generee pour {vendeur} -> {compte}[/cyan]"
        )

    # Mettre a jour la transaction avec le nouveau compte
    nouveaux_postings = []
    for posting in txn.postings:
        if posting.account == txn.meta.get("compte_propose", "") or (
            posting.account.startswith("Depenses:")
            and posting.account != "Depenses:Non-Classe"
        ):
            nouveau = data.Posting(
                account=compte,
                units=posting.units,
                cost=posting.cost,
                price=posting.price,
                flag=posting.flag,
                meta=posting.meta,
            )
            nouveaux_postings.append(nouveau)
        elif posting.account == "Depenses:Non-Classe":
            nouveau = data.Posting(
                account=compte,
                units=posting.units,
                cost=posting.cost,
                price=posting.price,
                flag=posting.flag,
                meta=posting.meta,
            )
            nouveaux_postings.append(nouveau)
        else:
            nouveaux_postings.append(posting)

    # Retirer le tag pending, mettre flag *
    tags = set(txn.tags) if txn.tags else set()
    tags.discard("pending")

    meta = copy.copy(txn.meta)
    meta["approuve"] = "oui"
    meta["recategorise"] = "oui"
    meta["compte_original"] = compte_original or ""
    meta["compte_corrige"] = compte

    txn_corrigee = data.Transaction(
        meta=meta,
        date=txn.date,
        flag="*",
        payee=txn.payee,
        narration=txn.narration,
        tags=frozenset(tags),
        links=txn.links,
        postings=nouveaux_postings,
    )

    # Ecrire dans le fichier mensuel
    ledger_dir = chemin_main.parent
    fichier_mensuel = chemin_fichier_mensuel(
        txn.date.year, txn.date.month, ledger_dir
    )

    texte = printer.format_entry(txn_corrigee)
    ecrire_transactions(fichier_mensuel, texte)
    chemin_relatif = str(fichier_mensuel.relative_to(ledger_dir))
    ajouter_include(chemin_main, chemin_relatif)

    # Retirer du pending
    restantes = [t for i, t in enumerate(pending) if i != idx]
    from compteqc.categorisation.pending import _reecrire_pending

    _reecrire_pending(chemin_pending, restantes)

    # Valider le ledger
    from compteqc.ledger.validation import valider_ledger

    valide, erreurs = valider_ledger(chemin_main)
    if not valide:
        console.print("[red]Erreur de validation du ledger apres recategorisation![/red]")
        for err in erreurs:
            console.print(f"  [red]{err}[/red]")
        return

    # Git auto-commit
    repertoire_projet = chemin_main.parent.parent
    try:
        auto_commit(repertoire_projet, f"reviser: recategorise {vendeur} -> {compte}")
    except (ValueError, Exception) as e:
        logger.warning("Erreur lors du commit: %s", e)

    console.print(
        f"[green]Transaction recategorisee: {vendeur} -> {compte}[/green]"
    )


@reviser_app.command(name="journal")
def journal() -> None:
    """Afficher les transactions recemment auto-approuvees (>95% confiance)."""
    chemin_main, _, _, _ = _get_paths()

    from beancount import loader

    entries, _, _ = loader.load_file(str(chemin_main))

    auto_approuvees = []
    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        source = entry.meta.get("source_ia")
        if source not in ("ml", "llm"):
            continue
        conf = entry.meta.get("confiance", "0.0")
        try:
            conf_float = float(conf)
        except (ValueError, TypeError):
            continue
        if conf_float > 0.95:
            auto_approuvees.append((entry, conf_float))

    if not auto_approuvees:
        console.print("Aucune transaction auto-approuvee recente.")
        return

    tableau = Table(title="Transactions auto-approuvees (>95%)", style="green")
    tableau.add_column("#", style="dim", width=4)
    tableau.add_column("Date", width=10)
    tableau.add_column("Beneficiaire", width=25)
    tableau.add_column("Compte", width=30)
    tableau.add_column("Conf.", width=6)
    tableau.add_column("Source", width=6)

    for i, (txn, conf) in enumerate(auto_approuvees, 1):
        beneficiaire = (txn.payee or txn.narration or "")[:25]
        compte = ""
        for p in txn.postings:
            if p.account.startswith("Depenses:"):
                compte = p.account
                break

        tableau.add_row(
            str(i),
            str(txn.date),
            beneficiaire,
            compte,
            f"{conf * 100:.0f}%",
            txn.meta.get("source_ia", ""),
        )

    console.print(tableau)
    console.print(f"\n{len(auto_approuvees)} transactions auto-approuvees.")
