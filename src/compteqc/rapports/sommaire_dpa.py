"""Sommaire DPA (deduction pour amortissement) pour le package CPA.

Genere un tableau par classe CCA montrant FNACC d'ouverture, acquisitions,
dispositions, regle du demi-taux, DPA reclamee, et FNACC de fermeture.
Inclut un sous-tableau d'actifs par classe.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from compteqc.quebec.dpa.calcul import PoolDPA, construire_pools
from compteqc.quebec.dpa.classes import CLASSES_DPA
from compteqc.quebec.dpa.registre import RegistreActifs
from compteqc.rapports.base import BaseReport


class SommaireDPA(BaseReport):
    """Sommaire DPA pour le package CPA.

    Affiche les pools DPA par classe avec detail des actifs.
    Lit le registre d'actifs depuis un fichier YAML.
    """

    report_name = "sommaire_dpa"
    template_name = "sommaire_dpa.html"

    def __init__(
        self,
        entries: list,
        annee: int,
        entreprise: str = "",
        chemin_actifs: str | Path = "data/actifs.yaml",
        ucc_precedent: dict[int, Decimal] | None = None,
    ) -> None:
        super().__init__(entries, annee, entreprise)
        self.chemin_actifs = Path(chemin_actifs)
        self.ucc_precedent = ucc_precedent or {}

    def extract_data(self) -> dict:
        """Extrait les pools DPA et les details des actifs."""
        registre = RegistreActifs(self.chemin_actifs)
        actifs = registre.charger()

        pools = construire_pools(actifs, self.ucc_precedent, self.annee)

        classes_data: list[dict] = []
        total_ucc_ouverture = Decimal("0")
        total_acquisitions = Decimal("0")
        total_dispositions = Decimal("0")
        total_dpa = Decimal("0")
        total_ucc_fermeture = Decimal("0")

        for classe_num in sorted(pools.keys()):
            pool = pools[classe_num]
            dpa = pool.calculer_dpa()
            info_classe = CLASSES_DPA.get(classe_num, {})

            # Actifs dans cette classe
            actifs_classe = [
                {
                    "description": a.description,
                    "date_acquisition": a.date_acquisition,
                    "cout": self._q(a.cout),
                }
                for a in actifs
                if a.classe == classe_num and a.date_acquisition.year <= self.annee
            ]

            # Demi-taux applicable?
            demi_taux = pool.additions_nettes > 0

            classes_data.append({
                "classe": classe_num,
                "description": info_classe.get("description", ""),
                "taux": info_classe.get("taux", Decimal("0")),
                "ucc_ouverture": self._q(pool.ucc_ouverture),
                "acquisitions": self._q(pool.acquisitions),
                "dispositions": self._q(pool.dispositions),
                "demi_taux": demi_taux,
                "dpa": self._q(dpa),
                "ucc_fermeture": self._q(pool.ucc_fermeture),
                "actifs": actifs_classe,
            })

            total_ucc_ouverture += pool.ucc_ouverture
            total_acquisitions += pool.acquisitions
            total_dispositions += pool.dispositions
            total_dpa += dpa
            total_ucc_fermeture += pool.ucc_fermeture

        return {
            "classes": classes_data,
            "total_ucc_ouverture": self._q(total_ucc_ouverture),
            "total_acquisitions": self._q(total_acquisitions),
            "total_dispositions": self._q(total_dispositions),
            "total_dpa": self._q(total_dpa),
            "total_ucc_fermeture": self._q(total_ucc_fermeture),
        }

    def csv_headers(self) -> list[str]:
        return [
            "Classe",
            "Description",
            "Taux",
            "FNACC Ouverture",
            "Acquisitions",
            "Dispositions",
            "Demi-taux",
            "DPA Reclamee",
            "FNACC Fermeture",
        ]

    def csv_rows(self) -> list[list]:
        d = self.data
        rows = []
        for c in d["classes"]:
            rows.append([
                str(c["classe"]),
                c["description"],
                str(c["taux"]),
                str(c["ucc_ouverture"]),
                str(c["acquisitions"]),
                str(c["dispositions"]),
                "Oui" if c["demi_taux"] else "Non",
                str(c["dpa"]),
                str(c["ucc_fermeture"]),
            ])
        rows.append([
            "TOTAL", "", "",
            str(d["total_ucc_ouverture"]),
            str(d["total_acquisitions"]),
            str(d["total_dispositions"]),
            "",
            str(d["total_dpa"]),
            str(d["total_ucc_fermeture"]),
        ])
        return rows
