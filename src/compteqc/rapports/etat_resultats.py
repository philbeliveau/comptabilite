"""Etat des resultats (income statement) avec codes GIFI."""

from __future__ import annotations

from decimal import Decimal

from beancount.core import data

from compteqc.rapports.base import BaseReport
from compteqc.rapports.gifi_export import extract_gifi_map


class EtatResultats(BaseReport):
    """Rapport de l'etat des resultats (revenus - depenses = resultat net).

    Les revenus Beancount sont negatifs (credits) et sont affiches en positif.
    Les depenses Beancount sont positives (debits).
    """

    report_name = "etat_resultats"
    template_name = "etat_resultats.html"

    def extract_data(self) -> dict:
        """Extrait revenus et depenses des transactions."""
        gifi_map = extract_gifi_map(self.entries)
        revenus: dict[str, Decimal] = {}
        depenses: dict[str, Decimal] = {}

        for entry in self.entries:
            if not isinstance(entry, data.Transaction):
                continue
            for posting in entry.postings:
                if posting.units is None:
                    continue
                acct = posting.account
                montant = posting.units.number
                if acct.startswith("Revenus"):
                    revenus[acct] = revenus.get(acct, Decimal("0")) + montant
                elif acct.startswith("Depenses"):
                    depenses[acct] = depenses.get(acct, Decimal("0")) + montant

        # Revenus en positif (inverser le signe beancount)
        lignes_revenus = [
            {"compte": k, "gifi": gifi_map.get(k, ""), "montant": self._q(-v)}
            for k, v in sorted(revenus.items())
        ]
        total_revenus = self._q(sum((-v for v in revenus.values()), Decimal("0")))

        lignes_depenses = [
            {"compte": k, "gifi": gifi_map.get(k, ""), "montant": self._q(v)}
            for k, v in sorted(depenses.items())
        ]
        total_depenses = self._q(sum(depenses.values(), Decimal("0")))

        resultat_net = self._q(total_revenus - total_depenses)

        return {
            "lignes_revenus": lignes_revenus,
            "lignes_depenses": lignes_depenses,
            "total_revenus": total_revenus,
            "total_depenses": total_depenses,
            "resultat_net": resultat_net,
        }

    def csv_headers(self) -> list[str]:
        return ["Compte", "GIFI", "Montant"]

    def csv_rows(self) -> list[list]:
        d = self.data
        rows = [["--- REVENUS ---", "", ""]]
        for ligne in d["lignes_revenus"]:
            rows.append([ligne["compte"], ligne["gifi"], str(ligne["montant"])])
        rows.append(["Total revenus", "", str(d["total_revenus"])])
        rows.append(["--- DEPENSES ---", "", ""])
        for ligne in d["lignes_depenses"]:
            rows.append([ligne["compte"], ligne["gifi"], str(ligne["montant"])])
        rows.append(["Total depenses", "", str(d["total_depenses"])])
        rows.append(["RESULTAT NET", "", str(d["resultat_net"])])
        return rows
