"""Balance de verification (trial balance) avec colonnes Debit/Credit et codes GIFI."""

from __future__ import annotations

from decimal import Decimal

from compteqc.mcp.services import calculer_soldes
from compteqc.rapports.base import BaseReport
from compteqc.rapports.gifi_export import extract_gifi_map


class BalanceVerification(BaseReport):
    """Rapport de balance de verification avec codes GIFI.

    Affiche tous les comptes avec solde non-nul, groupes par categorie,
    avec colonnes Debit et Credit. Verifie que les totaux correspondent.
    """

    report_name = "balance_verification"
    template_name = "balance_verification.html"

    def extract_data(self) -> dict:
        """Extrait les soldes et les separe en debits/credits."""
        soldes = calculer_soldes(self.entries)
        gifi_map = extract_gifi_map(self.entries)

        categories = ["Actifs", "Passifs", "Capital", "Revenus", "Depenses"]
        lignes: list[dict] = []
        total_debit = Decimal("0")
        total_credit = Decimal("0")

        for categorie in categories:
            comptes_cat = {
                k: v for k, v in sorted(soldes.items())
                if k.startswith(categorie) and v != Decimal("0")
            }
            if not comptes_cat:
                continue

            for nom, montant in comptes_cat.items():
                gifi = gifi_map.get(nom, "")
                if montant > 0:
                    lignes.append({
                        "compte": nom,
                        "gifi": gifi,
                        "debit": self._q(montant),
                        "credit": Decimal("0"),
                    })
                    total_debit += montant
                else:
                    lignes.append({
                        "compte": nom,
                        "gifi": gifi,
                        "debit": Decimal("0"),
                        "credit": self._q(abs(montant)),
                    })
                    total_credit += abs(montant)

        return {
            "lignes": lignes,
            "total_debit": self._q(total_debit),
            "total_credit": self._q(total_credit),
            "equilibre": total_debit == total_credit,
        }

    def csv_headers(self) -> list[str]:
        return ["Compte", "GIFI", "Debit", "Credit"]

    def csv_rows(self) -> list[list]:
        d = self.data
        rows = []
        for ligne in d["lignes"]:
            rows.append([
                ligne["compte"],
                ligne["gifi"],
                str(self._q(ligne["debit"])) if ligne["debit"] else "",
                str(self._q(ligne["credit"])) if ligne["credit"] else "",
            ])
        rows.append(["TOTAL", "", str(d["total_debit"]), str(d["total_credit"])])
        return rows
