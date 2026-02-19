"""Outils MCP de paie: calcul a sec (dry-run) et ecriture au ledger.

Expose calculer_paie_tool (lecture seule) et lancer_paie (mutation)
avec garde-fou unifie sur montant et changement de salaire.
"""

from __future__ import annotations

import datetime
import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path

from beancount.parser import printer

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from compteqc.mcp.server import AppContext, mcp
from compteqc.mcp.services import formater_montant

logger = logging.getLogger(__name__)

SEUIL_GROS_MONTANT = Decimal("2000")

MSG_LECTURE_SEULE = "Mode lecture seule actif. Les modifications du ledger sont desactivees."


def _resultat_vers_dict(resultat) -> dict:
    """Convertit un ResultatPaie en dict structure pour la reponse MCP."""
    retenues = [
        {"nom": "QPP base", "montant": formater_montant(resultat.qpp_base)},
        {"nom": "QPP supp1", "montant": formater_montant(resultat.qpp_supp1)},
        {"nom": "QPP supp2", "montant": formater_montant(resultat.qpp_supp2)},
        {"nom": "RQAP", "montant": formater_montant(resultat.rqap)},
        {"nom": "AE", "montant": formater_montant(resultat.ae)},
        {"nom": "Impot federal", "montant": formater_montant(resultat.impot_federal)},
        {"nom": "Impot Quebec", "montant": formater_montant(resultat.impot_quebec)},
    ]

    cotisations = [
        {"nom": "QPP base employeur", "montant": formater_montant(resultat.qpp_base_employeur)},
        {"nom": "QPP supp1 employeur", "montant": formater_montant(resultat.qpp_supp1_employeur)},
        {"nom": "QPP supp2 employeur", "montant": formater_montant(resultat.qpp_supp2_employeur)},
        {"nom": "RQAP employeur", "montant": formater_montant(resultat.rqap_employeur)},
        {"nom": "AE employeur", "montant": formater_montant(resultat.ae_employeur)},
        {"nom": "FSS", "montant": formater_montant(resultat.fss)},
        {"nom": "CNESST", "montant": formater_montant(resultat.cnesst)},
        {"nom": "Normes travail", "montant": formater_montant(resultat.normes_travail)},
    ]

    return {
        "salaire_brut": formater_montant(resultat.brut),
        "retenues_employe": retenues,
        "cotisations_employeur": cotisations,
        "salaire_net": formater_montant(resultat.net),
        "total_retenues": formater_montant(resultat.total_retenues),
        "cout_total_employeur": formater_montant(resultat.brut + resultat.total_cotisations_employeur),
    }


def _trouver_dernier_brut(entries: list) -> Decimal | None:
    """Trouve le salaire brut de la derniere paie dans le ledger."""
    from beancount.core import data

    dernier = None
    for entry in entries:
        if isinstance(entry, data.Transaction) and entry.tags and "paie" in entry.tags:
            if entry.meta and "brut" in entry.meta:
                try:
                    dernier = Decimal(str(entry.meta["brut"]))
                except Exception:
                    pass
    return dernier


def _determiner_raison_confirmation(
    brut: Decimal, dernier_brut: Decimal | None,
) -> str | None:
    """Determine la raison de confirmation requise (ou None si aucune)."""
    nouveau = dernier_brut is not None and brut != dernier_brut
    gros = brut > SEUIL_GROS_MONTANT

    if nouveau and gros:
        return "nouveau_et_gros_montant"
    elif nouveau:
        return "nouveau_montant"
    elif gros:
        return "gros_montant"
    return None


def _message_confirmation(raison: str, brut: Decimal, dernier_brut: Decimal | None) -> str:
    """Genere un message francais expliquant pourquoi la confirmation est requise."""
    brut_fmt = formater_montant(brut)
    if raison == "nouveau_et_gros_montant":
        ancien = formater_montant(dernier_brut) if dernier_brut else "N/A"
        return (
            f"Le salaire brut ({brut_fmt} $) differe du precedent ({ancien} $) "
            f"ET depasse {formater_montant(SEUIL_GROS_MONTANT)} $. "
            f"Relancez avec confirmer=True pour confirmer."
        )
    elif raison == "nouveau_montant":
        ancien = formater_montant(dernier_brut) if dernier_brut else "N/A"
        return (
            f"Le salaire brut ({brut_fmt} $) differe du precedent ({ancien} $). "
            f"Relancez avec confirmer=True pour confirmer."
        )
    elif raison == "gros_montant":
        return (
            f"Le salaire brut ({brut_fmt} $) depasse {formater_montant(SEUIL_GROS_MONTANT)} $. "
            f"Relancez avec confirmer=True pour confirmer."
        )
    return ""


