"""Sous-commande d'import de fichiers bancaires pour CompteQC."""

from __future__ import annotations

import copy
import logging
from decimal import Decimal
from pathlib import Path

import typer
from beancount import loader
from beancount.core import data
from beancount.parser import printer
from rich.console import Console
from rich.table import Table

from compteqc.categorisation.capex import DetecteurCAPEX
from compteqc.categorisation.llm import ClassificateurLLM
from compteqc.categorisation.ml import PredicteurML
from compteqc.categorisation.moteur import MoteurRegles
from compteqc.categorisation.pending import assurer_include_pending, ecrire_pending
from compteqc.categorisation.pipeline import PipelineCategorisation, ResultatPipeline
from compteqc.categorisation.regles import charger_regles
from compteqc.ingestion import (
    RBCCarteImporter,
    RBCChequesImporter,
    RBCOfxImporter,
    archiver_fichier,
)
from compteqc.ledger.fichiers import (
    ajouter_include,
    chemin_fichier_mensuel,
    ecrire_transactions,
)
from compteqc.ledger.git import auto_commit
from compteqc.ledger.validation import charger_comptes_existants, valider_ledger

logger = logging.getLogger(__name__)

importer_app = typer.Typer(no_args_is_help=True)
console = Console()


def _detecter_importateurs(chemin: str, compte: str) -> list:
    """Detecte les importateurs appropries pour le fichier.

    Retourne une liste d'importateurs (peut en contenir plusieurs
    pour un fichier combine Cheques + Visa).
    """
    if compte == "CHEQUES":
        imp = RBCChequesImporter()
        if imp.identify(chemin):
            return [imp]
        console.print(
            "[red]Erreur:[/red] Le fichier ne correspond pas au format"
            " CSV cheques RBC.",
            style="bold",
        )
        raise typer.Exit(1)

    if compte == "CARTE":
        imp = RBCCarteImporter()
        if imp.identify(chemin):
            return [imp]
        console.print(
            "[red]Erreur:[/red] Le fichier ne correspond pas au format"
            " CSV carte credit RBC.",
            style="bold",
        )
        raise typer.Exit(1)

    # AUTO: detecter tous les importateurs qui reconnaissent le fichier
    path = Path(chemin)

    # OFX/QFX: essayer le parser OFX
    if path.suffix.lower() in (".ofx", ".qfx"):
        try:
            from ofxtools.Parser import OFXTree

            tree = OFXTree()
            tree.parse(chemin)
            ofx = tree.convert()
            for stmt in ofx.statements:
                acctid = stmt.account.acctid
                acct_type = getattr(stmt.account, "accttype", "CHECKING")
                if acct_type in ("CHECKING", "SAVINGS"):
                    return [RBCOfxImporter(
                        account="Actifs:Banque:RBC:Cheques",
                        account_id=acctid,
                    )]
                else:
                    return [RBCOfxImporter(
                        account="Passifs:CartesCredit:RBC",
                        account_id=acctid,
                    )]
        except Exception:
            pass

    # CSV: essayer les deux importateurs (fichier combine possible)
    resultats = []
    imp_cheques = RBCChequesImporter()
    imp_carte = RBCCarteImporter()

    if imp_cheques.identify(chemin):
        resultats.append(imp_cheques)
    if imp_carte.identify(chemin):
        resultats.append(imp_carte)

    if resultats:
        return resultats

    console.print(
        "[red]Erreur:[/red] Format de fichier non reconnu.",
        style="bold",
    )
    console.print("Formats supportes :")
    console.print("  - CSV RBC (cheques et/ou carte de credit)")
    console.print("  - OFX/QFX RBC")
    raise typer.Exit(1)


def _creer_pipeline(
    chemin_main: Path,
    chemin_regles: Path,
    comptes_valides: set[str],
    entries_existantes: list,
) -> PipelineCategorisation:
    """Cree le pipeline de categorisation a trois niveaux."""
    # Tier 1: Regles
    try:
        config_regles = charger_regles(chemin_regles)
    except FileNotFoundError:
        from compteqc.categorisation.regles import ConfigRegles
        config_regles = ConfigRegles()

    moteur = MoteurRegles(config_regles, comptes_valides)

    # Tier 2: ML (essayer d'entrainer depuis le ledger existant)
    predicteur_ml = PredicteurML()
    donnees_ml = _extraire_donnees_entrainement(entries_existantes)
    if donnees_ml:
        predicteur_ml.entrainer(donnees_ml)
        if predicteur_ml.est_entraine:
            console.print(
                f"  [dim]ML: entraine avec {len(donnees_ml)} transactions[/dim]"
            )
        else:
            console.print(
                "  [dim]ML: donnees insuffisantes pour entrainement"
                f" ({len(donnees_ml)} transactions)[/dim]"
            )
    else:
        console.print("  [dim]ML: aucune donnee d'entrainement (demarrage a froid)[/dim]")

    # Tier 3: LLM
    classificateur_llm = None
    llm = ClassificateurLLM(comptes_valides=sorted(comptes_valides))
    if llm.est_disponible:
        classificateur_llm = llm
        console.print("  [dim]LLM: OpenRouter API disponible[/dim]")
    else:
        console.print(
            "  [dim]LLM: OPENROUTER_API_KEY non definie, tier LLM desactive[/dim]"
        )

    # CAPEX
    detecteur_capex = DetecteurCAPEX()

    return PipelineCategorisation(moteur, predicteur_ml, classificateur_llm, detecteur_capex)


