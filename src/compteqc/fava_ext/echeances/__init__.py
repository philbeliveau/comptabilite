"""Extension Fava: Echeances et rappels de production.

Affiche les echeances fiscales et alertes de production avec des bannieres
a code de couleur selon l'urgence. Se branche sur le module Phase 5
compteqc.echeances.calendrier quand il est disponible.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def couleur_urgence(urgence: str) -> str:
    """Retourne la classe CSS correspondant au niveau d'urgence.

    Args:
        urgence: Niveau d'urgence (critique, urgent, normal, info).

    Returns:
        Classe CSS pour la banniere d'alerte.
    """
    mapping = {
        "critique": "alerte-critique",
        "urgent": "alerte-urgent",
        "normal": "alerte-normal",
        "info": "alerte-info",
    }
    return mapping.get(urgence, "alerte-info")


# ---------------------------------------------------------------------------
# Extension
# ---------------------------------------------------------------------------

class EcheancesExtension(FavaExtensionBase):
    """Echeances fiscales et alertes de production."""

    report_title = "Echeances"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._alertes: list[dict[str, Any]] = []
        self._echeances_disponible: bool = False

    def _normaliser_alertes(self, alertes_brutes: list[object]) -> list[dict[str, Any]]:
        """Convertit les alertes du domaine vers un format simple pour le template."""
        alertes: list[dict[str, Any]] = []
        for alerte in alertes_brutes:
            urgence = getattr(alerte, "urgence", "info")
            echeance = getattr(alerte, "echeance", None)
            alertes.append(
                {
                    "description": getattr(echeance, "description", ""),
                    "date_limite": getattr(echeance, "date_limite", ""),
                    "jours_restants": getattr(alerte, "jours_restants", 0),
                    "urgence": urgence,
                    "classe_css": couleur_urgence(urgence),
                }
            )
        return alertes

    def after_load_file(self) -> None:
        """Charge les echeances depuis le module Phase 5 si disponible."""
        try:
            from compteqc.echeances.calendrier import (  # type: ignore[import-not-found]
                calculer_echeances,
                obtenir_alertes,
            )

            # Determiner la fin d'exercice
            fin_exercice = date(date.today().year, 12, 31)

            echeances = calculer_echeances(fin_exercice)
            alertes_brutes = obtenir_alertes(echeances)
            self._alertes = self._normaliser_alertes(alertes_brutes)
            self._echeances_disponible = True
        except ImportError:
            self._alertes = []
            self._echeances_disponible = False

    def alertes(self) -> list[dict[str, Any]]:
        """Retourne la liste des alertes actives."""
        return self._alertes

    def echeances_disponible(self) -> bool:
        """Retourne True si le module d'echeances Phase 5 est disponible."""
        return self._echeances_disponible