@mcp.tool()
def calculer_paie_tool(
    salaire_brut: str,
    nb_periodes: int = 26,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Calculer une paie a sec (dry-run) sans ecrire au ledger.

    Montre le detail des retenues employe, cotisations employeur,
    salaire net et cout total. Aucune modification du ledger.

    Args:
        salaire_brut: Salaire brut en CAD (ex: "4230.77").
        nb_periodes: Nombre de periodes par annee (defaut: 26 bi-hebdo).
    """
    try:
        brut = Decimal(salaire_brut)
    except (InvalidOperation, ValueError):
        return {"erreur": f"Montant invalide: {salaire_brut}"}

    app = ctx.request_context.lifespan_context

    from compteqc.quebec.paie.moteur import calculer_paie

    # Determiner le numero de periode courant
    from beancount.core import data
    nb_paies = sum(
        1 for e in app.entries
        if isinstance(e, data.Transaction) and e.tags and "paie" in e.tags
    )
    numero_periode = nb_paies + 1

    try:
        resultat = calculer_paie(
            brut=brut,
            numero_periode=numero_periode,
            chemin_ledger=app.ledger_path,
            nb_periodes=nb_periodes,
        )
    except Exception as e:
        return {"erreur": f"Erreur de calcul: {e}"}

    return _resultat_vers_dict(resultat)


@mcp.tool()
def lancer_paie(
    salaire_brut: str,
    nb_periodes: int = 26,
    offset_pret: str | None = None,
    confirmer: bool = False,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Calculer ET ecrire une paie au ledger.

    Necessite confirmation si le montant differe de la derniere paie
    ou depasse 2 000 $. Le champ raison precise le motif de confirmation.

    Args:
        salaire_brut: Salaire brut en CAD (ex: "4230.77").
        nb_periodes: Nombre de periodes par annee (defaut: 26 bi-hebdo).
        offset_pret: Montant a appliquer contre le pret actionnaire (optionnel).
        confirmer: Confirmer le lancement malgre les gardes-fous.
    """
    app = ctx.request_context.lifespan_context

    if app.read_only:
        return {"status": "erreur", "message": MSG_LECTURE_SEULE}

    try:
        brut = Decimal(salaire_brut)
    except (InvalidOperation, ValueError):
        return {"erreur": f"Montant invalide: {salaire_brut}"}

    offset = None
    if offset_pret:
        try:
            offset = Decimal(offset_pret)
        except (InvalidOperation, ValueError):
            return {"erreur": f"Offset invalide: {offset_pret}"}

    # Garde-fou unifie
    dernier_brut = _trouver_dernier_brut(app.entries)
    raison = _determiner_raison_confirmation(brut, dernier_brut)

    if raison and not confirmer:
        # Calcul dry-run pour information
        from compteqc.quebec.paie.moteur import calculer_paie as calc_paie
        from beancount.core import data

        nb_paies = sum(
            1 for e in app.entries
            if isinstance(e, data.Transaction) and e.tags and "paie" in e.tags
        )
        try:
            resultat = calc_paie(
                brut=brut,
                numero_periode=nb_paies + 1,
                chemin_ledger=app.ledger_path,
                nb_periodes=nb_periodes,
            )
            calcul = _resultat_vers_dict(resultat)
        except Exception:
            calcul = None

        return {
            "status": "confirmation_requise",
            "raison": raison,
            "message": _message_confirmation(raison, brut, dernier_brut),
            "calcul": calcul,
        }

    # Executer la paie
    from beancount.core import data
    from compteqc.quebec.paie.moteur import calculer_paie as calc_paie
    from compteqc.quebec.paie.journal import generer_transaction_paie
    from compteqc.ledger.fichiers import ecrire_transactions, chemin_fichier_mensuel, ajouter_include

    nb_paies = sum(
        1 for e in app.entries
        if isinstance(e, data.Transaction) and e.tags and "paie" in e.tags
    )
    numero_periode = nb_paies + 1

    resultat = calc_paie(
        brut=brut,
        numero_periode=numero_periode,
        chemin_ledger=app.ledger_path,
        nb_periodes=nb_periodes,
    )

    date_paie = datetime.date.today()
    txn = generer_transaction_paie(date_paie, resultat, salary_offset=offset)

    # Ecrire dans le fichier mensuel
    ledger_dir = Path(app.ledger_path).parent
    fichier_mensuel = chemin_fichier_mensuel(date_paie.year, date_paie.month, ledger_dir)
    texte = printer.format_entry(txn)
    ecrire_transactions(fichier_mensuel, texte)

    # Assurer l'include dans main.beancount
    chemin_main = Path(app.ledger_path)
    chemin_relatif = str(fichier_mensuel.relative_to(ledger_dir))
    ajouter_include(chemin_main, chemin_relatif)

    app.reload()

    return {
        "status": "ok",
        "message": f"Paie #{numero_periode} ecrite au ledger ({formater_montant(brut)} $ brut).",
        "transaction_id": f"paie-{date_paie.isoformat()}-{numero_periode}",
        "details": _resultat_vers_dict(resultat),
    }
