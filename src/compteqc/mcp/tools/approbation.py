"""Outils MCP d'approbation et rejet des transactions pending.

Expose lister_pending, approuver_lot (avec garde-fou $2,000) et rejeter
(avec correction optionnelle du compte).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from compteqc.mcp.server import AppContext, mcp
from compteqc.mcp.services import formater_montant, lister_pending

SEUIL_CONFIRMATION_MONTANT = Decimal("2000")

MSG_LECTURE_SEULE = "Mode lecture seule actif. Les modifications du ledger sont desactivees."


def _chemin_pending(app: AppContext) -> Path:
    """Retourne le chemin vers pending.beancount relatif au ledger."""
    return Path(app.ledger_path).parent / "pending.beancount"


def _chemin_main(app: AppContext) -> Path:
    """Retourne le chemin vers main.beancount."""
    return Path(app.ledger_path)


def _construire_id(entry: dict) -> str:
    """Construit un identifiant composite pour une transaction pending."""
    narration = entry.get("narration", "") or ""
    return f"{entry['date']}|{entry['payee']}|{narration[:20]}"


@mcp.tool()
def lister_pending_tool(
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Lister les transactions en attente de revision (#pending).

    Retourne toutes les transactions marquees #pending avec leur confiance,
    source IA, et identifiant composite pour approbation/rejet.
    """
    app = ctx.request_context.lifespan_context
    pending = lister_pending(app.entries)

    transactions = []
    for entry in pending:
        transactions.append({
            "id": _construire_id(entry),
            "date": entry["date"],
            "payee": entry["payee"],
            "narration": entry["narration"],
            "montant": formater_montant(entry["montant"]),
            "confiance": entry["confiance"],
            "source": entry["source"],
            "compte_propose": entry.get("compte_propose", ""),
        })

    return {
        "nb_pending": len(transactions),
        "transactions": transactions,
    }


@mcp.tool()
def approuver_lot(
    ids: list[str],
    confirmer_gros_montants: bool = False,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Approuver un lot de transactions pending et les ecrire au ledger.

    Les transactions de plus de 2 000 $ necessitent une confirmation explicite
    via confirmer_gros_montants=True. Apres approbation, le ledger est recharge.

    Args:
        ids: Liste d'identifiants composites (format: "date|payee|narration[:20]").
        confirmer_gros_montants: Confirmer l'approbation des transactions > 2 000 $.
    """
    app = ctx.request_context.lifespan_context

    if app.read_only:
        return {"status": "erreur", "message": MSG_LECTURE_SEULE}

    from compteqc.mcp.services import trouver_pending_par_id

    chemin_p = _chemin_pending(app)
    chemin_m = _chemin_main(app)

    # Resoudre les IDs en indices
    pending_list = lister_pending(app.entries)
    indices = []
    ids_introuvables = []
    gros_montants = []

    for id_str in ids:
        idx = trouver_pending_par_id(pending_list, id_str)
        if idx is None:
            ids_introuvables.append(id_str)
        else:
            indices.append(idx)
            # Verifier le montant
            entry = pending_list[idx]
            if entry["montant"] > SEUIL_CONFIRMATION_MONTANT and not confirmer_gros_montants:
                gros_montants.append({
                    "id": id_str,
                    "montant": formater_montant(entry["montant"]),
                    "payee": entry["payee"],
                })

    if ids_introuvables:
        return {
            "status": "erreur",
            "message": f"Transactions introuvables: {', '.join(ids_introuvables)}",
        }

    if gros_montants:
        return {
            "status": "confirmation_requise",
            "message": f"{len(gros_montants)} transaction(s) depassent {formater_montant(SEUIL_CONFIRMATION_MONTANT)} $. Confirmation requise.",
            "transactions_gros_montants": gros_montants,
            "action": "Relancez avec confirmer_gros_montants=True",
        }

    # Approuver
    from compteqc.categorisation.pending import approuver_transactions

    nb = approuver_transactions(chemin_p, chemin_m, indices)
    app.reload()

    return {
        "status": "ok",
        "nb_approuve": nb,
        "message": f"{nb} transaction(s) approuvee(s) et ecrite(s) au ledger.",
    }


@mcp.tool()
def rejeter(
    id: str,
    compte_corrige: str | None = None,
    raison: str | None = None,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Rejeter une transaction pending (avec correction optionnelle).

    Si compte_corrige est fourni, la transaction est mise a jour avec le
    nouveau compte (source="human", confiance=1.0) avant rejet.

    Args:
        id: Identifiant composite de la transaction (format: "date|payee|narration[:20]").
        compte_corrige: Nouveau compte comptable a attribuer (optionnel).
        raison: Raison du rejet en texte libre (optionnel).
    """
    app = ctx.request_context.lifespan_context

    if app.read_only:
        return {"status": "erreur", "message": MSG_LECTURE_SEULE}

    from compteqc.mcp.services import trouver_pending_par_id

    chemin_p = _chemin_pending(app)

    pending_list = lister_pending(app.entries)
    idx = trouver_pending_par_id(pending_list, id)

    if idx is None:
        return {
            "status": "erreur",
            "message": f"Transaction introuvable: {id}",
        }

    # Si correction de compte, mettre a jour la transaction pending avant rejet
    if compte_corrige:
        _corriger_pending(chemin_p, idx, compte_corrige)

    from compteqc.categorisation.pending import rejeter_transactions

    nb = rejeter_transactions(chemin_p, [idx])
    app.reload()

    msg = f"Transaction rejetee."
    if compte_corrige:
        msg = f"Transaction corrigee ({compte_corrige}) et rejetee."
    if raison:
        msg += f" Raison: {raison}"

    return {
        "status": "ok",
        "message": msg,
    }


def _corriger_pending(chemin_pending: Path, idx: int, nouveau_compte: str) -> None:
    """Corrige le compte d'une transaction pending avant rejet.

    Met a jour le fichier pending.beancount en remplacant le compte
    du posting de depenses et en mettant source=human, confiance=1.0.
    """
    import copy

    from beancount.core import data
    from beancount.parser import printer

    from compteqc.categorisation.pending import _ENTETE_PENDING, lire_pending

    pending = lire_pending(chemin_pending)
    if idx >= len(pending):
        return

    txn = pending[idx]

    # Mettre a jour les metadata
    meta = copy.copy(txn.meta)
    meta["source_ia"] = "human"
    meta["confiance"] = "1.0"
    meta["compte_propose"] = nouveau_compte

    # Remplacer le compte dans les postings de depenses
    nouveaux_postings = []
    for posting in txn.postings:
        if posting.account.startswith("Depenses:"):
            nouveau = data.Posting(
                account=nouveau_compte,
                units=posting.units,
                cost=posting.cost,
                price=posting.price,
                flag=posting.flag,
                meta=posting.meta,
            )
            nouveaux_postings.append(nouveau)
        else:
            nouveaux_postings.append(posting)

    txn_corrigee = data.Transaction(
        meta=meta,
        date=txn.date,
        flag=txn.flag,
        payee=txn.payee,
        narration=txn.narration,
        tags=txn.tags,
        links=txn.links,
        postings=nouveaux_postings,
    )

    pending[idx] = txn_corrigee

    # Reecrire le fichier
    contenu = _ENTETE_PENDING
    if pending:
        contenu += "\n" + "\n".join(printer.format_entry(t) for t in pending)
    chemin_pending.write_text(contenu, encoding="utf-8")
