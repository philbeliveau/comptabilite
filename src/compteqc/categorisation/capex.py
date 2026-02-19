"""Detecteur CAPEX pour identifier les immobilisations potentielles.

Signale les transactions qui depassent un seuil de montant ou qui
correspondent a des vendeurs connus d'equipement. Suggere une classe
DPA (CCA) basee sur des mots-cles.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)

# Mots-cles pour la suggestion de classe DPA
_MOTS_CLES_DPA: list[tuple[list[str], int]] = [
    (["ordinateur", "laptop", "macbook", "imac", "computer", "moniteur", "monitor"], 50),
    (["telephone", "phone", "iphone"], 50),
    (["meuble", "bureau", "chaise", "desk", "chair", "furniture"], 8),
    (["vehicule", "auto", "car", "camion", "truck"], 10),
    (["logiciel", "software", "licence", "license"], 12),
]

# Vendeurs connus d'equipement
_VENDEURS_DEFAUT: list[str] = [
    "apple",
    "dell",
    "b&h",
    "lenovo",
    "microsoft surface",
    "logitech",
    "samsung",
    "lg electronics",
]


@dataclass(frozen=True)
class ResultatCAPEX:
    """Resultat de la verification CAPEX."""

    est_capex: bool
    raison: str | None
    classe_suggeree: int | None


class DetecteurCAPEX:
    """Detecte les transactions qui pourraient etre des immobilisations (CAPEX).

    Signale si le montant depasse un seuil ou si le vendeur est connu.
    Suggere une classe DPA basee sur des mots-cles dans le payee/narration.
    """

    def __init__(
        self,
        seuil_montant: Decimal = Decimal("500"),
        patrons_vendeurs: list[str] | None = None,
    ) -> None:
        self._seuil = seuil_montant
        self._vendeurs = patrons_vendeurs if patrons_vendeurs is not None else _VENDEURS_DEFAUT

    def verifier(self, montant: Decimal, payee: str, narration: str) -> ResultatCAPEX:
        """Verifie si une transaction est un CAPEX potentiel.

        Args:
            montant: Montant de la transaction.
            payee: Nom du beneficiaire.
            narration: Description de la transaction.

        Returns:
            ResultatCAPEX avec le statut, la raison et la classe DPA suggeree.
        """
        montant_abs = abs(montant)
        texte_lower = f"{payee} {narration}".lower()
        raisons: list[str] = []

        # Verification par montant
        if montant_abs >= self._seuil:
            raisons.append(f"montant {montant_abs} >= seuil {self._seuil}")

        # Verification par vendeur connu
        for vendeur in self._vendeurs:
            if vendeur.lower() in texte_lower:
                raisons.append(f"vendeur connu: {vendeur}")
                break

        if not raisons:
            return ResultatCAPEX(est_capex=False, raison=None, classe_suggeree=None)

        # Suggestion de classe DPA
        classe = self._suggerer_classe(texte_lower)

        return ResultatCAPEX(
            est_capex=True,
            raison="; ".join(raisons),
            classe_suggeree=classe,
        )

    def _suggerer_classe(self, texte_lower: str) -> int | None:
        """Suggere une classe DPA basee sur des mots-cles.

        Args:
            texte_lower: Texte combine (payee + narration) en minuscules.

        Returns:
            Numero de classe DPA ou None si aucune correspondance.
        """
        for mots_cles, classe in _MOTS_CLES_DPA:
            for mot in mots_cles:
                if mot in texte_lower:
                    return classe
        return None
