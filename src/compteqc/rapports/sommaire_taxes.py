"""Sommaire TPS/TVQ pour le package CPA.

Genere un tableau par periode de declaration montrant TPS/TVQ
percues, CTI/RTI, et montants nets. Utilise les sommaires de
periode de compteqc.quebec.taxes.sommaire.
"""

from __future__ import annotations

from decimal import Decimal

from compteqc.quebec.taxes.sommaire import generer_sommaires_annuels
from compteqc.rapports.base import BaseReport


class SommaireTaxes(BaseReport):
    """Sommaire TPS/TVQ pour le package CPA.

    Affiche les periodes de declaration avec TPS/TVQ percues,
    payees (CTI/RTI), et nettes.
    """

    report_name = "sommaire_taxes"
    template_name = "sommaire_taxes.html"

    def __init__(
        self,
        entries: list,
        annee: int,
        entreprise: str = "",
        frequence: str = "trimestriel",
    ) -> None:
        super().__init__(entries, annee, entreprise)
        self.frequence = frequence

    def extract_data(self) -> dict:
        """Extrait les sommaires TPS/TVQ par periode."""
        sommaires = generer_sommaires_annuels(self.entries, self.annee, self.frequence)

        periodes: list[dict] = []
        totaux = {
            "tps_percue": Decimal("0"),
            "tps_payee": Decimal("0"),
            "tps_nette": Decimal("0"),
            "tvq_percue": Decimal("0"),
            "tvq_payee": Decimal("0"),
            "tvq_nette": Decimal("0"),
            "nb_transactions": 0,
        }

        for s in sommaires:
            periode = {
                "debut": s.debut,
                "fin": s.fin,
                "label": f"{s.debut} a {s.fin}",
                "tps_percue": self._q(s.tps_percue),
                "tps_payee": self._q(s.tps_payee),
                "tps_nette": self._q(s.tps_nette),
                "tvq_percue": self._q(s.tvq_percue),
                "tvq_payee": self._q(s.tvq_payee),
                "tvq_nette": self._q(s.tvq_nette),
                "nb_transactions": s.nb_transactions,
            }
            periodes.append(periode)

            totaux["tps_percue"] += s.tps_percue
            totaux["tps_payee"] += s.tps_payee
            totaux["tps_nette"] += s.tps_nette
            totaux["tvq_percue"] += s.tvq_percue
            totaux["tvq_payee"] += s.tvq_payee
            totaux["tvq_nette"] += s.tvq_nette
            totaux["nb_transactions"] += s.nb_transactions

        # Quantize totaux (except int)
        totaux_q = {
            k: self._q(v) if isinstance(v, Decimal) else v
            for k, v in totaux.items()
        }

        return {
            "periodes": periodes,
            "totaux": totaux_q,
            "frequence": self.frequence,
        }

    def csv_headers(self) -> list[str]:
        return [
            "Periode",
            "TPS Percue",
            "CTI (TPS Payee)",
            "TPS Nette",
            "TVQ Percue",
            "RTI (TVQ Payee)",
            "TVQ Nette",
            "Nb Transactions",
        ]

    def csv_rows(self) -> list[list]:
        d = self.data
        rows = []
        for p in d["periodes"]:
            rows.append([
                p["label"],
                str(p["tps_percue"]),
                str(p["tps_payee"]),
                str(p["tps_nette"]),
                str(p["tvq_percue"]),
                str(p["tvq_payee"]),
                str(p["tvq_nette"]),
                str(p["nb_transactions"]),
            ])
        t = d["totaux"]
        rows.append([
            "TOTAL",
            str(t["tps_percue"]),
            str(t["tps_payee"]),
            str(t["tps_nette"]),
            str(t["tvq_percue"]),
            str(t["tvq_payee"]),
            str(t["tvq_nette"]),
            str(t["nb_transactions"]),
        ])
        return rows
