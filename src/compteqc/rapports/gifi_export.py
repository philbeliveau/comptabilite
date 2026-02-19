"""Validation GIFI et export CSV pour import TaxCycle.

Le GIFI (General Index of Financial Information) est le systeme de codes
utilise par l'ARC pour la declaration fiscale des societes (T2).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from beancount.core import data


@dataclass
class GIFIValidationResult:
    """Resultat de la validation GIFI avant export."""

    balanced: bool
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    total_net_income: Decimal
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def extract_gifi_map(entries: list) -> dict[str, str]:
    """Extrait le mappage compte -> code GIFI des directives Open.

    Lit le champ metadata 'gifi' des directives d'ouverture de compte.

    Args:
        entries: Liste d'entrees Beancount (incluant les Open).

    Returns:
        Dictionnaire {nom_compte: code_gifi}.
    """
    gifi_map: dict[str, str] = {}
    for entry in entries:
        if isinstance(entry, data.Open) and entry.meta:
            gifi_code = entry.meta.get("gifi")
            if gifi_code:
                gifi_map[entry.account] = str(gifi_code)
    return gifi_map


def aggregate_by_gifi(
    soldes: dict[str, Decimal],
    gifi_map: dict[str, str],
) -> dict[str, Decimal]:
    """Agrege les soldes par code GIFI.

    Plusieurs comptes peuvent mapper au meme code GIFI; leurs soldes sont additionnes.

    Args:
        soldes: Dictionnaire {nom_compte: solde}.
        gifi_map: Dictionnaire {nom_compte: code_gifi}.

    Returns:
        Dictionnaire {code_gifi: solde_agrege}.
    """
    gifi_balances: dict[str, Decimal] = {}
    for acct, montant in soldes.items():
        gifi = gifi_map.get(acct)
        if gifi:
            gifi_balances[gifi] = gifi_balances.get(gifi, Decimal("0")) + montant
    return gifi_balances


def validate_gifi(
    soldes: dict[str, Decimal],
    gifi_map: dict[str, str],
) -> GIFIValidationResult:
    """Valide l'equilibre GIFI avant export.

    Verifie l'equation comptable: Actifs = Passifs + Capitaux + Resultat net.

    Args:
        soldes: Dictionnaire {nom_compte: solde}.
        gifi_map: Dictionnaire {nom_compte: code_gifi}.

    Returns:
        GIFIValidationResult avec statut et messages.
    """
    total_assets = Decimal("0")
    total_liabilities = Decimal("0")
    total_equity = Decimal("0")
    total_revenue = Decimal("0")
    total_expenses = Decimal("0")

    for acct, montant in soldes.items():
        if acct.startswith("Actifs"):
            total_assets += montant
        elif acct.startswith("Passifs"):
            total_liabilities += montant  # negatif en beancount
        elif acct.startswith("Capital"):
            total_equity += montant  # negatif en beancount
        elif acct.startswith("Revenus"):
            total_revenue += montant  # negatif en beancount
        elif acct.startswith("Depenses"):
            total_expenses += montant  # positif en beancount

    # Resultat net = -Revenus - Depenses (pour le cote credit)
    net_income = -(total_revenue + total_expenses)

    warnings: list[str] = []
    errors: list[str] = []

    # Verification: somme de toutes les entrees devrait etre zero
    # En beancount: Actifs + Passifs + Capital + Revenus + Depenses = 0
    # Equivalent: Actifs = -(Passifs + Capital + Revenus + Depenses)
    # Ou: Actifs = |Passifs| + |Capital| + Resultat net
    equation_diff = total_assets + total_liabilities + total_equity + total_revenue + total_expenses

    if equation_diff != Decimal("0"):
        errors.append(
            f"Equation comptable desequilibree: difference de {equation_diff.quantize(Decimal('0.01'))} CAD"
        )

    # Avertissements
    if total_revenue > Decimal("0"):
        warnings.append("Revenus positifs detectes (normalement credits/negatifs en beancount)")

    if total_assets < Decimal("0"):
        warnings.append("Total actifs negatif")

    balanced = len(errors) == 0

    return GIFIValidationResult(
        balanced=balanced,
        total_assets=total_assets.quantize(Decimal("0.01")),
        total_liabilities=abs(total_liabilities).quantize(Decimal("0.01")),
        total_equity=abs(total_equity).quantize(Decimal("0.01")),
        total_net_income=net_income.quantize(Decimal("0.01")),
        warnings=warnings,
        errors=errors,
    )


def export_gifi_csv(
    gifi_balances: dict[str, Decimal],
    output_path: Path,
    schedule: str = "S100",
) -> Path:
    """Exporte les soldes GIFI en CSV pour import TaxCycle.

    Formate: CODE_GIFI,MONTANT avec montants quantizes a 0.01.
    Les soldes a zero sont exclus.

    Args:
        gifi_balances: Dictionnaire {code_gifi: montant}.
        output_path: Chemin du fichier CSV de sortie.
        schedule: Code de l'annexe (defaut S100).

    Returns:
        Chemin du fichier CSV cree.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["GIFI_CODE", "AMOUNT", "SCHEDULE"])
        for code in sorted(gifi_balances.keys()):
            montant = gifi_balances[code]
            if montant == Decimal("0"):
                continue
            writer.writerow([
                code,
                str(montant.quantize(Decimal("0.01"))),
                schedule,
            ])
    return output_path
