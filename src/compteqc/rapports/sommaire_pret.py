"""Sommaire du pret actionnaire pour le package CPA.

Genere un tableau de continuite du pret actionnaire montrant
chaque mouvement (avances/remboursements) et le solde courant.
Inclut une section sur les echeances s.15(2) ITA.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from compteqc.quebec.pret_actionnaire.suivi import obtenir_etat_pret
from compteqc.rapports.base import BaseReport


class SommairePret(BaseReport):
    """Sommaire du pret actionnaire pour le package CPA.

    Tableau de continuite avec avances, remboursements, solde.
    Section s.15(2) avec dates limites d'inclusion au revenu.
    """

    report_name = "sommaire_pret"
    template_name = "sommaire_pret.html"

    def __init__(
        self,
        entries: list,
        annee: int,
        entreprise: str = "",
        fin_exercice: datetime.date | None = None,
    ) -> None:
        super().__init__(entries, annee, entreprise)
        self.fin_exercice = fin_exercice or datetime.date(annee, 12, 31)

    def extract_data(self) -> dict:
        """Extrait l'etat du pret actionnaire."""
        etat = obtenir_etat_pret(self.entries, self.fin_exercice)

        mouvements: list[dict] = []
        solde_courant = Decimal("0")

        for m in etat.mouvements:
            solde_courant += m.montant
            mouvements.append({
                "date": m.date,
                "description": m.description,
                "type": m.type,
                "avance": self._q(m.montant) if m.montant > 0 else Decimal("0"),
                "remboursement": self._q(abs(m.montant)) if m.montant < 0 else Decimal("0"),
                "solde": self._q(solde_courant),
            })

        # Section s.15(2): date d'inclusion = fin_exercice + 1 an pour chaque avance ouverte
        avances_s152: list[dict] = []
        for avance in etat.avances_ouvertes:
            date_avance = avance["date"]
            # s.15(2) inclusion date: end of fiscal year following the year of the loan
            # Per 02-04 decision: fiscal year-end + 1 year (not loan date + 1 year)
            date_inclusion = datetime.date(
                self.fin_exercice.year + 1,
                self.fin_exercice.month,
                self.fin_exercice.day,
            )
            jours_restants = (date_inclusion - datetime.date.today()).days
            statut = "dans les delais" if jours_restants > 0 else "EN RETARD"

            avances_s152.append({
                "date_avance": date_avance,
                "montant_initial": self._q(avance["montant_initial"]),
                "solde_restant": self._q(avance["solde_restant"]),
                "date_inclusion": date_inclusion,
                "jours_restants": jours_restants,
                "statut": statut,
            })

        total_avances = sum(
            (m.montant for m in etat.mouvements if m.montant > 0),
            Decimal("0"),
        )
        total_remboursements = sum(
            (abs(m.montant) for m in etat.mouvements if m.montant < 0),
            Decimal("0"),
        )

        return {
            "mouvements": mouvements,
            "avances_s152": avances_s152,
            "solde_fin": self._q(etat.solde),
            "total_avances": self._q(total_avances),
            "total_remboursements": self._q(total_remboursements),
            "a_solde_non_nul": etat.solde != Decimal("0"),
        }

    def csv_headers(self) -> list[str]:
        return [
            "Date",
            "Description",
            "Type",
            "Avance",
            "Remboursement",
            "Solde",
        ]

    def csv_rows(self) -> list[list]:
        d = self.data
        rows = []
        for m in d["mouvements"]:
            rows.append([
                str(m["date"]),
                m["description"],
                m["type"],
                str(m["avance"]) if m["avance"] else "",
                str(m["remboursement"]) if m["remboursement"] else "",
                str(m["solde"]),
            ])
        rows.append([
            "TOTAL", "", "",
            str(d["total_avances"]),
            str(d["total_remboursements"]),
            str(d["solde_fin"]),
        ])
        return rows
