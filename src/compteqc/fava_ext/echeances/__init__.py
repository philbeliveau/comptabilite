"""Extension Fava: Echeances et rappels de production.

Affiche les echeances fiscales et alertes de production avec des bannieres
a code de couleur selon l'urgence. Se branche sur le module Phase 5
compteqc.echeances.calendrier quand il est disponible.
"""

from __future__ import annotations

from datetime import date

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
        self._alertes: list[dict] = []
        self._echeances_disponible: bool = False

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
            # Pre-compute CSS class for each alert (Jinja2 can't call Python functions)
            for alerte in alertes_brutes:
                alerte["classe_css"] = couleur_urgence(alerte.get("urgence", "info"))
            self._alertes = alertes_brutes
            self._echeances_disponible = True
        except ImportError:
            self._alertes = []
            self._echeances_disponible = False

    def alertes(self) -> list[dict]:
        """Retourne la liste des alertes actives."""
        return self._alertes

    def echeances_disponible(self) -> bool:
        """Retourne True si le module d'echeances Phase 5 est disponible."""
        return self._echeances_disponible
