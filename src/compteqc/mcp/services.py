"""Couche de services partagee entre MCP et Fava.

Abstrait les operations de lecture du ledger Beancount pour eviter
de dupliquer la logique entre les outils MCP et les extensions Fava.
"""

from __future__ import annotations

from decimal import Decimal

from beancount import loader
from beancount.core import data


def charger_ledger(chemin: str) -> tuple[list, list, dict]:
    """Charge un fichier Beancount et retourne (entries, errors, options)."""
    return loader.load_file(chemin)


def calculer_soldes(entries: list, filtre: str | None = None) -> dict[str, Decimal]:
    """Calcule les soldes de chaque compte a partir des transactions.

    Args:
        entries: Liste d'entrees Beancount.
        filtre: Sous-chaine optionnelle pour filtrer les comptes.

    Returns:
        Dictionnaire {nom_compte: solde_CAD}.
    """
    soldes: dict[str, Decimal] = {}
    for entry in entries:
        if isinstance(entry, data.Transaction):
            for posting in entry.postings:
                if posting.units:
                    acct = posting.account
                    soldes[acct] = soldes.get(acct, Decimal("0")) + posting.units.number

    if filtre:
        filtre_upper = filtre.upper()
        soldes = {k: v for k, v in soldes.items() if filtre_upper in k.upper()}

    return soldes


def lister_pending(entries: list) -> list[dict]:
    """Liste toutes les transactions #pending avec leurs metadonnees AI.

    Args:
        entries: Liste d'entrees Beancount.

    Returns:
        Liste de dicts avec date, payee, narration, confiance, source, montant.
    """
    pending = []
    for entry in entries:
        if isinstance(entry, data.Transaction) and entry.tags and "pending" in entry.tags:
            # Montant = somme des postings positifs (debit side)
            montant = Decimal("0")
            for p in entry.postings:
                if p.units and p.units.number > 0:
                    montant += p.units.number

            # Meta keys: pending.py uses 'confiance'/'source_ia'/'compte_propose',
            # while some paths use 'confidence'/'ai-source'. Support both.
            meta = entry.meta or {}
            confiance = meta.get("confiance", meta.get("confidence", "unknown"))
            source = meta.get("source_ia", meta.get("ai-source", "unknown"))
            compte_propose = meta.get("compte_propose", "")

            pending.append({
                "date": str(entry.date),
                "payee": entry.payee or "",
                "narration": entry.narration or "",
                "confiance": confiance,
                "source": source,
                "compte_propose": compte_propose,
                "montant": montant,
            })
    return pending


def formater_montant(montant: Decimal) -> str:
    """Formate un montant en CAD avec 2 decimales et separateur de milliers."""
    return f"{montant:,.2f}"


def trouver_pending_par_id(pending_list: list[dict], id_str: str) -> int | None:
    """Trouve l'index d'une transaction pending par identifiant composite.

    L'identifiant composite est de la forme "date|payee|narration[:20]".

    Args:
        pending_list: Liste de dicts retournee par lister_pending().
        id_str: Identifiant composite a rechercher.

    Returns:
        Index 0-based de la transaction, ou None si introuvable.
    """
    for i, entry in enumerate(pending_list):
        narration = (entry.get("narration") or "")[:20]
        cle = f"{entry['date']}|{entry['payee']}|{narration}"
        if cle == id_str:
            return i
    return None
