"""Proposer des correspondances entre un recu et des transactions existantes.

Compare le montant total et la date du recu avec les transactions du ledger
pour suggerer des appariements avec un score de confiance.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from compteqc.documents.extraction import DonneesRecu


class Correspondance(BaseModel):
    """Une correspondance proposee entre un recu et une transaction."""

    transaction_index: int = Field(description="Index de la transaction dans la liste")
    date: datetime.date = Field(description="Date de la transaction")
    narration: str = Field(description="Narration de la transaction")
    montant: Decimal = Field(description="Montant de la transaction")
    score: float = Field(ge=0.0, le=1.0, description="Score de correspondance")


def proposer_correspondances(
    donnees: DonneesRecu,
    entries: list,
    seuil: float = 0.5,
) -> list[Correspondance]:
    """Propose des correspondances entre un recu et des transactions.

    Args:
        donnees: Donnees extraites du recu.
        entries: Liste d'entrees Beancount (issues du loader).
        seuil: Score minimum pour inclure une correspondance.

    Returns:
        Liste de Correspondance triee par score decroissant (max 5).
    """
    from beancount.core import data as beancount_data

    # Determiner la date du recu
    try:
        date_recu = datetime.date.fromisoformat(donnees.date)
    except (ValueError, TypeError):
        # Si date inconnue, on ne peut pas scorer la date
        date_recu = None

    correspondances: list[Correspondance] = []

    for i, entry in enumerate(entries):
        if not isinstance(entry, beancount_data.Transaction):
            continue

        # Prendre le montant du premier posting (valeur absolue)
        if not entry.postings:
            continue

        premier_posting = entry.postings[0]
        if premier_posting.units is None:
            continue

        montant_txn = abs(premier_posting.units.number)

        # Score montant: 1.0 si < $0.05, decroit lineairement a 0 a $5.00
        diff_montant = abs(donnees.total - montant_txn)
        if diff_montant <= Decimal("0.05"):
            score_montant = 1.0
        elif diff_montant >= Decimal("5.00"):
            score_montant = 0.0
        else:
            score_montant = float(1.0 - (diff_montant - Decimal("0.05")) / Decimal("4.95"))

        # Score date: 1.0 si meme jour, 0.8 si +/- 1 jour, decroit a 0 a 7 jours
        if date_recu is not None:
            diff_jours = abs((entry.date - date_recu).days)
            if diff_jours == 0:
                score_date = 1.0
            elif diff_jours == 1:
                score_date = 0.8
            elif diff_jours >= 7:
                score_date = 0.0
            else:
                # Linear decay from 0.8 at 1 day to 0.0 at 7 days
                score_date = 0.8 * (1.0 - (diff_jours - 1) / 6.0)
        else:
            score_date = 0.0

        # Score combine: 60% montant + 40% date
        score = 0.6 * score_montant + 0.4 * score_date

        if score >= seuil:
            correspondances.append(
                Correspondance(
                    transaction_index=i,
                    date=entry.date,
                    narration=entry.narration or "",
                    montant=montant_txn,
                    score=round(score, 3),
                )
            )

    # Trier par score decroissant, limiter a 5
    correspondances.sort(key=lambda c: c.score, reverse=True)
    return correspondances[:5]
