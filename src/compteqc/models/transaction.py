"""Modele de transaction normalisee pour CompteQC."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _rejeter_float(v: Any) -> Any:
    """Refuse les float pour forcer l'utilisation de Decimal ou str."""
    if isinstance(v, float):
        raise ValueError(
            "Les montants doivent etre Decimal ou str, jamais float. "
            "Utilisez Decimal('100.00') ou '100.00'."
        )
    return v


MontantDecimal = Annotated[Decimal, BeforeValidator(_rejeter_float)]


class TransactionNormalisee(BaseModel):
    """Transaction normalisee provenant de n'importe quelle source (CSV, OFX, etc.).

    Tous les montants sont en Decimal pour eviter les erreurs d'arrondi.
    Les float sont explicitement refuses pour le champ montant.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "date": "2026-01-15",
                    "montant": "100.00",
                    "devise": "CAD",
                    "beneficiaire": "Hydro-Quebec",
                    "description": "Paiement mensuel electricite",
                    "source": "rbc-cheques-csv",
                }
            ]
        },
    )

    date: datetime.date
    montant: MontantDecimal = Field(description="Montant en Decimal, jamais float")
    devise: str = "CAD"
    beneficiaire: str = Field(description="Payee / beneficiaire")
    description: str = Field(description="Narration / description de la transaction")
    memo: str | None = None
    source: str = Field(description="Identifiant de la source (ex: rbc-cheques-csv, rbc-ofx)")
    numero_reference: str | None = Field(
        default=None, description="FITID pour OFX ou autre numero de reference"
    )
