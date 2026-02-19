"""Extension Fava: Suivi TPS/TVQ par periode de production.

Affiche les sommaires TPS/TVQ par periode de declaration (annuel ou trimestriel)
avec CTI, RTI, et remise nette.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase

from compteqc.quebec.taxes.sommaire import SommairePeriode, generer_sommaires_annuels


class TaxesQCExtension(FavaExtensionBase):
    """Suivi TPS/TVQ par periode de production."""

    report_title = "TPS/TVQ"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._sommaires: list[SommairePeriode] = []
        self._annee: int = datetime.date.today().year
        # Defaut: annuel. Peut etre configure via le config string.
        self._frequence: str = "annuel"
        if config and config.strip() in ("annuel", "trimestriel"):
            self._frequence = config.strip()

    def after_load_file(self) -> None:
        """Recalcule les sommaires TPS/TVQ apres chargement du ledger."""
        self._annee = datetime.date.today().year
        entries = self.ledger.all_entries
        self._sommaires = generer_sommaires_annuels(entries, self._annee, self._frequence)

    def annee(self) -> int:
        """Retourne l'annee courante."""
        return self._annee

    def frequence(self) -> str:
        """Retourne la frequence de declaration."""
        return self._frequence

    def tax_summary(self) -> list[dict]:
        """Retourne les sommaires par periode pour le template.

        Structure par periode:
        - periode: Libelle de la periode (ex: "2026-01-01 au 2026-12-31")
        - tps_percue: TPS percue sur revenus
        - tvq_percue: TVQ percue sur revenus
        - ctis_tps: Credits de taxe sur intrants (TPS payee sur depenses)
        - rtis_tvq: Remboursements de taxe sur intrants (TVQ payee sur depenses)
        - remise_nette_tps: TPS percue - CTI (positif = du au gouvernement)
        - remise_nette_tvq: TVQ percue - RTI (positif = du au gouvernement)
        - nb_transactions: Nombre de transactions dans la periode
        """
        result = []
        for s in self._sommaires:
            result.append({
                "periode": f"{s.debut.isoformat()} au {s.fin.isoformat()}",
                "tps_percue": s.tps_percue,
                "tvq_percue": s.tvq_percue,
                "ctis_tps": s.tps_payee,
                "rtis_tvq": s.tvq_payee,
                "remise_nette_tps": s.tps_nette,
                "remise_nette_tvq": s.tvq_nette,
                "nb_transactions": s.nb_transactions,
            })
        return result

    def totaux_annuels(self) -> dict:
        """Retourne les totaux annuels agrege de toutes les periodes."""
        total = {
            "tps_percue": Decimal("0"),
            "tvq_percue": Decimal("0"),
            "ctis_tps": Decimal("0"),
            "rtis_tvq": Decimal("0"),
            "remise_nette_tps": Decimal("0"),
            "remise_nette_tvq": Decimal("0"),
            "nb_transactions": 0,
        }
        for s in self._sommaires:
            total["tps_percue"] += s.tps_percue
            total["tvq_percue"] += s.tvq_percue
            total["ctis_tps"] += s.tps_payee
            total["rtis_tvq"] += s.tvq_payee
            total["remise_nette_tps"] += s.tps_nette
            total["remise_nette_tvq"] += s.tvq_nette
            total["nb_transactions"] += s.nb_transactions
        return total
