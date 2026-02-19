"""Moteur de categorisation par regles YAML."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal

from compteqc.categorisation.regles import ConfigRegles

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultatCategorisation:
    """Resultat d'une categorisation."""

    compte: str
    confiance: float
    regle: str | None
    source: str  # "regle" ou "non-classe"


class MoteurRegles:
    """Moteur de categorisation par regles.

    Evalue les regles dans l'ordre. La premiere correspondance gagne.
    Ne retourne jamais un compte qui n'est pas dans comptes_valides.
    """

    def __init__(self, regles: ConfigRegles, comptes_valides: set[str]):
        """Initialise le moteur avec des regles et un set de comptes valides.

        Args:
            regles: Configuration des regles de categorisation.
            comptes_valides: Set de noms de comptes Beancount valides.
        """
        self._comptes_valides = comptes_valides
        self._regles_compilees: list[tuple[str, list, str, float]] = []

        for regle in regles.regles:
            patterns = []
            if regle.condition.payee:
                try:
                    patterns.append(("payee", re.compile(regle.condition.payee, re.IGNORECASE)))
                except re.error as e:
                    logger.warning("Regex invalide pour regle '%s' (payee): %s", regle.nom, e)
                    continue

            if regle.condition.narration:
                try:
                    patterns.append(
                        ("narration", re.compile(regle.condition.narration, re.IGNORECASE))
                    )
                except re.error as e:
                    logger.warning(
                        "Regex invalide pour regle '%s' (narration): %s", regle.nom, e
                    )
                    continue

            self._regles_compilees.append((
                regle.nom,
                patterns,
                regle.compte,
                regle.confiance,
            ))

            # Stocker les bornes de montant separement
            self._bornes: dict[str, tuple[Decimal | None, Decimal | None]] = {}
            for r in regles.regles:
                self._bornes[r.nom] = (r.condition.montant_min, r.condition.montant_max)

    def categoriser(
        self, payee: str, narration: str, montant: Decimal
    ) -> ResultatCategorisation:
        """Categorise une transaction selon les regles.

        Args:
            payee: Le nom du beneficiaire.
            narration: La narration/description de la transaction.
            montant: Le montant de la transaction.

        Returns:
            Resultat de la categorisation (compte, confiance, regle, source).
        """
        texte_complet = f"{payee} {narration}".upper()

        for nom, patterns, compte, confiance in self._regles_compilees:
            # Verifier les patterns regex
            match = True
            for type_pattern, pattern in patterns:
                if type_pattern == "payee":
                    if not pattern.search(texte_complet):
                        match = False
                        break
                elif type_pattern == "narration":
                    if not pattern.search(narration):
                        match = False
                        break

            if not match:
                continue

            # Verifier les bornes de montant
            montant_min, montant_max = self._bornes.get(nom, (None, None))
            montant_abs = abs(montant)
            if montant_min is not None and montant_abs < montant_min:
                continue
            if montant_max is not None and montant_abs > montant_max:
                continue

            # Verifier que le compte cible est valide
            if compte not in self._comptes_valides:
                logger.warning(
                    "Regle '%s' pointe vers un compte inexistant: '%s'. "
                    "Transaction traitee comme non-classe.",
                    nom,
                    compte,
                )
                return ResultatCategorisation(
                    compte="Depenses:Non-Classe",
                    confiance=0.0,
                    regle=nom,
                    source="non-classe",
                )

            return ResultatCategorisation(
                compte=compte,
                confiance=confiance,
                regle=nom,
                source="regle",
            )

        # Aucune regle ne matche
        return ResultatCategorisation(
            compte="Depenses:Non-Classe",
            confiance=0.0,
            regle=None,
            source="non-classe",
        )
