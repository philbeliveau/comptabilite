"""Module echeances: calendrier de production et suivi des remises.

Fournit le calcul des echeances fiscales, les alertes de production
et le suivi des remises de paie (retenues + cotisations employeur).
"""

from compteqc.echeances.calendrier import (
    AlerteEcheance,
    Echeance,
    TypeEcheance,
    calculer_echeances,
    formater_rappels_cli,
    integrer_echeances_pret,
    obtenir_alertes,
)
from compteqc.echeances.remises import (
    RemisePaie,
    prochaine_remise,
    suivi_remises,
)

__all__ = [
    "AlerteEcheance",
    "Echeance",
    "RemisePaie",
    "TypeEcheance",
    "calculer_echeances",
    "formater_rappels_cli",
    "integrer_echeances_pret",
    "obtenir_alertes",
    "prochaine_remise",
    "suivi_remises",
]
