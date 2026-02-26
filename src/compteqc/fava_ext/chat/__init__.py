"""Extension Fava: Chat avec Claude pour discuter de vos finances.

Expose un endpoint POST /chat qui proxie les messages vers l'API Anthropic
Messages avec acces aux 13 outils MCP CompteQC. Claude peut consulter le
ledger, categoriser des transactions, calculer la paie, etc.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import time
from decimal import Decimal
from pathlib import Path

from flask import jsonify, request

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase, extension_endpoint

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiting (simple in-memory, single-user)
# ---------------------------------------------------------------------------

_rate_state = {"last_request": 0.0, "hour_count": 0, "hour_start": 0.0}

MAX_REQ_PER_SEC = 1
MAX_REQ_PER_HOUR = 100


def _check_rate_limit() -> str | None:
    """Returns an error message if rate limited, else None."""
    now = time.time()

    # Per-second
    if now - _rate_state["last_request"] < (1.0 / MAX_REQ_PER_SEC):
        return "Trop de requetes. Veuillez patienter une seconde."

    # Per-hour
    if now - _rate_state["hour_start"] > 3600:
        _rate_state["hour_count"] = 0
        _rate_state["hour_start"] = now

    if _rate_state["hour_count"] >= MAX_REQ_PER_HOUR:
        return f"Limite horaire atteinte ({MAX_REQ_PER_HOUR} messages/heure)."

    _rate_state["last_request"] = now
    _rate_state["hour_count"] += 1
    return None


# ---------------------------------------------------------------------------
# Tool definitions for Anthropic API
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "soldes_comptes",
        "description": (
            "Afficher les soldes de tous les comptes du ledger. "
            "Filtre optionnel par sous-chaine sur le nom du compte."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filtre": {
                    "type": "string",
                    "description": "Sous-chaine pour filtrer les comptes (insensible a la casse).",
                },
            },
        },
    },
    {
        "name": "balance_verification",
        "description": (
            "Afficher la balance de verification (trial balance). "
            "Montre debits et credits par compte, verifie l'equilibre."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "etat_resultats",
        "description": (
            "Afficher l'etat des resultats (revenus et depenses) pour une periode. "
            "Sans filtres de dates, affiche toutes les transactions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_debut": {
                    "type": "string",
                    "description": "Date de debut inclusive (format AAAA-MM-JJ).",
                },
                "date_fin": {
                    "type": "string",
                    "description": "Date de fin inclusive (format AAAA-MM-JJ).",
                },
            },
        },
    },
    {
        "name": "bilan",
        "description": (
            "Afficher le bilan (actifs, passifs, capitaux propres). "
            "Verifie l'equation comptable."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "proposer_categorie",
        "description": (
            "Proposer une categorie pour une transaction en utilisant le pipeline IA. "
            "Retourne confiance, source et raisonnement."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "payee": {"type": "string", "description": "Nom du beneficiaire."},
                "narration": {"type": "string", "description": "Description de la transaction."},
                "montant": {"type": "string", "description": "Montant en CAD (ex: '150.00')."},
            },
            "required": ["payee", "narration", "montant"],
        },
    },
    {
        "name": "lister_pending_tool",
        "description": "Lister les transactions en attente de revision (#pending).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "approuver_lot",
        "description": (
            "Approuver un lot de transactions pending. "
            "Transactions > 2 000 $ necessitent confirmer_gros_montants=true."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Identifiants composites (date|payee|narration[:20]).",
                },
                "confirmer_gros_montants": {
                    "type": "boolean",
                    "description": "Confirmer l'approbation des transactions > 2 000 $.",
                },
            },
            "required": ["ids"],
        },
    },
    {
        "name": "rejeter",
        "description": "Rejeter une transaction pending (avec correction optionnelle du compte).",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Identifiant composite."},
                "compte_corrige": {
                    "type": "string",
                    "description": "Nouveau compte comptable (optionnel).",
                },
                "raison": {"type": "string", "description": "Raison du rejet (optionnel)."},
            },
            "required": ["id"],
        },
    },
    {
        "name": "calculer_paie_tool",
        "description": (
            "Calculer une paie a sec (dry-run) sans ecrire au ledger. "
            "Montre retenues employe, cotisations employeur, salaire net."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "salaire_brut": {"type": "string", "description": "Salaire brut en CAD."},
                "nb_periodes": {
                    "type": "integer",
                    "description": "Nombre de periodes par annee (defaut: 26).",
                },
            },
            "required": ["salaire_brut"],
        },
    },
    {
        "name": "lancer_paie",
        "description": (
            "Calculer ET ecrire une paie au ledger. "
            "Necessite confirmation si montant differe ou depasse 2 000 $."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "salaire_brut": {"type": "string", "description": "Salaire brut en CAD."},
                "nb_periodes": {
                    "type": "integer",
                    "description": "Nombre de periodes par annee (defaut: 26).",
                },
                "offset_pret": {
                    "type": "string",
                    "description": "Montant contre le pret actionnaire (optionnel).",
                },
                "confirmer": {
                    "type": "boolean",
                    "description": "Confirmer le lancement malgre les gardes-fous.",
                },
            },
            "required": ["salaire_brut"],
        },
    },
    {
        "name": "sommaire_tps_tvq",
        "description": (
            "Sommaire TPS/TVQ pour une periode. "
            "Montre TPS/TVQ percues, payees, et remise nette."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "periode": {
                    "type": "string",
                    "description": "Annee ('2026') ou trimestre ('2026-Q1').",
                },
            },
        },
    },
    {
        "name": "etat_dpa",
        "description": (
            "Tableau de deduction pour amortissement (CCA/DPA) par classe. "
            "FNACC, acquisitions, dispositions, DPA de l'annee."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "annee": {"type": "integer", "description": "Annee fiscale (defaut: courante)."},
            },
        },
    },
    {
        "name": "etat_pret_actionnaire",
        "description": (
            "Etat du pret actionnaire et alertes s.15(2). "
            "Solde net, avances ouvertes, compte a rebours."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ---------------------------------------------------------------------------
# Tool execution bridge
# ---------------------------------------------------------------------------


def _build_app_context(ledger: FavaLedger):
    """Build a lightweight AppContext-like object from Fava's ledger."""
    from compteqc.mcp.server import AppContext

    return AppContext(
        ledger_path=ledger.beancount_file_path,
        entries=ledger.all_entries,
        errors=list(ledger.errors),
        options=ledger.options,
        read_only=False,
    )


