"""Extension Fava: Tableau de bord -- page d'accueil avec KPIs et graphiques.

Calcule les indicateurs cles de performance, les revenus mensuels,
la repartition des depenses par categorie, et les transactions recentes.
Toutes les donnees sont recalculees dans after_load_file() pour rester
synchronisees avec le ledger.
"""

from __future__ import annotations

import datetime
import json
import logging
from decimal import Decimal

from beancount.core import data
from fava.core import FavaLedger
from fava.ext import FavaExtensionBase

from compteqc.mcp.services import calculer_soldes, lister_pending

logger = logging.getLogger(__name__)

MOIS_FR = [
    "Jan", "Fev", "Mar", "Avr", "Mai", "Jun",
    "Jul", "Aou", "Sep", "Oct", "Nov", "Dec",
]

QUEBEC_PALETTE = [
    "#003DA5", "#1A5BBF", "#4A7FD4", "#7BA3E0",
    "#16A34A", "#EA580C", "#D97706", "#64748B",
]


class TableauBordExtension(FavaExtensionBase):
    """Tableau de bord avec KPIs, graphiques et transactions recentes."""

    report_title = "Tableau de bord"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._kpis: dict = {}
        self._revenus_mensuels: dict = {}
        self._depenses_categories: dict = {}
        self._transactions_recentes: list[dict] = []

    def after_load_file(self) -> None:
        """Recalcule toutes les donnees du tableau de bord."""
        try:
            self._compute_kpis()
            self._compute_revenus_mensuels()
            self._compute_depenses_categories()
            self._compute_transactions_recentes()
        except Exception:
            logger.exception("Erreur lors du calcul du tableau de bord")

    # ------------------------------------------------------------------
    # KPIs
    # ------------------------------------------------------------------

    def _compute_kpis(self) -> None:
        """Calcule les 5 KPIs: revenus, depenses, resultat net, taxes dues, pending."""
        annee = datetime.date.today().year
        debut = datetime.date(annee, 1, 1)
        fin = datetime.date.today()

        revenus = Decimal("0")
        depenses = Decimal("0")

        for entry in self.ledger.all_entries:
            if not isinstance(entry, data.Transaction):
                continue
            if entry.date < debut or entry.date > fin:
                continue
            for posting in entry.postings:
                if posting.units is None:
                    continue
                if posting.account.startswith("Revenus"):
                    # Negate: Beancount credits are negative
                    revenus -= posting.units.number
                elif posting.account.startswith("Depenses"):
                    depenses += posting.units.number

        # Pending count
        pending = lister_pending(self.ledger.all_entries)

        # Tax owing (GST/QST net remittance)
        soldes = calculer_soldes(self.ledger.all_entries)
        tps_percue = abs(soldes.get("Passifs:TPS-Percue", Decimal("0")))
        tvq_percue = abs(soldes.get("Passifs:TVQ-Percue", Decimal("0")))
        tps_payee = soldes.get("Actifs:TPS-Payee", Decimal("0"))
        tvq_payee = soldes.get("Actifs:TVQ-Payee", Decimal("0"))
        taxes_dues = (tps_percue + tvq_percue) - (tps_payee + tvq_payee)

        self._kpis = {
            "revenus_ytd": revenus,
            "depenses_ytd": depenses,
            "resultat_net": revenus - depenses,
            "taxes_dues": taxes_dues,
            "pending_count": len(pending),
        }

    def kpis(self) -> dict:
        """Retourne les KPIs du tableau de bord."""
        return self._kpis

    def annee(self) -> int:
        """Retourne l'annee courante (utilise par le template)."""
        return datetime.date.today().year

    # ------------------------------------------------------------------
    # Stubs for remaining compute methods (implemented in Task 2)
    # ------------------------------------------------------------------

    def _compute_revenus_mensuels(self) -> None:
        """Placeholder -- implemented in Task 2."""

    def _compute_depenses_categories(self) -> None:
        """Placeholder -- implemented in Task 2."""

    def _compute_transactions_recentes(self) -> None:
        """Placeholder -- implemented in Task 2."""
