"""Modeles de donnees pour les factures fournisseurs (AP).

FactureFournisseur, LigneFactureFournisseur, BillStatus.
GST (5%) et QST (9.975%) calcules automatiquement sur les lignes applicables.
ITC/ITR rates (taux_itc/taux_itr) support partial eligibility (e.g., meals at 50%).
"""

from __future__ import annotations

import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator

from compteqc.factures.modeles import TAUX_TPS, TAUX_TVQ, QUANTIZE_CENT


class BillStatus(str, Enum):
    """Statut d'une facture fournisseur."""

    RECEIVED = "received"     # Bill received, not yet approved
    APPROVED = "approved"     # Approved for payment
    PAID = "paid"             # Fully paid
    PARTIAL = "partial"       # Partially paid
    DISPUTED = "disputed"     # Under dispute with vendor


class LigneFactureFournisseur(BaseModel):
    """Ligne d'une facture fournisseur."""

    description: str
    montant: Decimal  # Pre-tax amount for this line
    categorie_depense: str  # e.g. "Depenses:Bureau:Abonnements-Logiciels"
    tps_applicable: bool = True
    tvq_applicable: bool = True
    taux_itc: Decimal = Decimal("1.0")  # 1.0 = 100%, 0.5 = 50% (meals)
    taux_itr: Decimal = Decimal("1.0")  # Same for QST

    @field_validator("montant", "taux_itc", "taux_itr", mode="before")
    @classmethod
    def _coerce_decimal(cls, v: object) -> Decimal:
        if isinstance(v, float):
            return Decimal(str(v))
        return Decimal(v) if not isinstance(v, Decimal) else v


class FactureFournisseur(BaseModel):
    """Facture fournisseur (vendor bill) for accounts payable tracking."""

    numero_reference: str          # Vendor's invoice number
    numero_interne: str            # Internal tracking: "FOUR-2026-001"
    fournisseur: str               # Vendor name
    date_facture: datetime.date    # Invoice date
    date_echeance: datetime.date   # Due date
    lignes: list[LigneFactureFournisseur]
    statut: BillStatus = BillStatus.RECEIVED
    date_paiement: Optional[datetime.date] = None
    methode_paiement: Optional[str] = None  # "cheque", "virement", "carte-credit"
    montant_paye: Decimal = Decimal("0")
    notes: str = ""

    @field_validator("montant_paye", mode="before")
    @classmethod
    def _coerce_decimal(cls, v: object) -> Decimal:
        if isinstance(v, float):
            return Decimal(str(v))
        return Decimal(v) if not isinstance(v, Decimal) else v

    @property
    def montant_ht(self) -> Decimal:
        """Total pre-tax amount across all lines."""
        return sum((l.montant for l in self.lignes), Decimal("0"))

    @property
    def tps(self) -> Decimal:
        """GST (5%) on applicable lines."""
        base = sum(
            (l.montant for l in self.lignes if l.tps_applicable),
            Decimal("0"),
        )
        return (base * TAUX_TPS).quantize(QUANTIZE_CENT, rounding=ROUND_HALF_UP)

    @property
    def tvq(self) -> Decimal:
        """QST (9.975%) on applicable lines."""
        base = sum(
            (l.montant for l in self.lignes if l.tvq_applicable),
            Decimal("0"),
        )
        return (base * TAUX_TVQ).quantize(QUANTIZE_CENT, rounding=ROUND_HALF_UP)

    @property
    def total(self) -> Decimal:
        """Total amount including taxes."""
        return self.montant_ht + self.tps + self.tvq

    @property
    def solde(self) -> Decimal:
        """Outstanding balance (total - amount paid)."""
        return self.total - self.montant_paye