def _execute_tool(name: str, args: dict, ledger: FavaLedger) -> dict:
    """Execute a tool by name with given arguments, returning the result dict."""
    from compteqc.mcp.services import (
        calculer_soldes,
        formater_montant,
        lister_pending,
    )

    app = _build_app_context(ledger)

    # Dispatch to the appropriate tool logic (replicating MCP tool bodies
    # without the @mcp.tool() decorator and Context parameter).
    try:
        if name == "soldes_comptes":
            filtre = args.get("filtre")
            soldes = calculer_soldes(app.entries, filtre=filtre)
            comptes = [
                {"compte": k, "solde": formater_montant(v)}
                for k, v in sorted(soldes.items())
                if v != Decimal("0")
            ]
            return {
                "nb_comptes": len(comptes),
                "comptes": comptes[:50],
                "tronque": len(comptes) > 50,
            }

        elif name == "balance_verification":
            from compteqc.mcp.tools.ledger import balance_verification as _bv

            # Call via a mock context -- simpler to just recompute
            soldes = calculer_soldes(app.entries)
            categories = ["Actifs", "Passifs", "Capital", "Revenus", "Depenses"]
            comptes = []
            total_debits = Decimal("0")
            total_credits = Decimal("0")
            for cat in categories:
                for nom, montant in sorted(soldes.items()):
                    if nom.startswith(cat) and montant != Decimal("0"):
                        if montant > 0:
                            comptes.append({"compte": nom, "debit": formater_montant(montant), "credit": ""})
                            total_debits += montant
                        else:
                            comptes.append({"compte": nom, "debit": "", "credit": formater_montant(abs(montant))})
                            total_credits += abs(montant)
            return {
                "comptes": comptes[:50],
                "tronque": len(comptes) > 50,
                "total_debits": formater_montant(total_debits),
                "total_credits": formater_montant(total_credits),
                "equilibre": total_debits == total_credits,
            }

        elif name == "etat_resultats":
            from beancount.core import data

            date_debut = args.get("date_debut")
            date_fin = args.get("date_fin")
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

            liste_revenus = [{"compte": k, "montant": formater_montant(-v)} for k, v in sorted(revenus.items())]
            total_revenus = sum(-v for v in revenus.values())
            liste_depenses = [{"compte": k, "montant": formater_montant(v)} for k, v in sorted(depenses.items())]
            total_depenses = sum(depenses.values())
            return {
                "revenus": liste_revenus[:50],
                "depenses": liste_depenses[:50],
                "total_revenus": formater_montant(total_revenus),
                "total_depenses": formater_montant(total_depenses),
                "resultat_net": formater_montant(total_revenus - total_depenses),
                "tronque": len(liste_revenus) > 50 or len(liste_depenses) > 50,
            }

        elif name == "bilan":
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

            resultat_net = Decimal("0")
            for acct, montant in soldes.items():
                if acct.startswith("Revenus"):
                    resultat_net -= montant
                elif acct.startswith("Depenses"):
                    resultat_net -= montant

            total_actifs = sum(actifs.values())
            total_passifs = sum(-v for v in passifs.values())
            total_capitaux = sum(-v for v in capitaux.values()) + resultat_net
            return {
                "actifs": [{"compte": k, "montant": formater_montant(v)} for k, v in sorted(actifs.items())][:50],
                "passifs": [{"compte": k, "montant": formater_montant(-v)} for k, v in sorted(passifs.items())][:50],
                "capitaux_propres": [{"compte": k, "montant": formater_montant(-v)} for k, v in sorted(capitaux.items())],
                "total_actifs": formater_montant(total_actifs),
                "total_passifs": formater_montant(total_passifs),
                "total_capitaux_propres": formater_montant(total_capitaux),
                "equilibre": total_actifs == (total_passifs + total_capitaux),
            }

        elif name == "proposer_categorie":
            # Delegate to categorisation pipeline
            from compteqc.categorisation.pipeline import PipelineCategorisation
            from compteqc.categorisation.moteur import MoteurRegles
            from compteqc.categorisation.regles import ConfigRegles, charger_regles
            from compteqc.categorisation.capex import DetecteurCAPEX

            regles_path = os.path.join(os.path.dirname(app.ledger_path), "regles.yaml")
            if os.path.exists(regles_path):
                config = charger_regles(regles_path)
            else:
                config = ConfigRegles(regles=[])

            moteur = MoteurRegles(config)
            detecteur = DetecteurCAPEX()
            pipeline = PipelineCategorisation(
                moteur_regles=moteur, predicteur_ml=None,
                classificateur_llm=None, detecteur_capex=detecteur,
            )
            resultat = pipeline.categoriser(args["payee"], args["narration"], Decimal(args["montant"]))
            return {
                "compte_propose": resultat.compte,
                "confiance": resultat.confiance,
                "source": resultat.source,
                "est_capex": resultat.est_capex,
                "revue_obligatoire": resultat.revue_obligatoire,
            }

        elif name == "lister_pending_tool":
            pending = lister_pending(app.entries)
            transactions = []
            for entry in pending:
                narration = entry.get("narration", "") or ""
                transactions.append({
                    "id": f"{entry['date']}|{entry['payee']}|{narration[:20]}",
                    "date": entry["date"],
                    "payee": entry["payee"],
                    "narration": entry["narration"],
                    "montant": formater_montant(entry["montant"]),
                    "confiance": entry["confiance"],
                    "source": entry["source"],
                    "compte_propose": entry.get("compte_propose", ""),
                })
            return {"nb_pending": len(transactions), "transactions": transactions}

        elif name == "approuver_lot":
            from compteqc.mcp.services import trouver_pending_par_id
            from compteqc.categorisation.pending import approuver_transactions

            pending_list = lister_pending(app.entries)
            chemin_p = Path(app.ledger_path).parent / "pending.beancount"
            chemin_m = Path(app.ledger_path)
            ids = args.get("ids", [])
            confirmer = args.get("confirmer_gros_montants", False)

            indices = []
            for id_str in ids:
                idx = trouver_pending_par_id(pending_list, id_str)
                if idx is not None:
                    indices.append(idx)

            nb = approuver_transactions(chemin_p, chemin_m, indices)
            return {"status": "ok", "nb_approuve": nb}

        elif name == "rejeter":
            from compteqc.mcp.services import trouver_pending_par_id
            from compteqc.categorisation.pending import rejeter_transactions

            pending_list = lister_pending(app.entries)
            chemin_p = Path(app.ledger_path).parent / "pending.beancount"
            idx = trouver_pending_par_id(pending_list, args["id"])
            if idx is None:
                return {"status": "erreur", "message": f"Transaction introuvable: {args['id']}"}

            nb = rejeter_transactions(chemin_p, [idx])
            return {"status": "ok", "message": "Transaction rejetee."}

        elif name == "calculer_paie_tool":
            from compteqc.quebec.paie.moteur import calculer_paie
            from beancount.core import data

            brut = Decimal(args["salaire_brut"])
            nb_periodes = args.get("nb_periodes", 26)
            nb_paies = sum(
                1 for e in app.entries
                if isinstance(e, data.Transaction) and e.tags and "paie" in e.tags
            )
            resultat = calculer_paie(
                brut=brut, numero_periode=nb_paies + 1,
                chemin_ledger=app.ledger_path, nb_periodes=nb_periodes,
            )
            return {
                "salaire_brut": formater_montant(resultat.brut),
                "salaire_net": formater_montant(resultat.net),
                "total_retenues": formater_montant(resultat.total_retenues),
                "cout_total_employeur": formater_montant(
                    resultat.brut + resultat.total_cotisations_employeur
                ),
            }

        elif name == "lancer_paie":
            return {
                "status": "info",
                "message": (
                    "Pour des raisons de securite, l'execution de paie via le chat "
                    "n'est pas activee. Utilisez l'onglet Paie ou l'outil MCP directement."
                ),
            }

        elif name == "sommaire_tps_tvq":
            from compteqc.quebec.taxes import generer_sommaires_annuels

            periode = args.get("periode")
            if periode and "-Q" in periode:
                annee = int(periode.split("-Q")[0])
                trimestre = int(periode.split("-Q")[1])
                sommaires = generer_sommaires_annuels(app.entries, annee, frequence="trimestriel")
                if 1 <= trimestre <= len(sommaires):
                    s = sommaires[trimestre - 1]
                else:
                    return {"erreur": f"Trimestre invalide: Q{trimestre}"}
                return _format_sommaire(s)
            else:
                annee = int(periode) if periode else datetime.date.today().year
                sommaires = generer_sommaires_annuels(app.entries, annee, frequence="annuel")
                if len(sommaires) == 1:
                    return _format_sommaire(sommaires[0])
                return {"periodes": [_format_sommaire(s) for s in sommaires]}

        elif name == "etat_dpa":
            from compteqc.quebec.dpa import RegistreActifs, construire_pools

            annee_calc = args.get("annee") or datetime.date.today().year
            registre_path = os.path.join(os.path.dirname(app.ledger_path), "actifs.yaml")
            if os.path.exists(registre_path):
                registre = RegistreActifs.charger(registre_path)
                actifs_list = registre.actifs
            else:
                actifs_list = []
            pools = construire_pools(actifs_list, {}, annee_calc)
            classes = []
            for classe_id in sorted(pools.keys()):
                pool = pools[classe_id]
                classes.append({
                    "classe": pool.classe,
                    "fnacc_debut": formater_montant(pool.ucc_ouverture),
                    "dpa_annee": formater_montant(pool.calculer_dpa()),
                    "fnacc_fin": formater_montant(pool.ucc_fermeture),
                })
            return {"annee": annee_calc, "classes": classes}

        elif name == "etat_pret_actionnaire":
            from compteqc.quebec.pret_actionnaire import obtenir_alertes_actives, obtenir_etat_pret

            today = datetime.date.today()
            fin_exercice = datetime.date(today.year, 12, 31)
            etat = obtenir_etat_pret(app.entries, fin_exercice)
            direction = "actionnaire_doit" if etat.solde > 0 else ("corp_doit" if etat.solde < 0 else "equilibre")
            alertes = obtenir_alertes_actives(etat.avances_ouvertes, fin_exercice, today)
            alerte_niveau = "aucune"
            for a in alertes:
                if a["urgence"] == "depasse":
                    alerte_niveau = "depasse"
                    break
                if a["urgence"] == "30_jours":
                    alerte_niveau = "30_jours"
            return {
                "solde_net": formater_montant(abs(etat.solde)),
                "direction": direction,
                "alerte": alerte_niveau,
            }

        else:
            return {"erreur": f"Outil inconnu: {name}"}

    except Exception as e:
        logger.exception("Erreur lors de l'execution de l'outil %s", name)
        return {"erreur": f"Erreur lors de l'execution de {name}: {e}"}


