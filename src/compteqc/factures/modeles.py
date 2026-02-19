"""Modeles de donnees pour la facturation.

Facture, LigneFacture, InvoiceStatus, et ConfigFacturation.
GST (5%) et QST (9.975%) calcules automatiquement sur les lignes applicables.
"""

from __future__ import annotations

import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, field_validator


# Taux de taxes
TAUX_TPS = Decimal("0.05")
TAUX_TVQ = Decimal("0.09975")
QUANTIZE_CENT = Decimal("0.01")


class InvoiceStatus(str, Enum):
    """Statut d'une facture."""

    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"


class LigneFacture(BaseModel):
    """Ligne de facture avec calcul de sous-total."""

    description: str
    quantite: Decimal
    prix_unitaire: Decimal
    tps_applicable: bool = True
    tvq_applicable: bool = True

    @field_validator("quantite", "prix_unitaire", mode="before")
    @classmethod
    def _coerce_decimal(cls, v: object) -> Decimal:
        if isinstance(v, float):
            return Decimal(str(v))
        return Decimal(v) if not isinstance(v, Decimal) else v

    @property
    def sous_total(self) -> Decimal:
        """Sous-total de la ligne (quantite x prix unitaire), arrondi au cent."""
        return (self.quantite * self.prix_unitaire).quantize(
            QUANTIZE_CENT, rounding=ROUND_HALF_UP
        )


class Facture(BaseModel):
    """Facture complete avec calcul des taxes GST/QST."""

    numero: str  # e.g. "FAC-2026-001"
    nom_client: str
    adresse_client: str = ""
    date: datetime.date
    date_echeance: datetime.date
    lignes: list[LigneFacture]
    statut: InvoiceStatus = InvoiceStatus.DRAFT
    date_paiement: Optional[datetime.date] = None
    notes: str = ""

    @property
    def sous_total(self) -> Decimal:
        """Sous-total avant taxes."""
        return sum((ligne.sous_total for ligne in self.lignes), Decimal("0"))

    @property
    def tps(self) -> Decimal:
        """TPS (5%) sur les lignes applicables."""
        base = sum(
            (ligne.sous_total for ligne in self.lignes if ligne.tps_applicable),
            Decimal("0"),
        )
        return (base * TAUX_TPS).quantize(QUANTIZE_CENT, rounding=ROUND_HALF_UP)

    @property
    def tvq(self) -> Decimal:
        """TVQ (9.975%) sur les lignes applicables."""
        base = sum(
            (ligne.sous_total for ligne in self.lignes if ligne.tvq_applicable),
            Decimal("0"),
        )
        return (base * TAUX_TVQ).quantize(QUANTIZE_CENT, rounding=ROUND_HALF_UP)

    @property
    def total(self) -> Decimal:
        """Total de la facture (sous-total + TPS + TVQ)."""
        return self.sous_total + self.tps + self.tvq


class ConfigFacturation(BaseModel):
    """Configuration de facturation de l'entreprise."""

    nom_entreprise: str = "Mon Entreprise Inc."
    adresse: str = ""
    numero_tps: str = ""
    numero_tvq: str = ""
    logo_path: Optional[Path] = None
    couleur_primaire: str = "#1a365d"
    courriel: str = ""
    telephone: str = ""
