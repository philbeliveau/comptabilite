"""Factures recurrentes -- modeles et generation automatique.

Permet de definir des modeles de factures recurrentes (mensuelles, bimensuelles,
trimestrielles, annuelles) et de generer automatiquement les factures correspondantes.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import yaml
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, field_validator

from compteqc.factures.modeles import Facture, InvoiceStatus, LigneFacture
from compteqc.factures.registre import RegistreFactures

FREQUENCES_VALIDES = ("mensuel", "bimensuel", "trimestriel", "annuel")


class ModeleFactureRecurrente(BaseModel):
    """Modele pour la generation de factures recurrentes."""

    identifiant: str  # e.g. "REC-ACME-MENSUEL"
    nom_client: str
    adresse_client: str = ""
    lignes: list[LigneFacture]
    frequence: str = "mensuel"  # mensuel, bimensuel, trimestriel, annuel
    prochaine_generation: datetime.date
    actif: bool = True
    notes: str = ""
    echeance_jours: int = 30  # Delai de paiement en jours

    @field_validator("echeance_jours", mode="before")
    @classmethod
    def _coerce_int(cls, v: object) -> int:
        return int(v)


class RegistreRecurrents:
    """Registre de modeles de factures recurrentes, persiste en YAML."""

    def __init__(self, chemin: Path | None = None) -> None:
        self.chemin = chemin or Path("ledger/factures/modeles-recurrents.yaml")
        self._modeles: list[ModeleFactureRecurrente] = []
        self._charger()

    def _charger(self) -> None:
        """Charge les modeles depuis le fichier YAML."""
        if self.chemin.exists():
            with open(self.chemin, encoding="utf-8") as f:
                donnees = yaml.safe_load(f)
            if donnees and isinstance(donnees, list):
                self._modeles = [
                    ModeleFactureRecurrente.model_validate(d) for d in donnees
                ]

    def _sauvegarder(self) -> None:
        """Sauvegarde les modeles dans le fichier YAML."""
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        donnees = [m.model_dump(mode="json") for m in self._modeles]
        with open(self.chemin, "w", encoding="utf-8") as f:
            yaml.dump(
                donnees,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    def ajouter(self, modele: ModeleFactureRecurrente) -> None:
        """Ajoute un modele au registre. Leve ValueError si l'identifiant existe deja."""
        if any(m.identifiant == modele.identifiant for m in self._modeles):
            raise ValueError(
                f"Modele '{modele.identifiant}' existe deja dans le registre"
            )
        self._modeles.append(modele)
        self._sauvegarder()

    def obtenir(self, identifiant: str) -> ModeleFactureRecurrente | None:
        """Retourne un modele par son identifiant, ou None."""
        for m in self._modeles:
            if m.identifiant == identifiant:
                return m
        return None

    def lister(self, actif_seulement: bool = True) -> list[ModeleFactureRecurrente]:
        """Liste les modeles, optionnellement filtres par statut actif."""
        if actif_seulement:
            return [m for m in self._modeles if m.actif]
        return list(self._modeles)

    def mettre_a_jour(self, modele: ModeleFactureRecurrente) -> None:
        """Remplace un modele existant par son identifiant."""
        for i, m in enumerate(self._modeles):
            if m.identifiant == modele.identifiant:
                self._modeles[i] = modele
                self._sauvegarder()
                return
        raise ValueError(f"Modele '{modele.identifiant}' introuvable")


def avancer_date(frequence: str, date_courante: datetime.date) -> datetime.date:
    """Calcule la prochaine date de generation selon la frequence.

    Args:
        frequence: mensuel, bimensuel, trimestriel, annuel
        date_courante: Date courante de generation

    Returns:
        Prochaine date de generation
    """
    if frequence == "mensuel":
        return date_courante + relativedelta(months=1)
    elif frequence == "bimensuel":
        return date_courante + datetime.timedelta(weeks=2)
    elif frequence == "trimestriel":
        return date_courante + relativedelta(months=3)
    elif frequence == "annuel":
        return date_courante + relativedelta(months=12)
    else:
        raise ValueError(f"Frequence inconnue: {frequence}")


def generer_factures_recurrentes(
    registre_recurrents: RegistreRecurrents,
    registre_factures: RegistreFactures,
    date_reference: datetime.date | None = None,
) -> list[Facture]:
    """Genere les factures dues a partir des modeles recurrents.

    Pour chaque modele actif dont la prochaine_generation <= date_reference:
    - Cree une facture avec numero sequentiel
    - Ajoute la facture au registre
    - Avance la date de prochaine generation du modele

    Args:
        registre_recurrents: Registre des modeles recurrents
        registre_factures: Registre des factures
        date_reference: Date de reference (defaut: aujourd'hui)

    Returns:
        Liste des factures generees
    """
    if date_reference is None:
        date_reference = datetime.date.today()

    factures_generees: list[Facture] = []

    for modele in registre_recurrents.lister(actif_seulement=True):
        if modele.prochaine_generation > date_reference:
            continue

        # Create invoice
        numero = registre_factures.prochain_numero(modele.prochaine_generation.year)
        facture = Facture(
            numero=numero,
            nom_client=modele.nom_client,
            adresse_client=modele.adresse_client,
            date=modele.prochaine_generation,
            date_echeance=modele.prochaine_generation
            + datetime.timedelta(days=modele.echeance_jours),
            lignes=modele.lignes,
            statut=InvoiceStatus.DRAFT,
            notes=modele.notes,
        )

        registre_factures.ajouter(facture)
        factures_generees.append(facture)

        # Advance next generation date
        nouvelle_date = avancer_date(modele.frequence, modele.prochaine_generation)
        modele_maj = modele.model_copy(
            update={"prochaine_generation": nouvelle_date}
        )
        registre_recurrents.mettre_a_jour(modele_maj)

    return factures_generees
