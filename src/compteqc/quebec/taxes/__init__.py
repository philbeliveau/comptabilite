"""Module de calcul et suivi TPS/TVQ."""

from compteqc.quebec.taxes.calcul import (
    appliquer_taxes,
    extraire_taxes,
    extraire_taxes_selon_traitement,
)
from compteqc.quebec.taxes.traitement import (
    ReglesTaxes,
    charger_regles_taxes,
    determiner_traitement_depense,
    determiner_traitement_revenu,
)

__all__ = [
    "appliquer_taxes",
    "extraire_taxes",
    "extraire_taxes_selon_traitement",
    "ReglesTaxes",
    "charger_regles_taxes",
    "determiner_traitement_depense",
    "determiner_traitement_revenu",
]
