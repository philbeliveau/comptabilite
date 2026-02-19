"""Extension Fava: Cedule de deduction pour amortissement (DPA/CCA).

Affiche le tableau DPA par classe avec FNACC d'ouverture/fermeture,
acquisitions, dispositions, et DPA reclamee.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase

from compteqc.quebec.dpa.calcul import PoolDPA, construire_pools
from compteqc.quebec.dpa.classes import CLASSES_DPA
from compteqc.quebec.dpa.registre import RegistreActifs


# Classes DPA a afficher (toujours dans l'ordre)
CLASSES_AFFICHEES = [8, 10, 12, 50, 54]


class DpaQCExtension(FavaExtensionBase):
    """Cedule DPA/CCA par classe d'actif."""

    report_title = "DPA/CCA"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._pools: dict[int, PoolDPA] = {}
        self._annee: int = datetime.date.today().year
        self._registre_path: str | None = config

    def after_load_file(self) -> None:
        """Recalcule les pools DPA apres chargement du ledger."""
        self._annee = datetime.date.today().year
        self._pools = {}

        # Tenter de charger le registre d'actifs
        try:
            if self._registre_path:
                registre = RegistreActifs(self._registre_path)
                registre.charger()
            else:
                # Chemin par defaut relatif au ledger
                from pathlib import Path

                ledger_dir = Path(self.ledger.beancount_file_path).parent
                registre_path = ledger_dir / "actifs.yaml"
                registre = RegistreActifs(str(registre_path))
                registre.charger()
        except Exception:
            registre = RegistreActifs()
            registre._actifs = []

        # Construire les pools avec UCC d'ouverture a zero (premiere annee)
        # Dans une version future, l'UCC precedent proviendra du ledger
        ucc_precedent: dict[int, Decimal] = {}
        self._pools = construire_pools(registre.actifs, ucc_precedent, self._annee)

    def annee(self) -> int:
        """Retourne l'annee courante."""
        return self._annee

    def cca_schedule(self) -> list[dict]:
        """Retourne la cedule DPA pour le template.

        Structure par classe:
        - classe: Numero de classe
        - description: Description de la classe
        - fnacc_debut: FNACC d'ouverture (UCC debut d'annee)
        - acquisitions: Acquisitions de l'annee
        - dispositions: Dispositions de l'annee
        - dpa_reclamee: DPA reclamee
        - fnacc_fin: FNACC de fermeture
        """
        result = []
        for classe in CLASSES_AFFICHEES:
            if classe in self._pools:
                pool = self._pools[classe]
                result.append({
                    "classe": classe,
                    "description": CLASSES_DPA[classe]["description"],
                    "fnacc_debut": pool.ucc_ouverture,
                    "acquisitions": pool.acquisitions,
                    "dispositions": pool.dispositions,
                    "dpa_reclamee": pool.calculer_dpa(),
                    "fnacc_fin": pool.ucc_fermeture,
                })
            else:
                # Classe sans activite -- afficher une ligne vide
                result.append({
                    "classe": classe,
                    "description": CLASSES_DPA[classe]["description"],
                    "fnacc_debut": Decimal("0"),
                    "acquisitions": Decimal("0"),
                    "dispositions": Decimal("0"),
                    "dpa_reclamee": Decimal("0"),
                    "fnacc_fin": Decimal("0"),
                })
        return result

    def totaux(self) -> dict:
        """Retourne les totaux de la cedule DPA."""
        schedule = self.cca_schedule()
        return {
            "fnacc_debut": sum(r["fnacc_debut"] for r in schedule),
            "acquisitions": sum(r["acquisitions"] for r in schedule),
            "dispositions": sum(r["dispositions"] for r in schedule),
            "dpa_reclamee": sum(r["dpa_reclamee"] for r in schedule),
            "fnacc_fin": sum(r["fnacc_fin"] for r in schedule),
        }
