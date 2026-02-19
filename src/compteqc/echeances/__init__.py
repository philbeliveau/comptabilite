"""Module echeances: calendrier de production, suivi des remises et verification.

Fournit le calcul des echeances fiscales, les alertes de production,
le suivi des remises de paie (retenues + cotisations employeur) et
la verification de fin d'exercice pour le package CPA.
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
from compteqc.echeances.verification import (
    Severite,
    VerificationResult,
    verifier_fin_exercice,
)

__all__ = [
    "AlerteEcheance",
    "Echeance",
    "RemisePaie",
    "Severite",
    "TypeEcheance",
    "VerificationResult",
    "calculer_echeances",
    "formater_rappels_cli",
    "integrer_echeances_pret",
    "obtenir_alertes",
    "prochaine_remise",
    "suivi_remises",
    "verifier_fin_exercice",
]
