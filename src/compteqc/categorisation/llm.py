"""Classificateur LLM pour les transactions non classees par regles ou ML.

Utilise OpenRouter (API compatible OpenAI) avec structured output JSON
pour classifier les transactions selon le plan comptable. Toutes les
interactions sont journalisees en JSONL pour la detection de derive.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Charger .env au niveau du module
load_dotenv()


class ResultatClassificationLLM(BaseModel):
    """Modele Pydantic pour la reponse structuree du LLM."""

    compte: str = Field(description="Nom du compte Beancount (ex: Depenses:Bureau:Fournitures)")
    confiance: float = Field(ge=0.0, le=1.0, description="Niveau de confiance entre 0 et 1")
    raisonnement: str = Field(description="Explication breve du choix de classification")
    est_capex: bool = Field(
        default=False,
        description="True uniquement pour achats d'immobilisations (ordinateurs, meubles)",
    )


@dataclass(frozen=True)
class ResultatLLM:
    """Resultat interne du classificateur LLM."""

    compte: str
    confiance: float
    raisonnement: str
    est_capex: bool


_PROMPT_SYSTEME = """\
Tu es un comptable specialise pour une CCPC (corporation IT) au Quebec.
Le proprietaire est un consultant IT solo (revenus ~230k$/an). Il se verse un salaire via \
un service de paie externe ("Depot De Paie Consultants En"). La corporation a un seul \
employe (le proprietaire) et un produit logiciel (Enact).

