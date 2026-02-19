"""Extension Fava: Tableau de bord de la paie Quebec.

Affiche le cumulatif annuel (YTD) des cotisations de paie, retenues d'impot,
et le suivi des maximums annuels atteints.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase

from compteqc.quebec.paie.ytd import (
    MAPPAGE_COMPTES_EMPLOYEUR,
    MAPPAGE_COMPTES_RETENUES,
    calculer_cumuls_depuis_transactions,
)
from compteqc.quebec.rates import TAUX, obtenir_taux


# Descriptions et maximums par cotisation
# Structure: (cle_employe, cle_employeur, nom_affichage, max_employe_fn, max_employeur_fn)
COTISATIONS = [
    {
        "nom": "RRQ/QPP base",
        "cle_employe": "qpp_base_employe",
        "cle_employeur": "qpp_employeur",
        "max_employe": lambda t: t.qpp.max_base,
        "max_employeur": lambda t: t.qpp.max_base,
    },
    {
        "nom": "QPP supplementaire 1",
        "cle_employe": "qpp_supp1_employe",
        "cle_employeur": None,
        "max_employe": lambda t: t.qpp.max_supp1,
        "max_employeur": lambda _: Decimal("0"),
    },
    {
        "nom": "RQAP",
        "cle_employe": "rqap_employe",
        "cle_employeur": "rqap_employeur",
        "max_employe": lambda t: t.rqap.max_employe,
        "max_employeur": lambda t: t.rqap.max_employeur,
    },
    {
        "nom": "AE / Assurance-emploi",
        "cle_employe": "ae_employe",
        "cle_employeur": "ae_employeur",
        "max_employe": lambda t: t.ae.max_employe,
        "max_employeur": lambda t: t.ae.max_employeur,
    },
    {
        "nom": "FSS",
        "cle_employe": None,
        "cle_employeur": "fss",
        "max_employe": lambda _: Decimal("0"),
        "max_employeur": lambda _: Decimal("0"),  # FSS n'a pas de max fixe
    },
    {
        "nom": "CNESST",
        "cle_employe": None,
        "cle_employeur": "cnesst",
        "max_employe": lambda _: Decimal("0"),
        "max_employeur": lambda _: Decimal("0"),  # Pas de max annuel
    },
    {
        "nom": "Normes du travail",
        "cle_employe": None,
        "cle_employeur": "normes_travail",
        "max_employe": lambda _: Decimal("0"),
        "max_employeur": lambda _: Decimal("0"),  # Max indirect via gains
    },
]


class PaieQCExtension(FavaExtensionBase):
    """Tableau de bord paie Quebec avec cumulatif annuel."""

    report_title = "Paie Quebec"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._payroll_data: dict | None = None
        self._annee: int = datetime.date.today().year

    def after_load_file(self) -> None:
        """Recalcule les donnees de paie apres chargement du ledger."""
        self._annee = datetime.date.today().year
        entries = self.ledger.all_entries
        self._payroll_data = calculer_cumuls_depuis_transactions(entries, self._annee)

    def annee(self) -> int:
        """Retourne l'annee courante."""
        return self._annee

    def payroll_summary(self) -> list[dict]:
        """Retourne le sommaire des cotisations pour le template.

        Structure par cotisation:
        - nom: Nom de la cotisation
        - employe: Montant YTD employe
        - employeur: Montant YTD employeur
        - maximum_employe: Maximum annuel employe (0 si n'a pas de max)
        - maximum_employeur: Maximum annuel employeur (0 si n'a pas de max)
        - atteint_employe: True si le max employe est atteint
        - atteint_employeur: True si le max employeur est atteint
        """
        if not self._payroll_data:
            return []

        try:
            taux = obtenir_taux(self._annee)
        except ValueError:
            # Si les taux ne sont pas disponibles, retourner les cumuls sans max
            taux = None

        result = []
        cumuls = self._payroll_data

        for cot in COTISATIONS:
            employe = cumuls.get(cot["cle_employe"], Decimal("0")) if cot["cle_employe"] else Decimal("0")
            employeur = cumuls.get(cot["cle_employeur"], Decimal("0")) if cot["cle_employeur"] else Decimal("0")

            max_emp = cot["max_employe"](taux) if taux else Decimal("0")
            max_eur = cot["max_employeur"](taux) if taux else Decimal("0")

            result.append({
                "nom": cot["nom"],
                "employe": employe,
                "employeur": employeur,
                "maximum_employe": max_emp,
                "maximum_employeur": max_eur,
                "atteint_employe": max_emp > 0 and employe >= max_emp,
                "atteint_employeur": max_eur > 0 and employeur >= max_eur,
            })

        return result

    def retenues_impot(self) -> list[dict]:
        """Retourne les retenues d'impot YTD.

        Structure:
        - palier: "Federal" ou "Quebec"
        - montant: Montant retenu YTD
        """
        if not self._payroll_data:
            return []

        return [
            {
                "palier": "Federal",
                "montant": self._payroll_data.get("impot_federal", Decimal("0")),
            },
            {
                "palier": "Quebec",
                "montant": self._payroll_data.get("impot_quebec", Decimal("0")),
            },
        ]

    def totaux(self) -> dict:
        """Retourne les totaux pour le sommaire.

        - total_retenues_employe: Total des cotisations + impots employe
        - total_cotisations_employeur: Total des cotisations employeur
        - salaire_brut_ytd: Salaire brut YTD
        - salaire_net_ytd: Salaire net YTD (brut - retenues employe - impots)
        """
        if not self._payroll_data:
            return {
                "total_retenues_employe": Decimal("0"),
                "total_cotisations_employeur": Decimal("0"),
                "salaire_brut_ytd": Decimal("0"),
                "salaire_net_ytd": Decimal("0"),
            }

        cumuls = self._payroll_data

        # Retenues employe: cotisations + impots
        total_retenues = Decimal("0")
        for cle in MAPPAGE_COMPTES_RETENUES:
            total_retenues += cumuls.get(cle, Decimal("0"))

        # Cotisations employeur
        total_employeur = Decimal("0")
        for cle in MAPPAGE_COMPTES_EMPLOYEUR:
            total_employeur += cumuls.get(cle, Decimal("0"))

        salaire_brut = cumuls.get("gains_bruts", Decimal("0"))
        salaire_net = salaire_brut - total_retenues

        return {
            "total_retenues_employe": total_retenues,
            "total_cotisations_employeur": total_employeur,
            "salaire_brut_ytd": salaire_brut,
            "salaire_net_ytd": salaire_net,
        }
