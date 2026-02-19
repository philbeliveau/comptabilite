"""Gestion des transactions en attente de revision (pending.beancount).

Les transactions classees par IA avec confiance intermediaire sont
stagees dans pending.beancount avec le tag #pending. Les utilisateurs
peuvent ensuite les approuver ou les rejeter.
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path

from beancount.core import data
from beancount.parser import parser as beancount_parser
from beancount.parser import printer

from compteqc.categorisation.pipeline import ResultatPipeline
from compteqc.ledger.fichiers import (
    ajouter_include,
    chemin_fichier_mensuel,
    ecrire_transactions,
)

logger = logging.getLogger(__name__)

_ENTETE_PENDING = """\
; Transactions en attente de revision
option "name_assets" "Actifs"
option "name_liabilities" "Passifs"
option "name_equity" "Capital"
option "name_income" "Revenus"
option "name_expenses" "Depenses"
"""


def ecrire_pending(
    chemin_pending: Path,
    transactions: list[data.Transaction],
    resultats: list[ResultatPipeline],
) -> int:
    """Ecrit des transactions dans pending.beancount avec le tag #pending.

    Args:
        chemin_pending: Chemin vers pending.beancount.
        transactions: Liste de transactions Beancount.
        resultats: Resultats pipeline correspondants (meme ordre).

    Returns:
        Nombre de transactions ecrites.
    """
    if not transactions:
        return 0

    txns_pending = []
    for txn, resultat in zip(transactions, resultats):
        txn_pending = _preparer_pending(txn, resultat)
        txns_pending.append(txn_pending)

    texte = "\n".join(printer.format_entry(t) for t in txns_pending)

    if not chemin_pending.exists():
        chemin_pending.write_text(_ENTETE_PENDING, encoding="utf-8")

    ecrire_transactions(chemin_pending, texte)

    return len(txns_pending)


def _preparer_pending(
    txn: data.Transaction,
    resultat: ResultatPipeline,
) -> data.Transaction:
    """Prepare une transaction pour pending.beancount.

    Ajoute le tag #pending et les metadata AI.
    """
    # Ajouter le tag #pending
    tags = set(txn.tags) if txn.tags else set()
    tags.add("pending")

    # Construire les metadata
    meta = copy.copy(txn.meta)
    meta["source_ia"] = resultat.source
    meta["confiance"] = str(resultat.confiance)
    meta["compte_propose"] = resultat.compte

    if resultat.est_capex:
        meta["capex"] = "oui"
        if resultat.classe_dpa is not None:
            meta["classe_dpa_suggeree"] = str(resultat.classe_dpa)

    if resultat.suggestions is not None:
        ml_info = resultat.suggestions.get("ml")
        llm_info = resultat.suggestions.get("llm")
        if ml_info:
            meta["suggestion_ml"] = f"{ml_info[0]} ({ml_info[1]:.2f})"
        if llm_info:
            meta["suggestion_llm"] = f"{llm_info[0]} ({llm_info[1]:.2f})"

    # Remplacer le posting Non-Classe par le compte propose
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

    return data.Transaction(
        meta=meta,
        date=txn.date,
        flag="!",
        payee=txn.payee,
        narration=txn.narration,
        tags=frozenset(tags),
        links=txn.links,
        postings=nouveaux_postings,
    )


def lire_pending(chemin_pending: Path) -> list[data.Transaction]:
    """Lit les transactions #pending depuis pending.beancount.

    Args:
        chemin_pending: Chemin vers pending.beancount.

    Returns:
        Liste de transactions avec le tag #pending. Liste vide si le
        fichier n'existe pas.
    """
    if not chemin_pending.exists():
        return []

    # Utiliser le parser directement (sans validation des comptes Open)
    # car pending.beancount est un fichier isole sans declarations de comptes.
    contenu = chemin_pending.read_text(encoding="utf-8")
    entries, errors, _ = beancount_parser.parse_string(contenu)

    if errors:
        for err in errors:
            logger.warning("Erreur de syntaxe dans pending.beancount: %s", err)

    return [
        entry
        for entry in entries
        if isinstance(entry, data.Transaction) and "pending" in (entry.tags or set())
    ]


def approuver_transactions(
    chemin_pending: Path,
    chemin_main: Path,
    indices: list[int],
) -> int:
    """Approuve des transactions pending et les deplace vers les fichiers mensuels.

    Args:
        chemin_pending: Chemin vers pending.beancount.
        chemin_main: Chemin vers main.beancount.
        indices: Indices (0-based) des transactions a approuver.

    Returns:
        Nombre de transactions approuvees.
    """
    pending = lire_pending(chemin_pending)
    if not pending:
        return 0

    indices_set = set(indices)
    a_approuver = []
    restantes = []

    for i, txn in enumerate(pending):
        if i in indices_set:
            a_approuver.append(txn)
        else:
            restantes.append(txn)

    if not a_approuver:
        return 0

    # Sauvegarder pour rollback
    contenu_pending_avant = chemin_pending.read_text(encoding="utf-8")
    ledger_dir = chemin_main.parent

    fichiers_modifies: dict[Path, str | None] = {}

    try:
        # Ecrire chaque transaction approuvee dans son fichier mensuel
        for txn in a_approuver:
            txn_approuvee = _finaliser_approbation(txn)
            fichier_mensuel = chemin_fichier_mensuel(
                txn.date.year, txn.date.month, ledger_dir
            )

            # Sauvegarder pour rollback
            if fichier_mensuel not in fichiers_modifies:
                if fichier_mensuel.exists():
                    fichiers_modifies[fichier_mensuel] = fichier_mensuel.read_text(
                        encoding="utf-8"
                    )
                else:
                    fichiers_modifies[fichier_mensuel] = None

            texte = printer.format_entry(txn_approuvee)
            ecrire_transactions(fichier_mensuel, texte)

            chemin_relatif = str(fichier_mensuel.relative_to(ledger_dir))
            ajouter_include(chemin_main, chemin_relatif)

        # Reecrire pending.beancount avec les transactions restantes
        _reecrire_pending(chemin_pending, restantes)

        # Valider le ledger
        from compteqc.ledger.validation import valider_ledger

        valide, erreurs = valider_ledger(chemin_main)

        if not valide:
            logger.error(
                "Validation echouee apres approbation. Rollback."
            )
            for err in erreurs:
                logger.error("  %s", err)

            # Rollback
            chemin_pending.write_text(contenu_pending_avant, encoding="utf-8")
            for fichier, contenu in fichiers_modifies.items():
                if contenu is not None:
                    fichier.write_text(contenu, encoding="utf-8")
                elif fichier.exists():
                    fichier.unlink()
            return 0

    except Exception:
        logger.error("Erreur lors de l'approbation. Rollback.", exc_info=True)
        chemin_pending.write_text(contenu_pending_avant, encoding="utf-8")
        for fichier, contenu in fichiers_modifies.items():
            if contenu is not None:
                fichier.write_text(contenu, encoding="utf-8")
            elif fichier.exists():
                fichier.unlink()
        return 0

    return len(a_approuver)


def _finaliser_approbation(txn: data.Transaction) -> data.Transaction:
    """Retire le tag #pending et change le flag de ! a *."""
    tags = set(txn.tags) if txn.tags else set()
    tags.discard("pending")

    meta = copy.copy(txn.meta)
    meta["approuve"] = "oui"

    return data.Transaction(
        meta=meta,
        date=txn.date,
        flag="*",
        payee=txn.payee,
        narration=txn.narration,
        tags=frozenset(tags),
        links=txn.links,
        postings=txn.postings,
    )


