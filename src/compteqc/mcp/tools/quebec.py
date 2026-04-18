"""Outils MCP specifiques au Quebec (TPS/TVQ, DPA, pret actionnaire).

Delegue aux modules existants de compteqc.quebec.* pour les calculs.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from compteqc.documents.registre import RegistreDocumentsFiscaux
from compteqc.mcp.server import AppContext, mcp
from compteqc.mcp.services import formater_montant


@mcp.tool()
def sommaire_tps_tvq(
    periode: str | None = None,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Afficher le sommaire TPS/TVQ pour une periode de declaration.

    Montre la TPS et TVQ percues (sur revenus), payees (CTI/RTI),
    et le montant net a remettre. Par defaut utilise l'annee courante.

    Args:
        periode: Annee (ex: "2026") ou "2026-Q1" a "2026-Q4" pour trimestriel.
    """
    from compteqc.quebec.taxes import (
        auditer_revenus_taxes,
        generer_sommaires_annuels,
        trimestre_dates,
    )

    app = ctx.request_context.lifespan_context
    try:
        registre = RegistreDocumentsFiscaux(
            Path(app.ledger_path).parent / "documents" / "registre.yaml"
        )
        documents_revenus = registre.lister_revenus()
    except Exception:
        documents_revenus = []

    if periode and "-Q" in periode:
        # Format trimestriel: "2026-Q1"
        annee = int(periode.split("-Q")[0])
        trimestre = int(periode.split("-Q")[1])
        sommaires = generer_sommaires_annuels(app.entries, annee, frequence="trimestriel")
        if 1 <= trimestre <= len(sommaires):
            s = sommaires[trimestre - 1]
        else:
            return {"erreur": f"Trimestre invalide: Q{trimestre}"}
        debut, fin = trimestre_dates(annee, trimestre)
        audit = auditer_revenus_taxes(app.entries, documents_revenus, debut=debut, fin=fin)
        resultats = [_formater_sommaire(s, audit_count=audit.count)]
    elif periode:
        annee = int(periode)
        sommaires = generer_sommaires_annuels(app.entries, annee, frequence="annuel")
        audit = auditer_revenus_taxes(
            app.entries,
            documents_revenus,
            debut=datetime.date(annee, 1, 1),
            fin=datetime.date(annee, 12, 31),
        )
        resultats = [_formater_sommaire(s, audit_count=audit.count) for s in sommaires]
    else:
        annee = datetime.date.today().year
        sommaires = generer_sommaires_annuels(app.entries, annee, frequence="annuel")
        audit = auditer_revenus_taxes(
            app.entries,
            documents_revenus,
            debut=datetime.date(annee, 1, 1),
            fin=datetime.date(annee, 12, 31),
        )
        resultats = [_formater_sommaire(s, audit_count=audit.count) for s in sommaires]

    if len(resultats) == 1:
        return resultats[0]
    return {"periodes": resultats}


def _formater_sommaire(s, audit_count: int = 0) -> dict:
    """Formatte un SommairePeriode en dict pour la reponse MCP."""
    resultat = {
        "periode": f"{s.debut} a {s.fin}",
        "tps_percue": formater_montant(s.tps_percue),
        "tvq_percue": formater_montant(s.tvq_percue),
        "tps_payee": formater_montant(s.tps_payee),
        "tvq_payee": formater_montant(s.tvq_payee),
        "remise_nette_tps": formater_montant(s.tps_nette),
        "remise_nette_tvq": formater_montant(s.tvq_nette),
        "nb_transactions": s.nb_transactions,
    }
    if audit_count:
        resultat["anomalies_revenus_count"] = audit_count
        resultat["avertissement"] = (
            f"{audit_count} revenu(x) ou document(s) de revenu restent a revoir; "
            "les montants sont bases uniquement sur les ecritures explicites du ledger."
        )
    return resultat