def _extraire_donnees_entrainement(
    entries: list,
) -> list[tuple[str, str, str]]:
    """Extrait les donnees d'entrainement depuis les transactions approuvees."""
    donnees = []
    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        # Utiliser les transactions avec flag '*' (approuvees)
        # et qui ne sont pas Non-Classe
        if entry.flag != "*":
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
    return donnees


def _appliquer_pipeline_et_router(
    txn: data.Transaction,
    pipeline: PipelineCategorisation,
) -> tuple[data.Transaction, str, "PipelineCategorisation"]:
    """Applique le pipeline et route la transaction.

    Returns:
        Tuple (transaction_modifiee, destination, resultat_pipeline).
    """
    from compteqc.categorisation.pipeline import ResultatPipeline

    payee = txn.payee or ""
    narration = txn.narration or ""
    montant = txn.postings[0].units.number if txn.postings else Decimal(0)

    # Verifier si deja categorisee
    if txn.meta.get("categorisation") != "non-classe":
        # Deja categorisee par les regles d'extraction, passe direct
        resultat = ResultatPipeline(
            compte=txn.postings[-1].account if txn.postings else "Depenses:Non-Classe",
            confiance=1.0,
            source="pre-categorise",
            regle=None,
            est_capex=False,
            classe_dpa=None,
            revue_obligatoire=False,
            suggestions=None,
        )
        return txn, "direct", resultat

    resultat = pipeline.categoriser(payee, narration, montant)
    destination = pipeline.determiner_destination(resultat)

    # Appliquer le compte categorise a la transaction
    if resultat.source != "non-classe":
        nouveaux_postings = []
        for posting in txn.postings:
            if posting.account == "Depenses:Non-Classe":
                nouveau = data.Posting(
                    account=resultat.compte,
                    units=posting.units,
                    cost=posting.cost,
                    price=posting.price,
                    flag=posting.flag,
                    meta=posting.meta,
                )
                nouveaux_postings.append(nouveau)
            else:
                nouveaux_postings.append(posting)

        meta = copy.copy(txn.meta)
        meta["categorisation"] = resultat.source
        meta["confiance"] = str(resultat.confiance)

        txn = data.Transaction(
            meta=meta,
            date=txn.date,
            flag=txn.flag,
            payee=txn.payee,
            narration=txn.narration,
            tags=txn.tags,
            links=txn.links,
            postings=nouveaux_postings,
        )

    return txn, destination, resultat


def _importer_avec(
    importateur,
    path: Path,
    chemin_main: Path,
    chemin_regles: Path,
    entries_existantes,
) -> tuple[int, int, int, int]:
    """Execute l'import pour un importateur donne.

    Retourne (nb_importees, nb_regles, nb_ia_auto, nb_pending).
    """
    # Extraire les transactions
    nouvelles = importateur.extract(str(path), entries_existantes)

    if not nouvelles:
        type_compte = importateur.account("")
        console.print(
            f"  [yellow]Aucune nouvelle transaction pour {type_compte}.[/yellow]"
        )
        return (0, 0, 0, 0)

    # Creer le pipeline
    comptes_valides = charger_comptes_existants(chemin_main)
    pipeline = _creer_pipeline(
        chemin_main, chemin_regles, comptes_valides, entries_existantes
    )

    # Router chaque transaction
    txns_direct: list[data.Transaction] = []
    txns_pending: list[tuple[data.Transaction, ResultatPipeline]] = []
    nb_regles = 0
    nb_ia_auto = 0

    for txn in nouvelles:
        txn_mod, destination, resultat = _appliquer_pipeline_et_router(txn, pipeline)

        if destination == "direct":
            txns_direct.append(txn_mod)
            if resultat.source == "regle" or resultat.source == "pre-categorise":
                nb_regles += 1
            else:
                nb_ia_auto += 1
        else:
            # "pending" ou "revue" -> staging
            txns_pending.append((txn_mod, resultat))

    # Ecrire les transactions directes dans les fichiers mensuels
    if txns_direct:
        ledger_dir = chemin_main.parent
        # Grouper par mois
        par_mois: dict[tuple[int, int], list[data.Transaction]] = {}
        for txn in txns_direct:
            key = (txn.date.year, txn.date.month)
            par_mois.setdefault(key, []).append(txn)

        for (annee, mois), txns in par_mois.items():
            fichier_mensuel = chemin_fichier_mensuel(annee, mois, ledger_dir)

            texte = "\n".join(printer.format_entry(t) for t in txns)
            ecrire_transactions(fichier_mensuel, texte)

            chemin_relatif = str(fichier_mensuel.relative_to(ledger_dir))
            ajouter_include(chemin_main, chemin_relatif)

    # Ecrire les transactions pending
    nb_pending = 0
    if txns_pending:
        ledger_dir = chemin_main.parent
        chemin_pending = ledger_dir / "pending.beancount"

        txns_list = [t for t, _ in txns_pending]
        resultats_list = [r for _, r in txns_pending]

        nb_pending = ecrire_pending(chemin_pending, txns_list, resultats_list)

        if nb_pending > 0:
            assurer_include_pending(chemin_main, chemin_pending)

    # Valider le ledger
    valide, erreurs = valider_ledger(chemin_main)

    if not valide:
        console.print("[red]Erreur de validation du ledger ![/red]")
        console.print("Les ecritures ont ete annulees (rollback).")
        for err in erreurs:
            console.print(f"  [red]{err}[/red]")
        raise typer.Exit(1)

    return (len(nouvelles), nb_regles, nb_ia_auto, nb_pending)


