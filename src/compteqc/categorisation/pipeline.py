"""Pipeline de categorisation a trois niveaux: regles -> ML -> LLM.

Orchestre la cascade de categorisation avec scoring de confiance,
routage par seuil et detection CAPEX.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from compteqc.categorisation.capex import DetecteurCAPEX
from compteqc.categorisation.ml import PredicteurML
from compteqc.categorisation.moteur import MoteurRegles

logger = logging.getLogger(__name__)


@runtime_checkable
class ClassificateurLLM(Protocol):
    """Protocole pour le classificateur LLM (implemente dans 03-02)."""

    def classifier(self, payee: str, narration: str, montant: Decimal) -> Any:
        """Classifie une transaction. Retourne un objet avec .compte et .confiance."""
        ...


@dataclass(frozen=True)
class ResultatPipeline:
    """Resultat complet du pipeline de categorisation."""

    compte: str
    confiance: float
    source: str  # "regle", "ml", "llm", "non-classe"
    regle: str | None
    est_capex: bool
    classe_dpa: int | None
    revue_obligatoire: bool
    suggestions: dict | None  # {"ml": (compte, conf), "llm": (compte, conf)} en cas de desaccord


class PipelineCategorisation:
    """Orchestrateur de categorisation a trois niveaux.

    Cascade: regles (tier 1) -> ML (tier 2) -> LLM (tier 3).
    Chaque tier ne traite que les transactions non classees par le tier precedent.
    """

    SEUIL_AUTO_APPROUVE = 0.95
    SEUIL_REVUE_OPTIONNELLE = 0.80

    def __init__(
        self,
        moteur_regles: MoteurRegles,
        predicteur_ml: PredicteurML | None,
        classificateur_llm: Any | None,
        detecteur_capex: DetecteurCAPEX,
    ) -> None:
        self._regles = moteur_regles
        self._ml = predicteur_ml
        self._llm = classificateur_llm
        self._capex = detecteur_capex

    def categoriser(self, payee: str, narration: str, montant: Decimal) -> ResultatPipeline:
        """Categorise une transaction via la cascade regles -> ML -> LLM.

        Args:
            payee: Nom du beneficiaire.
            narration: Description de la transaction.
            montant: Montant de la transaction.

        Returns:
            ResultatPipeline avec compte, confiance, source et flags.
        """
        # Tier 1: Regles
        resultat_regles = self._regles.categoriser(payee, narration, montant)
        if resultat_regles.source == "regle":
            capex = self._capex.verifier(montant, payee, narration)
            return ResultatPipeline(
                compte=resultat_regles.compte,
                confiance=1.0,
                source="regle",
                regle=resultat_regles.regle,
                est_capex=capex.est_capex,
                classe_dpa=capex.classe_suggeree,
                revue_obligatoire=False,
                suggestions=None,
            )

        # Tier 2: ML
        resultat_ml = None
        if self._ml is not None and self._ml.est_entraine:
            resultat_ml = self._ml.predire(payee, narration, montant)

        # Tier 3: LLM
        resultat_llm = None
        if self._llm is not None:
            try:
                r = self._llm.classifier(payee, narration, montant)
                resultat_llm = (r.compte, r.confiance)
            except Exception:
                logger.warning("Erreur lors de la classification LLM", exc_info=True)

        # Resolution
        compte, confiance, source, suggestions = self._resoudre(resultat_ml, resultat_llm)

        # CAPEX
        capex = self._capex.verifier(montant, payee, narration)

        # Revue obligatoire
        revue = (
            confiance < self.SEUIL_REVUE_OPTIONNELLE
            or suggestions is not None
        )

        return ResultatPipeline(
            compte=compte,
            confiance=confiance,
            source=source,
            regle=None,
            est_capex=capex.est_capex,
            classe_dpa=capex.classe_suggeree,
            revue_obligatoire=revue,
            suggestions=suggestions,
        )

    def _resoudre(
        self,
        resultat_ml: Any | None,
        resultat_llm: tuple[str, float] | None,
    ) -> tuple[str, float, str, dict | None]:
        """Resout les resultats ML et LLM.

        Returns:
            Tuple de (compte, confiance, source, suggestions).
        """
        ml_compte = resultat_ml.compte if resultat_ml else None
        ml_conf = resultat_ml.confiance if resultat_ml else 0.0
        llm_compte = resultat_llm[0] if resultat_llm else None
        llm_conf = resultat_llm[1] if resultat_llm else 0.0

        has_ml = resultat_ml is not None
        has_llm = resultat_llm is not None

        if has_ml and has_llm:
            if ml_compte == llm_compte:
                # Accord: utiliser la confiance la plus haute
                if ml_conf >= llm_conf:
                    return (ml_compte, ml_conf, "ml", None)
                else:
                    return (llm_compte, llm_conf, "llm", None)
            else:
                # Desaccord: signaler les deux
                suggestions = {
                    "ml": (ml_compte, ml_conf),
                    "llm": (llm_compte, llm_conf),
                }
                # Utiliser celui avec la plus haute confiance comme proposition
                if ml_conf >= llm_conf:
                    return (ml_compte, ml_conf, "ml", suggestions)
                else:
                    return (llm_compte, llm_conf, "llm", suggestions)
        elif has_ml:
            return (ml_compte, ml_conf, "ml", None)
        elif has_llm:
            return (llm_compte, llm_conf, "llm", None)
        else:
            return ("Depenses:Non-Classe", 0.0, "non-classe", None)

    def determiner_destination(self, resultat: ResultatPipeline) -> str:
        """Determine la destination d'un resultat de categorisation.

        Args:
            resultat: Le resultat du pipeline.

        Returns:
            "direct" (regles ou >95%), "pending" (80-95% ou CAPEX), "revue" (<80% ou desaccord).
        """
        if resultat.revue_obligatoire:
            return "revue"
        if resultat.est_capex:
            return "pending"
        if resultat.source == "regle" or resultat.confiance > self.SEUIL_AUTO_APPROUVE:
            return "direct"
        if resultat.confiance >= self.SEUIL_REVUE_OPTIONNELLE:
            return "pending"
        return "revue"
