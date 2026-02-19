"""Importateur CSV pour compte-cheques RBC."""

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

# Colonnes attendues pour le format RBC cheques
_COLONNES_CHEQUES = {
    "Account Type",
    "Account Number",
    "Transaction Date",
    "Cheque Number",
    "Description 1",
    "Description 2",
    "CAD$",
}


class RBCChequesImporter(beangulp.Importer):
    """Importateur pour les CSV de compte-cheques RBC.

    Formats attendus:
    - Colonnes: Account Type, Account Number, Transaction Date, Cheque Number,
      Description 1, Description 2, CAD$, USD$
    - Montants positifs = depots, negatifs = debits
    """

    def __init__(self, account: str = "Actifs:Banque:RBC:Cheques"):
        self._account = account

    def identify(self, filepath: str) -> bool:
        """Retourne True si le fichier est un CSV de cheques RBC."""
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
                return _COLONNES_CHEQUES.issubset(header_set)
        except Exception:
            return False

    def account(self, filepath: str) -> str:
        """Retourne le compte Beancount associe."""
        return self._account

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        """Extrait les transactions du CSV de cheques RBC.

        Args:
            filepath: Chemin du fichier CSV.
            existing: Transactions existantes pour deduplication.

        Returns:
            Liste de transactions Beancount.
        """
        path = Path(filepath)
        encodage = detecter_encodage(path)
        transactions: data.Entries = []

        # Construire un set de signatures pour deduplication
        existing_sigs = _construire_signatures_existantes(existing)

        with open(path, encoding=encodage, newline="") as f:
            reader = csv.DictReader(f)
            for lineno, row in enumerate(reader, start=2):
                try:
                    # Parser la date (format M/D/YYYY)
                    date_str = row["Transaction Date"].strip()
                    txn_date = datetime.strptime(date_str, "%m/%d/%Y").date()

                    # Parser le montant (CAD$)
                    montant_str = row["CAD$"].strip()
                    if not montant_str:
                        continue
                    montant = Decimal(montant_str)

                    # Construire la narration
                    desc1 = row.get("Description 1", "").strip()
                    desc2 = row.get("Description 2", "").strip()
                    narration = f"{desc1} {desc2}".strip() if desc2 else desc1
                    payee = nettoyer_beneficiaire(narration)

                    # Deduplication par date + montant + 20 premiers chars de narration
                    sig = _signature(txn_date, montant, narration)
                    if sig in existing_sigs:
                        logger.info(
                            "Doublon detecte ligne %d: %s %s %s",
                            lineno,
                            txn_date,
                            montant,
                            narration[:40],
                        )
                        continue

                    # Creer la transaction Beancount
                    meta = data.new_metadata(
                        str(path),
                        lineno,
                        {
                            "source": "rbc-cheques-csv",
                            "categorisation": "non-classe",
                            "fichier_source": path.name,
                            "ligne": str(lineno),
                        },
                    )

                    posting_banque = data.Posting(
                        account=self._account,
                        units=data.Amount(montant, "CAD"),
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                    posting_contrepartie = data.Posting(
                        account="Depenses:Non-Classe",
                        units=data.Amount(-montant, "CAD"),
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
                        postings=[posting_banque, posting_contrepartie],
                    )

                    transactions.append(txn)
                    existing_sigs.add(sig)

                except (KeyError, ValueError) as e:
                    logger.warning("Erreur ligne %d du CSV cheques: %s", lineno, e)
                    continue

        return transactions


def _signature(txn_date, montant: Decimal, narration: str) -> str:
    """Cree une signature pour deduplication CSV."""
    return f"{txn_date}|{montant}|{narration[:20]}"


def _construire_signatures_existantes(existing: data.Entries) -> set[str]:
    """Construit les signatures de deduplication a partir des transactions existantes."""
    sigs: set[str] = set()
    for entry in existing:
        if not isinstance(entry, data.Transaction):
            continue
        # Prendre le montant du premier posting
        if entry.postings:
            montant = entry.postings[0].units.number
            narration = entry.narration or ""
            sigs.add(_signature(entry.date, montant, narration))
    return sigs