def rejeter_transactions(
    chemin_pending: Path,
    indices: list[int],
) -> int:
    """Rejette des transactions pending (les supprime).

    Args:
        chemin_pending: Chemin vers pending.beancount.
        indices: Indices (0-based) des transactions a rejeter.

    Returns:
        Nombre de transactions rejetees.
    """
    pending = lire_pending(chemin_pending)
    if not pending:
        return 0

    indices_set = set(indices)
    restantes = [txn for i, txn in enumerate(pending) if i not in indices_set]
    nb_rejetees = len(pending) - len(restantes)

    if nb_rejetees > 0:
        _reecrire_pending(chemin_pending, restantes)

    return nb_rejetees


def _reecrire_pending(chemin_pending: Path, transactions: list[data.Transaction]) -> None:
    """Reecrit pending.beancount avec les transactions fournies."""
    contenu = _ENTETE_PENDING

    if transactions:
        contenu += "\n" + "\n".join(printer.format_entry(t) for t in transactions)

    chemin_pending.write_text(contenu, encoding="utf-8")


def assurer_include_pending(chemin_main: Path, chemin_pending: Path) -> None:
    """Ajoute l'include pour pending.beancount dans main.beancount si necessaire."""
    ledger_dir = chemin_main.parent
    chemin_relatif = str(chemin_pending.relative_to(ledger_dir))
    ajouter_include(chemin_main, chemin_relatif)
