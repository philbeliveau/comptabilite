"""Registre de factures fournisseurs avec persistance YAML.

Stocke les factures fournisseurs dans un fichier YAML avec numerotation sequentielle FOUR-YYYY-NNN.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import yaml

from compteqc.fournisseurs.modeles import FactureFournisseur, BillStatus


class RegistreFournisseurs:
    """Registre de factures fournisseurs persistant en YAML."""

    def __init__(self, chemin: Path | None = None) -> None:
        self.chemin = chemin or Path("ledger/fournisseurs/registre.yaml")
        self._factures: list[FactureFournisseur] = []
        self._charger()

    def _charger(self) -> None:
        """Charge les factures fournisseurs depuis le fichier YAML."""
        if self.chemin.exists():
            with open(self.chemin, encoding="utf-8") as f:
                donnees = yaml.safe_load(f)
            if donnees and isinstance(donnees, list):
                self._factures = [FactureFournisseur.model_validate(d) for d in donnees]

    def _sauvegarder(self) -> None:
        """Sauvegarde les factures fournisseurs dans le fichier YAML."""
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        donnees = [f.model_dump(mode="json") for f in self._factures]
        with open(self.chemin, "w", encoding="utf-8") as f:
            yaml.dump(donnees, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def ajouter(self, facture: FactureFournisseur) -> None:
        """Ajoute une facture fournisseur. Leve ValueError si le numero interne existe deja."""
        if any(f.numero_interne == facture.numero_interne for f in self._factures):
            raise ValueError(f"Facture fournisseur {facture.numero_interne} existe deja dans le registre")
        self._factures.append(facture)
        self._sauvegarder()

    def obtenir(self, numero_interne: str) -> FactureFournisseur | None:
        """Retourne une facture fournisseur par son numero interne, ou None."""
        for f in self._factures:
            if f.numero_interne == numero_interne:
                return f
        return None

    def lister(self, statut: BillStatus | None = None) -> list[FactureFournisseur]:
        """Liste les factures fournisseurs, optionnellement filtrees par statut."""
        if statut is None:
            return list(self._factures)
        return [f for f in self._factures if f.statut == statut]

    def lister_impayees(self) -> list[FactureFournisseur]:
        """Liste les factures fournisseurs non payees (RECEIVED, APPROVED, PARTIAL)."""
        return [
            f for f in self._factures
            if f.statut in (BillStatus.RECEIVED, BillStatus.APPROVED, BillStatus.PARTIAL)
        ]

    def mettre_a_jour_statut(
        self,
        numero_interne: str,
        statut: BillStatus,
        date_paiement: Optional[datetime.date] = None,
        montant_paye: Optional[Decimal] = None,
        methode_paiement: Optional[str] = None,
    ) -> FactureFournisseur:
        """Met a jour le statut d'une facture fournisseur. Leve ValueError si non trouvee."""
        for i, f in enumerate(self._factures):
            if f.numero_interne == numero_interne:
                donnees = f.model_dump()
                donnees["statut"] = statut
                if date_paiement is not None:
                    donnees["date_paiement"] = date_paiement
                if montant_paye is not None:
                    donnees["montant_paye"] = str(montant_paye)
                if methode_paiement is not None:
                    donnees["methode_paiement"] = methode_paiement
                self._factures[i] = FactureFournisseur.model_validate(donnees)
                self._sauvegarder()
                return self._factures[i]
        raise ValueError(f"Facture fournisseur {numero_interne} introuvable")

    def prochain_numero(self, annee: int) -> str:
        """Genere le prochain numero de facture fournisseur: FOUR-YYYY-NNN."""
        prefix = f"FOUR-{annee}-"
        numeros_existants = [
            int(f.numero_interne.replace(prefix, ""))
            for f in self._factures
            if f.numero_interne.startswith(prefix)
        ]
        prochain = max(numeros_existants, default=0) + 1
        return f"{prefix}{prochain:03d}"
