"""Outils MCP de consultation du grand-livre (soldes, balance, resultats, bilan).

Chaque outil est enregistre via @mcp.tool() et accede au ledger en memoire
via le contexte lifespan (AppContext).
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from compteqc.mcp.server import AppContext, mcp
from compteqc.mcp.services import calculer_soldes, formater_montant

MAX_ITEMS = 50


@mcp.tool()
def soldes_comptes(
    filtre: str | None = None,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Afficher les soldes de tous les comptes du ledger.

    Filtre optionnel par sous-chaine sur le nom du compte
    (ex: "Depenses", "Actifs:Banque"). Les comptes a solde zero sont exclus.
    Limite a 50 resultats; le champ tronque indique si la liste est incomplete.

    Args:
        filtre: Sous-chaine pour filtrer les comptes (insensible a la casse).
    """
    app = ctx.request_context.lifespan_context
    soldes = calculer_soldes(app.entries, filtre=filtre)

    comptes = [
        {"compte": k, "solde": formater_montant(v)}
        for k, v in sorted(soldes.items())
        if v != Decimal("0")
    ]
    return {
        "nb_comptes": len(comptes),
        "comptes": comptes[:MAX_ITEMS],
        "tronque": len(comptes) > MAX_ITEMS,
    }


@mcp.tool()
def balance_verification(
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Afficher la balance de verification (trial balance).

    Montre les debits et credits par compte, groupes par categorie
    (Actifs, Passifs, Capital, Revenus, Depenses).
    Verifie que total debits = total credits.
    """
    app = ctx.request_context.lifespan_context
    soldes = calculer_soldes(app.entries)

    categories = ["Actifs", "Passifs", "Capital", "Revenus", "Depenses"]
    comptes = []
    total_debits = Decimal("0")
    total_credits = Decimal("0")

    for categorie in categories:
        comptes_cat = {
            k: v for k, v in sorted(soldes.items())
            if k.startswith(categorie) and v != Decimal("0")
        }
        for nom, montant in comptes_cat.items():
            if montant > 0:
                comptes.append({"compte": nom, "debit": formater_montant(montant), "credit": ""})
                total_debits += montant
            else:
                comptes.append({"compte": nom, "debit": "", "credit": formater_montant(abs(montant))})
                total_credits += abs(montant)

    return {
        "comptes": comptes[:MAX_ITEMS],
        "tronque": len(comptes) > MAX_ITEMS,
        "total_debits": formater_montant(total_debits),
        "total_credits": formater_montant(total_credits),
        "equilibre": total_debits == total_credits,
    }


@mcp.tool()
def etat_resultats(
    date_debut: str | None = None,
    date_fin: str | None = None,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Afficher l'etat des resultats (revenus et depenses) pour une periode.

    Sans filtres de dates, affiche toutes les transactions.
    Les revenus sont affiches en valeur absolue (positif = revenu gagne).

    Args:
        date_debut: Date de debut inclusive (format AAAA-MM-JJ).
        date_fin: Date de fin inclusive (format AAAA-MM-JJ).
    """
    from beancount.core import data

    app = ctx.request_context.lifespan_context
    d_debut = datetime.date.fromisoformat(date_debut) if date_debut else None
    d_fin = datetime.date.fromisoformat(date_fin) if date_fin else None

    revenus: dict[str, Decimal] = {}
    depenses: dict[str, Decimal] = {}

    for entry in app.entries:
        if not isinstance(entry, data.Transaction):
            continue
        if d_debut and entry.date < d_debut:
            continue
        if d_fin and entry.date > d_fin:
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

    # Revenus sont negatifs en beancount (credits) -> afficher en positif
    liste_revenus = [
        {"compte": k, "montant": formater_montant(-v)}
        for k, v in sorted(revenus.items())
    ]
    total_revenus = sum(-v for v in revenus.values())

    liste_depenses = [
        {"compte": k, "montant": formater_montant(v)}
        for k, v in sorted(depenses.items())
    ]
    total_depenses = sum(depenses.values())

    resultat_net = total_revenus - total_depenses

    return {
        "revenus": liste_revenus[:MAX_ITEMS],
        "depenses": liste_depenses[:MAX_ITEMS],
        "total_revenus": formater_montant(total_revenus),
        "total_depenses": formater_montant(total_depenses),
        "resultat_net": formater_montant(resultat_net),
        "tronque": len(liste_revenus) > MAX_ITEMS or len(liste_depenses) > MAX_ITEMS,
    }


@mcp.tool()
def bilan(
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Afficher le bilan (actifs, passifs, capitaux propres).

    Verifie l'equation comptable: Actifs = Passifs + Capitaux propres.
    Le resultat net est inclus dans les capitaux propres.
    """
    app = ctx.request_context.lifespan_context
    soldes = calculer_soldes(app.entries)

    actifs: dict[str, Decimal] = {}
    passifs: dict[str, Decimal] = {}
    capitaux: dict[str, Decimal] = {}

    for acct, montant in soldes.items():
        if montant == Decimal("0"):
            continue
        if acct.startswith("Actifs"):
            actifs[acct] = montant
        elif acct.startswith("Passifs"):
            passifs[acct] = montant
        elif acct.startswith("Capital"):
            capitaux[acct] = montant

    # Resultat net = Revenus (inverses) - Depenses
    resultat_net = Decimal("0")
    for acct, montant in soldes.items():
        if acct.startswith("Revenus"):
            resultat_net -= montant  # credits sont negatifs -> -(-x) = +x
        elif acct.startswith("Depenses"):
            resultat_net -= montant  # debits sont positifs -> -(+x) = -x

    total_actifs = sum(actifs.values())
    total_passifs = sum(abs(v) for v in passifs.values())
    total_capitaux = sum(abs(v) for v in capitaux.values()) + resultat_net
    total_passifs_capitaux = total_passifs + total_capitaux

    return {
        "actifs": [
            {"compte": k, "montant": formater_montant(v)}
            for k, v in sorted(actifs.items())
        ][:MAX_ITEMS],
        "passifs": [
            {"compte": k, "montant": formater_montant(abs(v))}
            for k, v in sorted(passifs.items())
        ][:MAX_ITEMS],
        "capitaux_propres": [
            {"compte": k, "montant": formater_montant(abs(v))}
            for k, v in sorted(capitaux.items())
        ] + ([{"compte": "Resultat net de l'exercice", "montant": formater_montant(resultat_net)}] if resultat_net != 0 else []),
        "total_actifs": formater_montant(total_actifs),
        "total_passifs": formater_montant(total_passifs),
        "total_capitaux_propres": formater_montant(total_capitaux),
        "equilibre": total_actifs == total_passifs_capitaux,
        "tronque": (
            len(actifs) > MAX_ITEMS
            or len(passifs) > MAX_ITEMS
            or len(capitaux) > MAX_ITEMS
        ),
    }
