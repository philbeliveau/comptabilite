"""Sommaire de paie pour le package CPA.

Genere un tableau detaille de toutes les periodes de paie de l'exercice:
brut, retenues (QPP, RQAP, AE, impots), cotisations employeur, et net.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from beancount.core import data

from compteqc.rapports.base import BaseReport

# Comptes de paie dans le plan comptable (Phase 2 decision: per-deduction sub-accounts)
COMPTE_SALAIRE_BRUT = "Depenses:Salaires:Brut"
COMPTES_RETENUES = {
    "qpp_base": "Passifs:Retenues:QPP-Base",
    "qpp_supp1": "Passifs:Retenues:QPP-Supp1",
    "qpp_supp2": "Passifs:Retenues:QPP-Supp2",
    "rqap": "Passifs:Retenues:RQAP",
    "ae": "Passifs:Retenues:AE",
    "impot_federal": "Passifs:Retenues:Impot-Federal",
    "impot_quebec": "Passifs:Retenues:Impot-Quebec",
}
COMPTES_COTISATIONS = {
    "qpp_employeur": "Depenses:Salaires:QPP-Employeur",
    "rqap_employeur": "Depenses:Salaires:RQAP-Employeur",
    "ae_employeur": "Depenses:Salaires:AE-Employeur",
    "fss": "Depenses:Salaires:FSS",
    "cnesst": "Depenses:Salaires:CNESST",
    "normes_travail": "Depenses:Salaires:Normes-Travail",
}


def _extraire_montant(posting: data.Posting) -> Decimal:
    """Extrait le montant d'un posting comme Decimal."""
    if posting.units is None:
        return Decimal("0")
    return Decimal(str(posting.units.number))


class SommairePaie(BaseReport):
    """Sommaire de paie pour le package CPA.

    Tableau: une ligne par transaction de paie (tag 'paie' ou
    contenant un posting au brut). Colonnes: date, brut, chaque
    retenue, net, cotisations employeur.
    """

    report_name = "sommaire_paie"
    template_name = "sommaire_paie.html"

    def extract_data(self) -> dict:
        """Extrait les donnees de paie du ledger par transaction."""
        periodes: list[dict] = []
        totaux = {
            "brut": Decimal("0"),
            "qpp_base": Decimal("0"),
            "qpp_supp1": Decimal("0"),
            "qpp_supp2": Decimal("0"),
            "rqap": Decimal("0"),
            "ae": Decimal("0"),
            "impot_federal": Decimal("0"),
            "impot_quebec": Decimal("0"),
            "total_retenues": Decimal("0"),
            "net": Decimal("0"),
            "qpp_employeur": Decimal("0"),
            "rqap_employeur": Decimal("0"),
            "ae_employeur": Decimal("0"),
            "fss": Decimal("0"),
            "cnesst": Decimal("0"),
            "normes_travail": Decimal("0"),
            "total_cotisations": Decimal("0"),
        }

        debut = datetime.date(self.annee, 1, 1)
        fin = datetime.date(self.annee, 12, 31)

        for entry in self.entries:
            if not isinstance(entry, data.Transaction):
                continue
            if entry.date < debut or entry.date > fin:
                continue

            # Identifier les transactions de paie: tag "paie" ou posting au brut
            est_paie = False
            if entry.tags and "paie" in entry.tags:
                est_paie = True
            else:
                for posting in entry.postings:
                    if posting.account == COMPTE_SALAIRE_BRUT:
                        est_paie = True
                        break

            if not est_paie:
                continue

            # Extraire les montants par compte
            ligne: dict[str, Decimal | datetime.date] = {"date": entry.date}
            brut = Decimal("0")
            retenues: dict[str, Decimal] = {k: Decimal("0") for k in COMPTES_RETENUES}
            cotisations: dict[str, Decimal] = {k: Decimal("0") for k in COMPTES_COTISATIONS}

            for posting in entry.postings:
                montant = _extraire_montant(posting)
                if posting.account == COMPTE_SALAIRE_BRUT:
                    brut = montant
                else:
                    for cle, compte in COMPTES_RETENUES.items():
                        if posting.account == compte:
                            retenues[cle] = abs(montant)
                            break
                    for cle, compte in COMPTES_COTISATIONS.items():
                        if posting.account == compte:
                            cotisations[cle] = abs(montant)
                            break

            total_ret = sum(retenues.values())
            net = brut - total_ret
            total_cot = sum(cotisations.values())

            ligne["brut"] = self._q(brut)
            for cle, val in retenues.items():
                ligne[cle] = self._q(val)
            ligne["total_retenues"] = self._q(total_ret)
            ligne["net"] = self._q(net)
            for cle, val in cotisations.items():
                ligne[cle] = self._q(val)
            ligne["total_cotisations"] = self._q(total_cot)

            periodes.append(ligne)

            # Accumuler totaux
            totaux["brut"] += brut
            for cle in retenues:
                totaux[cle] += retenues[cle]
            totaux["total_retenues"] += total_ret
            totaux["net"] += net
            for cle in cotisations:
                totaux[cle] += cotisations[cle]
            totaux["total_cotisations"] += total_cot

        # Quantize totaux
        totaux = {k: self._q(v) for k, v in totaux.items()}

        return {
            "periodes": periodes,
            "totaux": totaux,
            "nb_periodes": len(periodes),
        }

    def csv_headers(self) -> list[str]:
        return [
            "Date",
            "Brut",
            "QPP Base",
            "QPP Supp1",
            "QPP Supp2",
            "RQAP",
            "AE",
            "Impot Federal",
            "Impot Quebec",
            "Total Retenues",
            "Net",
            "QPP Employeur",
            "RQAP Employeur",
            "AE Employeur",
            "FSS",
            "CNESST",
            "Normes Travail",
            "Total Cotisations",
        ]

    def csv_rows(self) -> list[list]:
        d = self.data
        rows = []
        champs = [
            "brut", "qpp_base", "qpp_supp1", "qpp_supp2", "rqap", "ae",
            "impot_federal", "impot_quebec", "total_retenues", "net",
            "qpp_employeur", "rqap_employeur", "ae_employeur", "fss",
            "cnesst", "normes_travail", "total_cotisations",
        ]
        for p in d["periodes"]:
            rows.append([str(p["date"])] + [str(p[c]) for c in champs])
        # Total row
        rows.append(["TOTAL"] + [str(d["totaux"][c]) for c in champs])
        return rows