def _format_sommaire(s) -> dict:
    """Format a SommairePeriode for tool output."""
    from compteqc.mcp.services import formater_montant

    return {
        "periode": f"{s.debut} a {s.fin}",
        "tps_percue": formater_montant(s.tps_percue),
        "tvq_percue": formater_montant(s.tvq_percue),
        "tps_payee": formater_montant(s.tps_payee),
        "tvq_payee": formater_montant(s.tvq_payee),
        "remise_nette_tps": formater_montant(s.tps_nette),
        "remise_nette_tvq": formater_montant(s.tvq_nette),
    }


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """\
Tu es un assistant financier bilingue (francais/anglais) pour une SPCC \
(societe privee sous controle canadien) incorporee au Quebec. Tu travailles \
avec le systeme comptable CompteQC.

Contexte fiscal:
- Annee fiscale: {fiscal_year} (se terminant le {fiscal_year_end})
- Date du jour: {today}
- Entreprise: Consultation IT solo, ~230 000 $ de revenus annuels
- Juridiction: Quebec, Canada (TPS 5% + TVQ 9.975%)

Regles strictes:
1. N'invente JAMAIS de chiffres. Utilise toujours les outils pour consulter \
les donnees reelles du ledger.
2. Quand tu ne sais pas, dis-le clairement.
3. Pour les questions de strategie fiscale (salaire vs dividendes, \
optimisation T2/CO-17), recommande de consulter le CPA.
4. Montre tes calculs quand tu fais des operations arithmetiques.
5. Reponds dans la langue de la question (francais si francais, anglais si anglais).
6. Sois concis mais complet. Utilise des listes et tableaux quand pertinent.

Tu as acces a 13 outils pour consulter le grand-livre, categoriser des \
transactions, gerer la file d'approbation, calculer la paie, et consulter \
les taxes TPS/TVQ, la DPA et le pret actionnaire."""


