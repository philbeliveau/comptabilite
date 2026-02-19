"""Predicteur ML pour la categorisation de transactions.

Utilise sklearn directement (SVC avec probability=True) plutot que
smart_importer.EntryPredictor qui est trop couple au workflow beangulp.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.pipeline import Pipeline, make_pipeline, make_union
from sklearn.svm import SVC

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultatML:
    """Resultat d'une prediction ML."""

    compte: str
    confiance: float


class PredicteurML:
    """Predicteur ML avec scoring de confiance par probabilite.

    Utilise un pipeline sklearn CountVectorizer + SVC(probability=True)
    pour predire le compte comptable a partir du payee et de la narration.
    """

    MIN_TRAINING_SIZE = 20

    def __init__(self) -> None:
        self._pipeline: Pipeline | None = None
        self._est_entraine: bool = False
        self._classes: np.ndarray | None = None

    @property
    def est_entraine(self) -> bool:
        """Retourne True si le modele a ete entraine avec succes."""
        return self._est_entraine

    def entrainer(self, data: list[tuple[str, str, str]]) -> None:
        """Entraine le modele sur des donnees approuvees.

        Args:
            data: Liste de tuples (payee, narration, compte).
                  Chaque tuple represente une transaction approuvee.
        """
        if len(data) < self.MIN_TRAINING_SIZE:
            logger.warning(
                "Donnees insuffisantes pour entrainer le modele ML: "
                "%d entrees (minimum %d)",
                len(data),
                self.MIN_TRAINING_SIZE,
            )
            self._est_entraine = False
            return

        comptes = [compte for _, _, compte in data]
        comptes_distincts = set(comptes)
        if len(comptes_distincts) < 2:
            logger.warning(
                "Pas assez de comptes distincts pour entrainer: %d (minimum 2)",
                len(comptes_distincts),
            )
            self._est_entraine = False
            return

        # Construire les textes d'entree avec poids
        # narration poids 1.0, payee poids 0.8 (repete pour simuler le poids)
        textes = [f"{narration} {payee}" for payee, narration, _ in data]

        self._pipeline = make_pipeline(
            CountVectorizer(analyzer="word", ngram_range=(1, 2)),
            SVC(kernel="linear", probability=True),
        )

        self._pipeline.fit(textes, comptes)
        self._classes = self._pipeline.classes_
        self._est_entraine = True
        logger.info(
            "Modele ML entraine avec %d entrees, %d comptes distincts",
            len(data),
            len(comptes_distincts),
        )

    def predire(self, payee: str, narration: str, montant: Decimal) -> ResultatML | None:
        """Predit le compte comptable pour une transaction.

        Args:
            payee: Nom du beneficiaire.
            narration: Description de la transaction.
            montant: Montant de la transaction (non utilise pour l'instant).

        Returns:
            ResultatML avec le compte predit et la confiance, ou None si non entraine.
        """
        if not self._est_entraine or self._pipeline is None:
            return None

        texte = f"{narration} {payee}"
        probas = self._pipeline.predict_proba([texte])[0]
        idx_max = int(np.argmax(probas))
        compte = str(self._classes[idx_max])
        confiance = float(probas[idx_max])

        return ResultatML(compte=compte, confiance=confiance)
