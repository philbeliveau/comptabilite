"""Classificateur LLM pour les transactions non classees par regles ou ML.

Utilise l'API Anthropic avec structured output (messages.parse) pour
classifier les transactions selon le plan comptable. Toutes les
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

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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
Tu es un comptable specialise pour une corporation IT au Quebec (CCPC).
Tu dois classifier une transaction dans le plan comptable fourni.

REGLES STRICTES:
- Choisis UNIQUEMENT parmi les comptes valides listes ci-dessous.
- Set est_capex=true UNIQUEMENT pour achats d'immobilisations (ordinateurs, meubles, etc.)
- Ta confiance doit refleter ta certitude reelle sur la classification.
- Ne mentionne JAMAIS la TPS/TVQ/GST/QST ni aucun calcul de taxe.
- Si tu n'es pas certain, utilise une confiance basse.
"""


class ClassificateurLLM:
    """Classificateur LLM utilisant l'API Anthropic avec structured output.

    Utilise client.messages.parse() avec un modele Pydantic (output_format)
    pour obtenir des reponses structurees et validees.
    """

    def __init__(
        self,
        comptes_valides: list[str],
        chemin_log: Path = Path("data/llm_log/categorisations.jsonl"),
        modele: str = "claude-sonnet-4-5-20250929",
    ) -> None:
        self._comptes_valides = set(comptes_valides)
        self._chemin_log = chemin_log
        self._modele = modele
        self._client = None

    def _get_client(self):
        """Initialise le client Anthropic de facon lazy."""
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    @property
    def est_disponible(self) -> bool:
        """True si la cle API Anthropic est configuree."""
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def classifier(
        self,
        payee: str,
        narration: str,
        montant: Decimal,
        historique_vendeur: list[dict] | None = None,
        transactions_similaires: list[dict] | None = None,
    ) -> ResultatLLM:
        """Classifie une transaction via l'API Anthropic.

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
            response = client.messages.parse(
                model=self._modele,
                max_tokens=256,
                system=_PROMPT_SYSTEME,
                messages=[{"role": "user", "content": prompt}],
                output_format=ResultatClassificationLLM,
            )

            resultat_parse = response.parsed_output

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
            logger.warning("Erreur lors de l'appel API Anthropic", exc_info=True)
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

        # Extraire les tokens utilises
        tokens_utilises = 0
        if hasattr(response, "usage") and response.usage:
            tokens_utilises = (
                getattr(response.usage, "input_tokens", 0)
                + getattr(response.usage, "output_tokens", 0)
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