@mcp.tool()
def etat_dpa(
    annee: int | None = None,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Afficher le tableau de deduction pour amortissement (CCA) par classe.

    Montre la FNACC d'ouverture, acquisitions, dispositions, DPA de l'annee
    et FNACC de fermeture pour les classes 8, 10, 12, 50, 54.

    Args:
        annee: Annee fiscale (defaut: annee courante).
    """
    from compteqc.quebec.dpa import RegistreActifs, construire_pools

    app = ctx.request_context.lifespan_context
    annee_calc = annee or datetime.date.today().year

    # Charger le registre d'actifs depuis le fichier YAML standard
    import os

    registre_path = os.path.join(
        os.path.dirname(app.ledger_path), "actifs.yaml"
    )
    if os.path.exists(registre_path):
        registre = RegistreActifs.charger(registre_path)
        actifs = registre.actifs
    else:
        actifs = []

    # UCC precedent = pool de l'annee precedente (simplifie: on part de zero)
    # En production, on lirait d'un fichier de report ou calculerait recursivement
    ucc_precedent: dict[int, object] = {}
    pools = construire_pools(actifs, ucc_precedent, annee_calc)

    classes = []
    for classe_id in sorted(pools.keys()):
        pool = pools[classe_id]
        classes.append({
            "classe": pool.classe,
            "fnacc_debut": formater_montant(pool.ucc_ouverture),
            "acquisitions": formater_montant(pool.acquisitions),
            "dispositions": formater_montant(pool.dispositions),
            "dpa_annee": formater_montant(pool.calculer_dpa()),
            "fnacc_fin": formater_montant(pool.ucc_fermeture),
        })

    return {
        "annee": annee_calc,
        "classes": classes,
    }


@mcp.tool()
def etat_pret_actionnaire(
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Afficher l'etat du pret actionnaire et les alertes s.15(2).

    Montre le solde net, la direction (corp doit a l'actionnaire ou vice versa),
    les avances ouvertes avec date d'inclusion s.15(2), et le compte a rebours
    en jours. Les alertes graduees (11 mois, 9 mois, 30 jours, depasse) sont
    incluses pour chaque avance ouverte.
    """
    from compteqc.quebec.pret_actionnaire import obtenir_alertes_actives, obtenir_etat_pret

    app = ctx.request_context.lifespan_context
    today = datetime.date.today()
    fin_exercice = datetime.date(today.year, 12, 31)

    etat = obtenir_etat_pret(app.entries, fin_exercice)

    # Direction du solde
    if etat.solde > 0:
        direction = "actionnaire_doit"
    elif etat.solde < 0:
        direction = "corp_doit"
    else:
        direction = "equilibre"

    # Alertes s.15(2) pour les avances ouvertes
    alertes = obtenir_alertes_actives(etat.avances_ouvertes, fin_exercice, today)

    avances_fmt = []
    for avance in etat.avances_ouvertes:
        # Calculer jours restants avant inclusion
        from compteqc.quebec.pret_actionnaire.alertes import calculer_dates_alerte

        alerte = calculer_dates_alerte(
            avance["date"], avance["montant_initial"], fin_exercice, avance["solde_restant"]
        )
        jours_restants = (alerte.date_inclusion - today).days

        avances_fmt.append({
            "date": str(avance["date"]),
            "montant_initial": formater_montant(avance["montant_initial"]),
            "solde_restant": formater_montant(avance["solde_restant"]),
            "date_inclusion_s152": str(alerte.date_inclusion),
            "jours_restants": jours_restants,
        })

    # Niveau d'alerte global
    if any(a["urgence"] == "depasse" for a in alertes):
        alerte_niveau = "depasse"
    elif any(a["urgence"] == "30_jours" for a in alertes):
        alerte_niveau = "30_jours"
    elif any(a["urgence"] == "9_mois" for a in alertes):
        alerte_niveau = "9_mois"
    elif any(a["urgence"] == "11_mois" for a in alertes):
        alerte_niveau = "11_mois"
    else:
        alerte_niveau = "aucune"

    return {
        "solde_net": formater_montant(abs(etat.solde)),
        "direction": direction,
        "avances": avances_fmt,
        "alerte": alerte_niveau,
    }