CONTEXTE CRITIQUE — DEPENSES PERSONNELLES:
Le compte bancaire corporatif est parfois utilise pour des depenses personnelles.
Toute depense PERSONNELLE doit aller dans Passifs:Pret-Actionnaire (pret a l'actionnaire).
Ceci est TRES IMPORTANT pour la conformite fiscale (article 15(2) LIR).

DEPENSES PERSONNELLES (-> Passifs:Pret-Actionnaire):
- Epiceries: IGA, Metro, Provigo, Maxi, Costco (nourriture), Super C, PA
- Depanneurs: Couche-Tard, Deps
- Cafes personnels: petits montants ($3-15) dans un cafe sans contexte d'affaires
- Vetements: RWCO, Zara, H&M, Simons, etc.
- Virements personnels: "Virement Envoye" ou "Virement Recu" a/de personnes physiques \
(amis, famille) = personnel. Montant recu d'un proche = remboursement personnel, \
utilise Passifs:Pret-Actionnaire (credit).
- "Vir Courriel Virement Envoye/Recu" generiques = personnel
- Cannabis (SQDC), alcool (SAQ) = personnel
- Divertissement personnel: Netflix, Spotify (sauf si clairement d'affaires)

DEPENSES D'AFFAIRES LEGITIMES:
- Depenses:Repas-Representation — repas d'affaires avec clients/collegues (restaurants, \
pubs). En cas de doute pour un restaurant, utilise ce compte avec confiance 0.70-0.80.
- Depenses:Bureau:Internet-Telecom — telecom, internet d'affaires
- Depenses:Bureau:Abonnements-Logiciels — SaaS, outils de dev, cloud (AWS, GitHub, etc.)
- Depenses:Bureau:Fournitures — papeterie, petit materiel de bureau
- Depenses:Bureau:Loyer — loyer du bureau
- Depenses:Bureau:Entretien — electricite (Hydro-Quebec), entretien bureau
- Depenses:Deplacement:Transport — Uber/taxi/transport pour affaires
- Depenses:Deplacement:Hebergement — hotel pour deplacement professionnel
- Depenses:Vehicule:Carburant — essence (portion affaires)
- Depenses:Formation — cours, conferences, livres techniques
- Depenses:Publicite-Marketing — publicite, domaines, marketing
- Depenses:Frais-Bancaires — frais mensuels bancaires, frais de virement
- Depenses:Honoraires-Professionnels:Comptable — CPA, comptable
- Depenses:Honoraires-Professionnels:Juridique — avocat, notaire
- Depenses:Assurances:Responsabilite — assurance erreurs et omissions
- Depenses:Salaires:Brut — NE PAS utiliser pour les imports bancaires (gere par module paie)
- Passifs:CartesCredit:RBC — paiement de carte de credit (transfert entre comptes)

REVENUS:
- Revenus:Consultation — paiements de clients pour services IT
- Revenus:Produit-Logiciel — revenus du produit Enact
- Revenus:Interets — interets bancaires
- Revenus:Autres — credits d'impot, remboursements gouvernementaux

TRANSACTIONS INTER-COMPTES:
- "Paiement Divers Carte Rbc" = paiement de carte credit -> Passifs:CartesCredit:RBC
- "Depot De Paie Consultants En" = versement salaire via service de paie -> ignore ou \
Depenses:Salaires:Brut avec confiance 0.70 (normalement gere par module paie)

REGLES STRICTES:
- Choisis UNIQUEMENT parmi les comptes valides listes dans le prompt utilisateur.
- est_capex=true UNIQUEMENT pour immobilisations (ordinateurs >500$, meubles, equipement).
- Ta confiance doit refleter ta certitude reelle.
- Ne mentionne JAMAIS la TPS/TVQ/GST/QST.
- Confiance basse (<0.5) si tu n'es pas sur — ca enverra en revue humaine.
- N'utilise JAMAIS Depenses:Non-Classe si tu peux raisonnablement classifier.
- Depenses:Divers est pour les depenses d'affaires inclassables, PAS pour le personnel.

Tu DOIS repondre UNIQUEMENT en JSON valide avec ce schema exact:
{"compte": "...", "confiance": 0.0, "raisonnement": "...", "est_capex": false}
"""


class ClassificateurLLM:
    """Classificateur LLM utilisant OpenRouter (API compatible OpenAI).

    Utilise le SDK openai pointe vers OpenRouter avec JSON mode
    pour obtenir des reponses structurees et validees.
    """

    def __init__(
        self,
        comptes_valides: list[str],
        chemin_log: Path = Path("data/llm_log/categorisations.jsonl"),
        modele: str = "anthropic/claude-sonnet-4",
    ) -> None:
        self._comptes_valides = set(comptes_valides)
        self._chemin_log = chemin_log
        self._modele = modele
        self._client = None

    def _get_client(self):
        """Initialise le client OpenAI pointe vers OpenRouter de facon lazy."""
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=os.environ.get("OPENROUTER_API_KEY", ""),
                base_url=os.environ.get(
                    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
                ),
            )
        return self._client

    @property
    def est_disponible(self) -> bool:
        """True si la cle API OpenRouter est configuree."""
        return bool(os.environ.get("OPENROUTER_API_KEY"))

    def classifier(
        self,
        payee: str,
        narration: str,
        montant: Decimal,
        historique_vendeur: list[dict] | None = None,
        transactions_similaires: list[dict] | None = None,
    ) -> ResultatLLM:
        """Classifie une transaction via OpenRouter.

        Args:
            payee: Nom du beneficiaire.
            narration: Description de la transaction.
            montant: Montant de la transaction.
            historique_vendeur: Historique des classifications pour ce vendeur.
            transactions_similaires: Transactions similaires deja classees.

        Returns:
            ResultatLLM avec le compte, la confiance, le raisonnement et le flag CAPEX.
        """
        prompt = self._construire_prompt(
            payee, narration, montant, historique_vendeur, transactions_similaires
        )

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self._modele,
                max_tokens=256,
                messages=[
                    {"role": "system", "content": _PROMPT_SYSTEME},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            contenu = response.choices[0].message.content
            # OpenRouter peut retourner du JSON enveloppe dans des fences markdown
            if contenu.startswith("```"):
                contenu = contenu.strip("`").removeprefix("json").strip()
            resultat_parse = ResultatClassificationLLM.model_validate_json(contenu)

            # Valider que le compte retourne est dans la liste des comptes valides
            if resultat_parse.compte not in self._comptes_valides:
                logger.warning(
                    "LLM a retourne un compte invalide: '%s'. Fallback a Non-Classe.",
                    resultat_parse.compte,
                )
                resultat = ResultatLLM(
                    compte="Depenses:Non-Classe",
                    confiance=0.1,
                    raisonnement=f"Compte invalide retourne par LLM: {resultat_parse.compte}",
                    est_capex=False,
                )
            else:
                resultat = ResultatLLM(
                    compte=resultat_parse.compte,
                    confiance=resultat_parse.confiance,
                    raisonnement=resultat_parse.raisonnement,
                    est_capex=resultat_parse.est_capex,
                )

            # Journaliser
            self._enregistrer_log(
                payee=payee,
                narration=narration,
                montant=montant,
                prompt=prompt,
                response=response,
                resultat=resultat,
            )

            return resultat

        except Exception:
            logger.warning("Erreur lors de l'appel API OpenRouter", exc_info=True)
            return ResultatLLM(
                compte="Depenses:Non-Classe",
                confiance=0.0,
                raisonnement="Erreur API",
                est_capex=False,
            )

    def _construire_prompt(
        self,
        payee: str,
        narration: str,
        montant: Decimal,
        historique_vendeur: list[dict] | None,
        transactions_similaires: list[dict] | None,
    ) -> str:
        """Construit le prompt utilisateur avec tout le contexte."""
        comptes_liste = "\n".join(f"  - {c}" for c in sorted(self._comptes_valides))

        parties = [
            "TRANSACTION A CLASSIFIER:",
            f"  Beneficiaire: {payee}",
            f"  Description: {narration}",
            f"  Montant: {montant} CAD",
            "",
            "COMPTES VALIDES (choisis UNIQUEMENT parmi ceux-ci):",
            comptes_liste,
        ]

        if historique_vendeur:
            parties.append("")
            parties.append("HISTORIQUE DE CE VENDEUR:")
            for h in historique_vendeur[:5]:
                parties.append(f"  - {h.get('compte', '?')} (confiance: {h.get('confiance', '?')})")

        if transactions_similaires:
            parties.append("")
            parties.append("TRANSACTIONS SIMILAIRES DEJA CLASSEES:")
            for t in transactions_similaires[:5]:
                payee_t = t.get("payee", "?")
                narr_t = t.get("narration", "?")
                cpt_t = t.get("compte", "?")
                parties.append(f"  - {payee_t} | {narr_t} -> {cpt_t}")

        return "\n".join(parties)

    def _enregistrer_log(
        self,
        payee: str,
        narration: str,
        montant: Decimal,
        prompt: str,
        response,
        resultat: ResultatLLM,
    ) -> None:
        """Enregistre l'interaction LLM dans le fichier JSONL."""
        self._chemin_log.parent.mkdir(parents=True, exist_ok=True)

        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]

        # Extraire les tokens utilises (format OpenAI)
        tokens_utilises = 0
        if hasattr(response, "usage") and response.usage:
            tokens_utilises = (
                getattr(response.usage, "prompt_tokens", 0)
                + getattr(response.usage, "completion_tokens", 0)
            )

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payee": payee,
            "narration": narration,
            "montant": str(montant),
            "prompt_hash": prompt_hash,
            "modele": self._modele,
            "compte": resultat.compte,
            "confiance": resultat.confiance,
            "raisonnement": resultat.raisonnement,
            "est_capex": resultat.est_capex,
            "tokens_utilises": tokens_utilises,
        }

        with open(self._chemin_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
