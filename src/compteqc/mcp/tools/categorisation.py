"""Outil MCP de categorisation avec raisonnement en francais.

Expose proposer_categorie qui utilise le PipelineCategorisation pour suggerer
un compte avec confiance, source et raisonnement. Auto-approuve les
transactions a haute confiance / faible montant.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from compteqc.mcp.server import AppContext, mcp

logger = logging.getLogger(__name__)


def _construire_raison(source: str, compte: str, confiance: float, regle: str | None) -> str:
    """Construit une explication en francais du raisonnement de categorisation."""
    pct = int(confiance * 100)
    if source == "regle":
        nom_regle = regle or "inconnue"
        return f"Regle '{nom_regle}' correspond au beneficiaire/narration"
    elif source == "ml":
        return f"Modele ML predit {compte} (confiance {pct}%) base sur transactions historiques similaires"
    elif source == "llm":
        return f"Classification LLM: {compte} ({pct}%)"
    else:
        return "Aucun classificateur n'a pu determiner la categorie"


@mcp.tool()
def proposer_categorie(
    payee: str,
    narration: str,
    montant: str,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Proposer une categorie pour une transaction en utilisant le pipeline IA.

    Analyse le beneficiaire et la narration pour suggerer le meilleur compte
    comptable. Retourne la confiance, la source (regle/ML/LLM) et une
    explication en francais du raisonnement.

    Les transactions a haute confiance (>=95%), non-CAPEX, et <=2000$ sont
    auto-approuvees et contournent la file d'attente.

    Args:
        payee: Nom du beneficiaire (ex: "Amazon", "Bell Canada").
        narration: Description de la transaction.
        montant: Montant en CAD (ex: "150.00").
    """
    try:
        montant_decimal = Decimal(montant)
    except (InvalidOperation, ValueError):
        return {"erreur": f"Montant invalide: {montant}"}

    # Tenter d'initialiser le pipeline avec les composants disponibles
    try:
        from compteqc.categorisation.capex import DetecteurCAPEX
        from compteqc.categorisation.moteur import MoteurRegles
        from compteqc.categorisation.pipeline import PipelineCategorisation
        from compteqc.categorisation.regles import ConfigRegles

        app = ctx.request_context.lifespan_context

        # Charger les regles depuis le repertoire du ledger
        import os
        regles_path = os.path.join(os.path.dirname(app.ledger_path), "regles.yaml")

        if os.path.exists(regles_path):
            config = ConfigRegles.charger(regles_path)
        else:
            config = ConfigRegles(regles=[], comptes_valides=set())

        moteur = MoteurRegles(config)
        detecteur = DetecteurCAPEX()

        # ML et LLM: optionnels, ne pas echouer si indisponibles
        predicteur_ml = None
        classificateur_llm = None

        pipeline = PipelineCategorisation(
            moteur_regles=moteur,
            predicteur_ml=predicteur_ml,
            classificateur_llm=classificateur_llm,
            detecteur_capex=detecteur,
        )

        resultat = pipeline.categoriser(payee, narration, montant_decimal)

    except Exception as e:
        logger.warning("Erreur pipeline de categorisation: %s", e, exc_info=True)
        return {
            "compte_propose": "Depenses:Non-Classe",
            "confiance": 0.0,
            "source": "non-classe",
            "raison": f"Erreur lors de la categorisation: {e}",
            "est_capex": False,
            "classe_dpa": None,
            "revue_obligatoire": True,
            "auto_approuve": False,
        }

    raison = _construire_raison(resultat.source, resultat.compte, resultat.confiance, resultat.regle)

    # Auto-approve: confiance >= 0.95, pas de revue obligatoire, montant <= 2000
    seuil_auto = Decimal("2000")
    auto_approuve = (
        resultat.confiance >= 0.95
        and not resultat.revue_obligatoire
        and abs(montant_decimal) <= seuil_auto
    )

    if auto_approuve:
        # Transaction auto-approuvee -- pas besoin de passer par pending
        logger.info(
            "Auto-approbation: %s %s -> %s (confiance=%.2f)",
            payee, montant, resultat.compte, resultat.confiance,
        )

    return {
        "compte_propose": resultat.compte,
        "confiance": resultat.confiance,
        "source": resultat.source,
        "raison": raison,
        "est_capex": resultat.est_capex,
        "classe_dpa": resultat.classe_dpa,
        "revue_obligatoire": resultat.revue_obligatoire,
        "auto_approuve": auto_approuve,
    }
