"""Importateur CSV pour carte de credit RBC."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import beangulp
from beancount.core import data
from beancount.core.data import EMPTY_SET

from compteqc.ingestion.normalisation import detecter_encodage, nettoyer_beneficiaire

logger = logging.getLogger(__name__)

# Colonnes attendues pour le format RBC carte credit
_COLONNES_CARTE = {
    "Transaction Date",
    "Posting Date",
    "Activity Type",
    "Description",
    "Amount",
}


class RBCCarteImporter(beangulp.Importer):
    """Importateur pour les CSV de carte de credit RBC.

    Formats attendus:
    - Colonnes: Transaction Date, Posting Date, Activity Type, Description, Amount
    - Montants positifs = achats (debits), negatifs = paiements/credits
    """

    def __init__(self, account: str = "Passifs:CartesCredit:RBC"):
        self._account = account

    def identify(self, filepath: str) -> bool:
        """Retourne True si le fichier est un CSV de carte credit RBC."""
        path = Path(filepath)
        if path.suffix.lower() != ".csv":
            return False
        try:
            encodage = detecter_encodage(path)
            with open(path, encoding=encodage, newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header is None:
                    return False
                header_set = {col.strip().strip('"') for col in header}
                return _COLONNES_CARTE.issubset(header_set)
        except Exception:
            return False

    def account(self, filepath: str) -> str:
        """Retourne le compte Beancount associe."""
        return self._account

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        """Extrait les transactions du CSV de carte credit RBC.

        Pour une carte credit:
        - Achats (montants positifs dans le CSV) = augmentent le passif
          -> Posting carte: -montant (credit en double-entry)
          -> Posting depense: +montant (debit en double-entry)
        - Paiements (montants negatifs dans le CSV) = diminuent le passif
          -> Posting carte: +abs(montant) (debit en double-entry)
          -> Posting depense: -abs(montant) (credit en double-entry)

        Args:
            filepath: Chemin du fichier CSV.
            existing: Transactions existantes pour deduplication.

        Returns:
            Liste de transactions Beancount.
        """
        path = Path(filepath)
        encodage = detecter_encodage(path)
        transactions: data.Entries = []

        existing_sigs = _construire_signatures_existantes(existing)

        with open(path, encoding=encodage, newline="") as f:
            reader = csv.DictReader(f)
            for lineno, row in enumerate(reader, start=2):
                try:
                    date_str = row["Transaction Date"].strip()
                    txn_date = datetime.strptime(date_str, "%m/%d/%Y").date()

                    montant_str = row["Amount"].strip()
                    if not montant_str:
                        continue
                    montant_csv = Decimal(montant_str)

                    description = row.get("Description", "").strip()
                    payee = nettoyer_beneficiaire(description)
                    narration = description

                    # Deduplication
                    sig = _signature(txn_date, montant_csv, narration)
                    if sig in existing_sigs:
                        logger.info(
                            "Doublon detecte ligne %d: %s %s %s",
                            lineno,
                            txn_date,
                            montant_csv,
                            narration[:40],
                        )
                        continue

                    meta = data.new_metadata(
                        str(path),
                        lineno,
                        {
                            "source": "rbc-carte-csv",
                            "categorisation": "non-classe",
                            "fichier_source": path.name,
                            "ligne": str(lineno),
                        },
                    )

                    # Carte credit: achat positif -> credit la carte (negatif),
                    # debit la depense (positif)
                    montant_carte = -montant_csv
                    montant_contrepartie = montant_csv

                    posting_carte = data.Posting(
                        account=self._account,
                        units=data.Amount(montant_carte, "CAD"),
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                    posting_contrepartie = data.Posting(
                        account="Depenses:Non-Classe",
                        units=data.Amount(montant_contrepartie, "CAD"),
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )

                    txn = data.Transaction(
                        meta=meta,
                        date=txn_date,
                        flag="!",
                        payee=payee,
                        narration=narration,
                        tags=EMPTY_SET,
                        links=EMPTY_SET,
                        postings=[posting_carte, posting_contrepartie],
                    )

                    transactions.append(txn)
                    existing_sigs.add(sig)

                except (KeyError, ValueError) as e:
                    logger.warning("Erreur ligne %d du CSV carte: %s", lineno, e)
                    continue

        return transactions


def _signature(txn_date, montant: Decimal, narration: str) -> str:
    """Cree une signature pour deduplication CSV."""
    return f"{txn_date}|{montant}|{narration[:20]}"


def _construire_signatures_existantes(existing: data.Entries) -> set[str]:
    """Construit les signatures de deduplication a partir des transactions existantes.

    Pour la carte credit, le montant CSV original est l'oppose du posting carte.
    On utilise le posting contrepartie (Depenses:Non-Classe) qui a le meme signe
    que le montant CSV original.
    """
    sigs: set[str] = set()
    for entry in existing:
        if not isinstance(entry, data.Transaction):
            continue
        if len(entry.postings) >= 2:
            # Le posting contrepartie (index 1) a le montant CSV original
            montant = entry.postings[1].units.number
            narration = entry.narration or ""
            sigs.add(_signature(entry.date, montant, narration))
    return sigs
