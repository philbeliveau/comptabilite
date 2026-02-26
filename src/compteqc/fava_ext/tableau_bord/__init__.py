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
    # Revenus mensuels (line chart)
    # ------------------------------------------------------------------

    def _compute_revenus_mensuels(self) -> None:
        """Calcule les revenus mensuels pour le graphique en ligne."""
        annee = datetime.date.today().year
        mensuels = [Decimal("0")] * 12

        for entry in self.ledger.all_entries:
            if not isinstance(entry, data.Transaction):
                continue
            if entry.date.year != annee:
                continue
            for posting in entry.postings:
                if posting.units is None:
                    continue
                if posting.account.startswith("Revenus"):
                    # Negate: credits are negative in Beancount
                    mensuels[entry.date.month - 1] -= posting.units.number

        mois_courant = datetime.date.today().month
        self._revenus_mensuels = {
            "labels": MOIS_FR[:mois_courant],
            "datasets": [{
                "label": "Revenus",
                "data": [float(m) for m in mensuels[:mois_courant]],
            }],
        }

    def revenus_mensuels(self) -> dict:
        """Retourne les donnees de revenus mensuels."""
        return self._revenus_mensuels

    def revenus_mensuels_json(self) -> str:
        """Retourne les revenus mensuels en JSON pour data-chart."""
        return json.dumps(self._revenus_mensuels)

    # ------------------------------------------------------------------
    # Depenses par categorie (doughnut chart)
    # ------------------------------------------------------------------

    def _compute_depenses_categories(self) -> None:
        """Calcule la repartition des depenses par categorie de second niveau."""
        annee = datetime.date.today().year
        categories: dict[str, Decimal] = {}

        for entry in self.ledger.all_entries:
            if not isinstance(entry, data.Transaction):
                continue
            if entry.date.year != annee:
                continue
            for posting in entry.postings:
                if posting.units is None:
                    continue
                if posting.account.startswith("Depenses:"):
                    parts = posting.account.split(":")
                    cat = parts[1] if len(parts) >= 2 else "Autres"
                    categories[cat] = categories.get(cat, Decimal("0")) + posting.units.number

        if not categories:
            self._depenses_categories = {
                "labels": [],
                "datasets": [{"data": [], "backgroundColor": []}],
            }
            return

        # Sort descending, top 6 + Autres bucket
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_cats) > 6:
            top6 = sorted_cats[:6]
            autres_total = sum(v for _, v in sorted_cats[6:])
            labels = [c for c, _ in top6] + ["Autres"]
            values = [float(v) for _, v in top6] + [float(autres_total)]
        else:
            labels = [c for c, _ in sorted_cats]
            values = [float(v) for _, v in sorted_cats]

        self._depenses_categories = {
            "labels": labels,
            "datasets": [{
                "data": values,
                "backgroundColor": QUEBEC_PALETTE[:len(labels)],
            }],
        }

    def depenses_categories(self) -> dict:
        """Retourne les donnees de depenses par categorie."""
        return self._depenses_categories

    def depenses_categories_json(self) -> str:
        """Retourne les depenses par categorie en JSON pour data-chart."""
        return json.dumps(self._depenses_categories)

    # ------------------------------------------------------------------
    # Transactions recentes
    # ------------------------------------------------------------------

    def _compute_transactions_recentes(self) -> None:
        """Calcule les 10 transactions les plus recentes."""
        transactions = [
            e for e in self.ledger.all_entries
            if isinstance(e, data.Transaction)
        ]
        transactions.sort(key=lambda e: e.date, reverse=True)
        transactions = transactions[:10]

        # Import hash_entry for Fava context linking
        try:
            from fava.beans.funcs import hash_entry
        except ImportError:
            try:
                from beancount.core.compare import hash_entry
            except ImportError:
                def hash_entry(entry: object) -> str:
                    return ""

        result = []
        for txn in transactions:
            # Montant = sum of positive posting amounts (debit side)
            montant = Decimal("0")
            for p in txn.postings:
                if p.units is not None and p.units.number > 0:
                    montant += p.units.number

            # Status badge
            tags = txn.tags or frozenset()
            if "pending" in tags:
                statut = "pending"
            elif txn.flag == "!":
                statut = "attention"
            else:
                statut = "ok"

            result.append({
                "date": str(txn.date),
                "payee": txn.payee or "",
                "narration": txn.narration or "",
                "montant": montant,
                "statut": statut,
                "entry_hash": hash_entry(txn),
            })

        self._transactions_recentes = result

    def transactions_recentes(self) -> list[dict]:
        """Retourne les 10 transactions les plus recentes."""
        return self._transactions_recentes