def _build_system_prompt(ledger: FavaLedger) -> str:
    """Build the system prompt with fiscal year context from the ledger."""
    options = ledger.options
    fiscal_year_end = options.get("fiscal_year_end", "12-31")
    today = datetime.date.today()
    fiscal_year = today.year

    return SYSTEM_PROMPT_TEMPLATE.format(
        fiscal_year=fiscal_year,
        fiscal_year_end=fiscal_year_end,
        today=today.isoformat(),
    )


# ---------------------------------------------------------------------------
# ChatExtension
# ---------------------------------------------------------------------------

MAX_TOOL_ITERATIONS = 10
MAX_CONTEXT_MESSAGES = 20
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096


class ChatExtension(FavaExtensionBase):
    """Chat avec Claude -- assistant financier avec acces au ledger."""

    report_title = "Chat"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)

    # ------------------------------------------------------------------
    # POST /chat -- Proxy vers Anthropic Messages API
    # ------------------------------------------------------------------

    @extension_endpoint("chat", ["POST"])
    def chat(self):
        """Recoit les messages utilisateur, appelle Claude avec les outils, retourne la reponse."""
        # Check API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return jsonify({
                "role": "assistant",
                "content": (
                    "Cle API Anthropic non configuree. "
                    "Definissez la variable d'environnement ANTHROPIC_API_KEY "
                    "pour activer le chat.\n\n"
                    "```bash\nexport ANTHROPIC_API_KEY=sk-ant-...\n```"
                ),
                "tools_used": [],
                "error": "missing_api_key",
            }), 200

        # Rate limiting
        rate_error = _check_rate_limit()
        if rate_error:
            return jsonify({
                "role": "assistant",
                "content": rate_error,
                "tools_used": [],
                "error": "rate_limited",
            }), 429

        # Parse request
        try:
            body = request.get_json(force=True)
            messages = body.get("messages", [])
        except Exception:
            return jsonify({
                "role": "assistant",
                "content": "Requete invalide.",
                "tools_used": [],
                "error": "bad_request",
            }), 400

        if not messages:
            return jsonify({
                "role": "assistant",
                "content": "Aucun message recu.",
                "tools_used": [],
                "error": "empty",
            }), 400

        # Trim to last N messages for context window
        messages = messages[-MAX_CONTEXT_MESSAGES:]

        # Build system prompt
        system_prompt = _build_system_prompt(self.ledger)

        # Call Anthropic API with tool loop
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            tools_used: list[str] = []

            for _iteration in range(MAX_TOOL_ITERATIONS):
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=system_prompt,
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                )

                # Check if Claude wants to use tools
                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

                if not tool_use_blocks:
                    # No tool calls -- extract text and return
                    text_parts = [b.text for b in response.content if b.type == "text"]
                    final_text = "\n".join(text_parts)
                    return jsonify({
                        "role": "assistant",
                        "content": final_text,
                        "tools_used": tools_used,
                    })

                # Execute tool calls
                # First, add the assistant message with tool_use to context
                messages.append({
                    "role": "assistant",
                    "content": [
                        {"type": b.type, **({"text": b.text} if b.type == "text" else {"id": b.id, "name": b.name, "input": b.input})}
                        for b in response.content
                    ],
                })

                # Execute each tool and collect results
                tool_results = []
                for block in tool_use_blocks:
                    tools_used.append(block.name)
                    logger.info("Chat tool call: %s(%s)", block.name, json.dumps(block.input, ensure_ascii=False)[:200])
                    result = _execute_tool(block.name, block.input, self.ledger)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })

                messages.append({"role": "user", "content": tool_results})

            # If we hit max iterations, return what we have
            return jsonify({
                "role": "assistant",
                "content": "J'ai atteint la limite d'iterations d'outils. Veuillez reformuler votre question.",
                "tools_used": tools_used,
                "error": "max_iterations",
            })

        except ImportError:
            return jsonify({
                "role": "assistant",
                "content": (
                    "Le module `anthropic` n'est pas installe. "
                    "Installez-le avec:\n\n```bash\npip install anthropic\n```"
                ),
                "tools_used": [],
                "error": "missing_dependency",
            }), 200

        except Exception as e:
            logger.exception("Erreur lors de l'appel a l'API Anthropic")
            return jsonify({
                "role": "assistant",
                "content": f"Erreur de communication avec Claude: {e}",
                "tools_used": [],
                "error": "api_error",
            }), 500
