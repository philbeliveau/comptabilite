"""Definitions des classes DPA (CCA) selon l'ARC.

Chaque classe contient un taux de deduction et une description.
Ref: https://www.canada.ca/fr/agence-revenu/services/impot/entreprises/sujets/
     entreprise-individuelle-societe-personnes/declaration-revenus-depenses-entreprise/
     demander-deduction-amortissement/categories-biens-amortissables.html
"""

from decimal import Decimal

CLASSES_DPA: dict[int, dict] = {
    8: {
        "taux": Decimal("0.20"),
        "description": "Mobilier et equipement de bureau",
    },
    10: {
        "taux": Decimal("0.30"),
        "description": "Vehicules automobiles",
    },
    12: {
        "taux": Decimal("1.00"),
        "description": "Logiciels, outils < $500",
    },
    50: {
        "taux": Decimal("0.55"),
        "description": "Materiel informatique (ordinateurs, moniteurs)",
    },
    54: {
        "taux": Decimal("0.30"),
        "description": "Vehicules zero emission",
    },
}
