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
from compteqc.rapprochement import suggerer_rapprochement_ar, suggerer_rapprochement_ap
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
                (posting.account.startswith("Depenses:") or posting.account == "Passifs:Pret-Actionnaire")
                and posting.account != "Depenses:Non-Classe"
            ):
                donnees.append((payee, narration, posting.account))
                break
    return donnees


def _appliquer_pipeline_et_router(
    txn: data.Transaction,
    pipeline: PipelineCategorisation | None,
    source_type: str = "corporate",
) -> tuple[data.Transaction, str, "ResultatPipeline"]:
    """Applique le pipeline et route la transaction.

    Args:
        txn: Transaction beancount a router.
        pipeline: Pipeline de categorisation (None si source_type == "personal").
        source_type: "corporate" (pipeline normal) ou "personal" (tout -> Pret-Actionnaire).

    Returns:
        Tuple (transaction_modifiee, destination, resultat_pipeline).
    """
    from compteqc.categorisation.pipeline import ResultatPipeline

    # Short-circuit pour les comptes personnels: tout va en Pret-Actionnaire
    if source_type == "personal":
        nouveaux_postings = []
        for posting in txn.postings:
            if posting.account == "Depenses:Non-Classe":
                nouveau = data.Posting(
                    account="Passifs:Pret-Actionnaire",
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
        meta["categorisation"] = "personal"
        meta["source_type"] = "personal"

        txn = data.Transaction(
            meta=meta,
            date=txn.date,
            flag="*",
            payee=txn.payee,
            narration=txn.narration,
            tags=txn.tags,
            links=txn.links,
            postings=nouveaux_postings,
        )

        resultat = ResultatPipeline(
            compte="Passifs:Pret-Actionnaire",
            confiance=1.0,
            source="personal",
            regle=None,
            est_capex=False,
            classe_dpa=None,
            revue_obligatoire=False,
            suggestions=None,
        )
        return txn, "direct", resultat

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
    source_type: str = "corporate",
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

    # Creer le pipeline (inutile pour source personnelle)
    pipeline = None
    if source_type != "personal":
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
        txn_mod, destination, resultat = _appliquer_pipeline_et_router(txn, pipeline, source_type)

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


def _beancount_vers_transactions(entries: list) -> list:
    """Convertit les entries beancount en TransactionNormalisee pour le rapprochement."""
    from compteqc.models.transaction import TransactionNormalisee

    transactions = []
    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        montant = entry.postings[0].units.number if entry.postings else Decimal(0)
        transactions.append(
            TransactionNormalisee(
                date=entry.date,
                montant=montant,
                beneficiaire=entry.payee or "",
                description=entry.narration or "",
                source="import",
            )
        )
    return transactions


def _afficher_rapprochements(
    transactions: list,
    console: Console,
    chemin_registre_ar: Path | None = None,
    chemin_registre_ap: Path | None = None,
) -> None:
    """Affiche les suggestions de rapprochement AR/AP pour les transactions importees.

    Charge les registres de factures et fournisseurs, puis suggere des correspondances
    entre les transactions importees et les factures ouvertes.

    Args:
        transactions: Liste de TransactionNormalisee.
        console: Console Rich pour l'affichage.
        chemin_registre_ar: Chemin optionnel au registre AR (defaut: ledger/factures/registre.yaml).
        chemin_registre_ap: Chemin optionnel au registre AP (defaut: ledger/fournisseurs/registre.yaml).
    """
    if not transactions:
        return

    # AR matching
    toutes_suggestions_ar = []
    try:
        from compteqc.factures.registre import RegistreFactures

        registre_path = chemin_registre_ar or Path("ledger/factures/registre.yaml")
        if registre_path.exists():
            registre = RegistreFactures(registre_path)
            factures_ouvertes = registre.lister_impayees()
            if factures_ouvertes:
                for txn in transactions:
                    suggestions = suggerer_rapprochement_ar(txn, factures_ouvertes)
                    for s in suggestions:
                        toutes_suggestions_ar.append((txn, s))
    except Exception:
        pass

    # AP matching
    toutes_suggestions_ap = []
    try:
        from compteqc.fournisseurs.registre import RegistreFournisseurs

        registre_path = chemin_registre_ap or Path("ledger/fournisseurs/registre.yaml")
        if registre_path.exists():
            registre_four = RegistreFournisseurs(registre_path)
            bills_ouvertes = registre_four.lister_impayees()
            if bills_ouvertes:
                for txn in transactions:
                    suggestions = suggerer_rapprochement_ap(txn, bills_ouvertes)
                    for s in suggestions:
                        toutes_suggestions_ap.append((txn, s))
    except ImportError:
        pass  # AP module not yet available

    # Display AR suggestions
    if toutes_suggestions_ar:
        console.print()
        table_ar = Table(title="Rapprochements AR suggeres")
        table_ar.add_column("Transaction", style="cyan")
        table_ar.add_column("Facture", style="green")
        table_ar.add_column("Client", style="white")
        table_ar.add_column("Montant", style="yellow", justify="right")
        table_ar.add_column("Confiance", style="magenta", justify="right")

        for txn, sugg in toutes_suggestions_ar:
            table_ar.add_row(
                f"{txn.date} {txn.beneficiaire[:20]}",
                sugg.reference,
                sugg.nom,
                f"{sugg.montant_attendu:,.2f} $",
                f"{sugg.confiance:.0%}",
            )

        console.print(table_ar)
        console.print(
            "\n[dim]Pour appliquer un rapprochement, utilisez:"
            " [cyan]cqc facture payer <NUMERO>[/cyan][/dim]"
        )

    # Display AP suggestions
    if toutes_suggestions_ap:
        console.print()
        table_ap = Table(title="Rapprochements AP suggeres")
        table_ap.add_column("Transaction", style="cyan")
        table_ap.add_column("Facture", style="green")
        table_ap.add_column("Fournisseur", style="white")
        table_ap.add_column("Montant", style="yellow", justify="right")
        table_ap.add_column("Confiance", style="magenta", justify="right")

        for txn, sugg in toutes_suggestions_ap:
            table_ap.add_row(
                f"{txn.date} {txn.beneficiaire[:20]}",
                sugg.reference,
                sugg.nom,
                f"{sugg.montant_attendu:,.2f} $",
                f"{sugg.confiance:.0%}",
            )

        console.print(table_ap)
        console.print(
            "\n[dim]Pour appliquer un rapprochement, utilisez:"
            " [cyan]cqc fournisseur payer <NUMERO>[/cyan][/dim]"
        )


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
    source_type: str = typer.Option(
        "corporate",
        "--source-type",
        "-s",
        help="Type de source : corporate (normal) ou personal (tout -> Pret-Actionnaire)",
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

    if source_type not in ("corporate", "personal"):
        console.print(
            f"[red]Erreur:[/red] --source-type invalide : '{source_type}'. "
            "Valeurs acceptees : corporate, personal."
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
    nb_entries_avant_import = len(entries_existantes)

    total_importees = 0
    total_regles = 0
    total_ia_auto = 0
    total_pending = 0

    for imp in importateurs:
        type_label = imp.account("")
        console.print(f"\nImport [cyan]{type_label}[/cyan]...")

        nb_imp, nb_reg, nb_ia, nb_pend = _importer_avec(
            imp, path, chemin_main, chemin_regles, entries_existantes,
            source_type=source_type,
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
    if source_type == "personal":
        console.print(
            "[cyan]Source: personnel (tout -> Pret-Actionnaire)[/cyan]"
        )
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

    # Display AR/AP match suggestions for the newly imported transactions
    try:
        entries_finales, _, _ = loader.load_file(str(chemin_main))
        nouvelles_entries = entries_finales[nb_entries_avant_import:]
        if nouvelles_entries:
            transactions_pour_matching = _beancount_vers_transactions(nouvelles_entries)
            if transactions_pour_matching:
                _afficher_rapprochements(transactions_pour_matching, console)
    except Exception:
        pass  # Don't let matching errors break the import