@importer_app.command(name="fichier")
def fichier(
    chemin_fichier: str = typer.Argument(
        help="Chemin du fichier bancaire a importer"
    ),
    compte: str = typer.Option(
        "AUTO",
        "--compte",
        "-c",
        help="Type de compte : CHEQUES, CARTE, ou AUTO (detection automatique)",
    ),
) -> None:
    """Importer un fichier bancaire dans le ledger.

    Detecte automatiquement le type de fichier (CSV ou OFX) et l'importateur
    correspondant. Pour les fichiers CSV combines (cheques + carte), les deux
    types sont importes automatiquement.
    """
    from compteqc.cli.app import get_ledger_path, get_regles_path

    chemin_main = get_ledger_path()
    chemin_regles = get_regles_path()

    path = Path(chemin_fichier)
    if not path.exists():
        console.print(
            f"[red]Erreur:[/red] Fichier introuvable : {chemin_fichier}"
        )
        raise typer.Exit(1)

    if not chemin_main.exists():
        console.print(
            f"[red]Erreur:[/red] Ledger introuvable : {chemin_main}\n"
            "Verifiez le chemin avec l'option --ledger."
        )
        raise typer.Exit(1)

    console.print(f"Analyse du fichier [cyan]{path.name}[/cyan]...")
    importateurs = _detecter_importateurs(str(path), compte.upper())

    if len(importateurs) > 1:
        console.print(
            f"[cyan]Fichier combine detecte:[/cyan]"
            f" {len(importateurs)} types de compte trouves"
        )

    # Charger le ledger existant pour deduplication
    entries_existantes, errors, options = loader.load_file(str(chemin_main))

    total_importees = 0
    total_regles = 0
    total_ia_auto = 0
    total_pending = 0

    for imp in importateurs:
        type_label = imp.account("")
        console.print(f"\nImport [cyan]{type_label}[/cyan]...")

        nb_imp, nb_reg, nb_ia, nb_pend = _importer_avec(
            imp, path, chemin_main, chemin_regles, entries_existantes,
        )

        total_importees += nb_imp
        total_regles += nb_reg
        total_ia_auto += nb_ia
        total_pending += nb_pend

        # Recharger le ledger pour le prochain importateur
        if nb_imp > 0:
            entries_existantes, errors, options = loader.load_file(
                str(chemin_main)
            )

    if total_importees == 0:
        console.print(
            "\n[yellow]Aucune nouvelle transaction a importer.[/yellow] "
            "Le fichier a peut-etre deja ete importe."
        )
        raise typer.Exit(0)

    # Archiver le fichier source
    repertoire_processed = Path("data/processed")
    archiver_fichier(path, repertoire_processed, total_importees)

    # Git auto-commit
    repertoire_projet = chemin_main.parent.parent
    message_commit = f"import({path.name}): {total_importees} transactions"

    try:
        commit_cree = auto_commit(repertoire_projet, message_commit)
    except ValueError as e:
        console.print(f"[red]Erreur lors du commit :[/red] {e}")
        commit_cree = False

    # Resume final
    total_non_classees = total_importees - total_regles - total_ia_auto - total_pending
    console.print()
    tableau = Table(title="Resume de l'import", show_header=True)
    tableau.add_column("Metrique", style="cyan")
    tableau.add_column("Valeur", style="green", justify="right")
    tableau.add_row("Transactions importees", str(total_importees))
    tableau.add_row("Categorisees par regles", str(total_regles))
    tableau.add_row("Categorisees par IA (auto)", str(total_ia_auto))
    tableau.add_row("En attente de revision", str(total_pending))
    tableau.add_row("Non-classees", str(total_non_classees))
    console.print(tableau)

    if total_pending > 0:
        console.print(
            f"\n[yellow]{total_pending} transaction(s) en attente de revision.[/yellow]"
            "\nUtilisez [cyan]cqc reviser[/cyan] pour les approuver ou rejeter."
        )

    if total_non_classees > 0:
        console.print(
            "\nAjoutez des regles dans le fichier de categorisation"
            " pour les classer automatiquement."
        )

    if commit_cree:
        console.print(f"\n[green]Commit git cree :[/green] {message_commit}")
    else:
        console.print(
            "\n[yellow]Aucun commit git cree[/yellow]"
            " (pas de changements ou erreur)."
        )
