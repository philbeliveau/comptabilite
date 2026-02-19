"""Suivi des cumuls annuels (YTD) de cotisations depuis le grand-livre Beancount.

Derive les totaux directement des transactions existantes (source unique de verite).
Utilise les sous-comptes de passifs pour un suivi par type de cotisation.
"""

from decimal import Decimal

from beancount import loader
from beancount.core import data

# Mappage: cle de cumul -> compte Beancount correspondant
# Les montants dans les comptes de passifs sont negatifs (credits),
# on prend la valeur absolue pour obtenir le cumul positif.
MAPPAGE_COMPTES_RETENUES: dict[str, str] = {
    "qpp_base_employe": "Passifs:Retenues:QPP-Base",
    "qpp_supp1_employe": "Passifs:Retenues:QPP-Supp1",
    "qpp_supp2_employe": "Passifs:Retenues:QPP-Supp2",
    "rqap_employe": "Passifs:Retenues:RQAP",
    "ae_employe": "Passifs:Retenues:AE",
    "impot_federal": "Passifs:Retenues:Impot-Federal",
    "impot_quebec": "Passifs:Retenues:Impot-Quebec",
}

MAPPAGE_COMPTES_EMPLOYEUR: dict[str, str] = {
    "qpp_employeur": "Passifs:Cotisations-Employeur:QPP",
    "rqap_employeur": "Passifs:Cotisations-Employeur:RQAP",
    "ae_employeur": "Passifs:Cotisations-Employeur:AE",
    "fss": "Passifs:Cotisations-Employeur:FSS",
    "cnesst": "Passifs:Cotisations-Employeur:CNESST",
    "normes_travail": "Passifs:Cotisations-Employeur:Normes-Travail",
}

TOUS_COMPTES = {**MAPPAGE_COMPTES_RETENUES, **MAPPAGE_COMPTES_EMPLOYEUR}

# Cles pour lesquelles on suit aussi les gains cumulatifs (pour normes du travail)
CLES_GAINS = {"gains_bruts"}


def _cumuls_vides() -> dict[str, Decimal]:
    """Retourne un dictionnaire de cumuls initialise a zero."""
    cumuls = {cle: Decimal("0") for cle in TOUS_COMPTES}
    cumuls["gains_bruts"] = Decimal("0")
    return cumuls


def calculer_cumuls_depuis_transactions(
    entries: list,
    annee: int,
) -> dict[str, Decimal]:
    """Calcule les cumuls annuels depuis une liste d'entrees Beancount.

    Filtre les transactions avec le tag 'paie' pour l'annee donnee.
    Somme les postings par sous-compte pour deriver le YTD.

    Args:
        entries: Liste d'entrees Beancount (de loader.load_file).
        annee: Annee fiscale pour le filtrage.

    Returns:
        Dictionnaire {cle_cumul: montant_cumule} avec toutes les cles initialisees a 0.
    """
    cumuls = _cumuls_vides()

    # Index inverse: compte -> cle de cumul
    compte_vers_cle = {compte: cle for cle, compte in TOUS_COMPTES.items()}

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.date.year != annee:
            continue
        if not entry.tags or "paie" not in entry.tags:
            continue

        for posting in entry.postings:
            compte = posting.account

            # Accumulation par sous-compte de passif
            if compte in compte_vers_cle:
                cle = compte_vers_cle[compte]
                # Les passifs sont credites (negatifs) -- on veut le cumul positif
                montant = abs(posting.units.number)
                cumuls[cle] += montant

            # Suivi des gains bruts (pour normes du travail)
            if compte == "Depenses:Salaires:Brut":
                cumuls["gains_bruts"] += posting.units.number

    return cumuls


def obtenir_cumuls_annuels(
    chemin_ledger: str,
    annee: int,
) -> dict[str, Decimal]:
    """Extrait les cumuls annuels de cotisations depuis le fichier ledger.

    Derive les YTD directement des transactions existantes (source unique de verite).
    Cherche les transactions avec le tag 'paie' pour l'annee donnee.

    Args:
        chemin_ledger: Chemin vers le fichier principal beancount (ex: ledger/main.beancount).
        annee: Annee fiscale.

    Returns:
        Dictionnaire {cle_cumul: montant_cumule}.
        Retourne Decimal("0") pour toutes les cles si aucune transaction paie n'existe.
    """
    entries, errors, options = loader.load_file(chemin_ledger)
    return calculer_cumuls_depuis_transactions(entries, annee)
