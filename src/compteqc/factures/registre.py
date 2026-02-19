"""Registre de factures avec persistance YAML.

Stocke les factures dans un fichier YAML avec numerotation sequentielle.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

import yaml

from compteqc.factures.modeles import Facture, InvoiceStatus


class RegistreFactures:
    """Registre de factures persistant en YAML."""

    def __init__(self, chemin: Path | None = None) -> None:
        self.chemin = chemin or Path("ledger/factures/registre.yaml")
        self._factures: list[Facture] = []
        self._charger()

    def _charger(self) -> None:
        """Charge les factures depuis le fichier YAML."""
        if self.chemin.exists():
            with open(self.chemin, encoding="utf-8") as f:
                donnees = yaml.safe_load(f)
            if donnees and isinstance(donnees, list):
                self._factures = [Facture.model_validate(d) for d in donnees]

    def _sauvegarder(self) -> None:
        """Sauvegarde les factures dans le fichier YAML."""
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        donnees = [f.model_dump(mode="json") for f in self._factures]
        with open(self.chemin, "w", encoding="utf-8") as f:
            yaml.dump(donnees, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def ajouter(self, facture: Facture) -> None:
        """Ajoute une facture au registre. Leve ValueError si le numero existe deja."""
        if any(f.numero == facture.numero for f in self._factures):
            raise ValueError(f"Facture {facture.numero} existe deja dans le registre")
        self._factures.append(facture)
        self._sauvegarder()

    def obtenir(self, numero: str) -> Facture | None:
        """Retourne une facture par son numero, ou None."""
        for f in self._factures:
            if f.numero == numero:
                return f
        return None

    def lister(self, statut: InvoiceStatus | None = None) -> list[Facture]:
        """Liste les factures, optionnellement filtrees par statut."""
        if statut is None:
            return list(self._factures)
        return [f for f in self._factures if f.statut == statut]

    def mettre_a_jour_statut(
        self,
        numero: str,
        statut: InvoiceStatus,
        date_paiement: Optional[datetime.date] = None,
    ) -> Facture:
        """Met a jour le statut d'une facture. Leve ValueError si non trouvee."""
        for i, f in enumerate(self._factures):
            if f.numero == numero:
                donnees = f.model_dump()
                donnees["statut"] = statut
                if date_paiement is not None:
                    donnees["date_paiement"] = date_paiement
                self._factures[i] = Facture.model_validate(donnees)
                self._sauvegarder()
                return self._factures[i]
        raise ValueError(f"Facture {numero} introuvable")

    def prochain_numero(self, annee: int) -> str:
        """Genere le prochain numero de facture pour l'annee donnee.

        Format: FAC-YYYY-NNN (zero-padded a 3 chiffres).
        """
        prefix = f"FAC-{annee}-"
        numeros_existants = [
            int(f.numero.replace(prefix, ""))
            for f in self._factures
            if f.numero.startswith(prefix)
        ]
        prochain = max(numeros_existants, default=0) + 1
        return f"{prefix}{prochain:03d}"
