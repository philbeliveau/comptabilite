"""Bilan (balance sheet) avec codes GIFI et verification de l'equation comptable."""

from __future__ import annotations

from decimal import Decimal

from compteqc.mcp.services import calculer_soldes
from compteqc.rapports.base import BaseReport
from compteqc.rapports.gifi_export import extract_gifi_map


class Bilan(BaseReport):
    """Rapport du bilan avec verification Actifs = Passifs + Capitaux propres.

    Le resultat net (Revenus - Depenses) est inclus sous capitaux propres.
    """

    report_name = "bilan"
    template_name = "bilan.html"

    def extract_data(self) -> dict:
        """Extrait actifs, passifs, capitaux propres et resultat net."""
        soldes = calculer_soldes(self.entries)
        gifi_map = extract_gifi_map(self.entries)

        actifs: dict[str, Decimal] = {}
        passifs: dict[str, Decimal] = {}
        capitaux: dict[str, Decimal] = {}

        for acct, montant in soldes.items():
            if montant == Decimal("0"):
                continue
            if acct.startswith("Actifs"):
                actifs[acct] = montant
            elif acct.startswith("Passifs"):
                passifs[acct] = montant
            elif acct.startswith("Capital"):
                capitaux[acct] = montant

        # Resultat net = Revenus (inverses) - Depenses
        resultat_net = Decimal("0")
        for acct, montant in soldes.items():
            if acct.startswith("Revenus"):
                resultat_net -= montant  # credits negatifs -> -(-x) = +x
            elif acct.startswith("Depenses"):
                resultat_net -= montant  # debits positifs -> -(+x) = -x

        total_actifs = self._q(sum(actifs.values(), Decimal("0")))
        total_passifs = self._q(sum((abs(v) for v in passifs.values()), Decimal("0")))
        total_capitaux = self._q(sum((abs(v) for v in capitaux.values()), Decimal("0")) + resultat_net)
        total_passifs_capitaux = self._q(total_passifs + total_capitaux)

        lignes_actifs = [
            {"compte": k, "gifi": gifi_map.get(k, ""), "montant": self._q(v)}
            for k, v in sorted(actifs.items())
        ]
        lignes_passifs = [
            {"compte": k, "gifi": gifi_map.get(k, ""), "montant": self._q(abs(v))}
            for k, v in sorted(passifs.items())
        ]
        lignes_capitaux = [
            {"compte": k, "gifi": gifi_map.get(k, ""), "montant": self._q(abs(v))}
            for k, v in sorted(capitaux.items())
        ]

        return {
            "lignes_actifs": lignes_actifs,
            "lignes_passifs": lignes_passifs,
            "lignes_capitaux": lignes_capitaux,
            "resultat_net": self._q(resultat_net),
            "total_actifs": total_actifs,
            "total_passifs": total_passifs,
            "total_capitaux": total_capitaux,
            "total_passifs_capitaux": total_passifs_capitaux,
            "equilibre": total_actifs == total_passifs_capitaux,
        }

    def csv_headers(self) -> list[str]:
        return ["Compte", "GIFI", "Montant"]

    def csv_rows(self) -> list[list]:
        d = self.data
        rows = [["--- ACTIFS ---", "", ""]]
        for ligne in d["lignes_actifs"]:
            rows.append([ligne["compte"], ligne["gifi"], str(ligne["montant"])])
        rows.append(["Total actifs", "", str(d["total_actifs"])])

        rows.append(["--- PASSIFS ---", "", ""])
        for ligne in d["lignes_passifs"]:
            rows.append([ligne["compte"], ligne["gifi"], str(ligne["montant"])])
        rows.append(["Total passifs", "", str(d["total_passifs"])])

        rows.append(["--- CAPITAUX PROPRES ---", "", ""])
        for ligne in d["lignes_capitaux"]:
            rows.append([ligne["compte"], ligne["gifi"], str(ligne["montant"])])
        if d["resultat_net"] != Decimal("0"):
            rows.append(["Resultat net de l'exercice", "", str(d["resultat_net"])])
        rows.append(["Total capitaux propres", "", str(d["total_capitaux"])])

        rows.append(["TOTAL PASSIFS + CAPITAUX", "", str(d["total_passifs_capitaux"])])
        return rows
