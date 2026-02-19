"""Importateur CSV pour carte de crédit RBC (Visa)."""

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
from compteqc.ingestion.rbc_cheques import (
    _est_header_rbc,
    _trouver_colonne,
)

logger = logging.getLogger(__name__)

_TYPE_VISA = "Visa"


class RBCCarteImporter(beangulp.Importer):
    """Importateur pour les transactions Visa dans un CSV RBC.

    Format réel RBC (même fichier que chèques):
    - Colonnes: Type de compte, Numéro du compte, Date de l'opération,
      Numéro du chèque, Description 1, Description 2, CAD, USD
    - Cet importateur ne traite que les lignes "Visa"
    - Montants négatifs = achats (augmentent le passif)
    - Montants positifs = paiements/crédits (diminuent le passif)
    """

    def __init__(self, account: str = "Passifs:CartesCredit:RBC"):
        self._account = account

    def identify(self, filepath: str) -> bool:
        """Retourne True si le fichier contient des transactions Visa RBC."""
        path = Path(filepath)
        if path.suffix.lower() != ".csv":
            return False
        try:
            encodage = detecter_encodage(path)
            with open(path, encoding=encodage, newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header is None or not _est_header_rbc(header):
                    return False
                col_type = _trouver_colonne(header, "Type")
                if col_type is None:
                    return False
                idx_type = [h.strip().strip('"') for h in header].index(col_type)
                for row in reader:
                    if len(row) > idx_type:
                        val = row[idx_type].strip().strip('"')
                        if val == _TYPE_VISA:
                            return True
                return False
        except Exception:
            return False

    def account(self, filepath: str) -> str:
        return self._account

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        """Extrait les transactions Visa du CSV RBC.

        Pour une carte crédit dans le CSV RBC:
        - Achats (montants négatifs): liability augmente
          -> Posting carte: montant tel quel (négatif = crédit au passif)
          -> Posting contrepartie: -montant (positif = débit à la dépense)
        - Paiements (montants positifs): liability diminue
          -> Posting carte: montant tel quel (positif = débit au passif)
          -> Posting contrepartie: -montant (négatif)
        """
        path = Path(filepath)
        encodage = detecter_encodage(path)
        transactions: data.Entries = []

        existing_sigs = _construire_signatures_existantes(existing)

        with open(path, encoding=encodage, newline="") as f:
            reader = csv.reader(f)
            header_raw = next(reader, None)
            if header_raw is None:
                return []

            header = [h.strip().strip('"') for h in header_raw]

            col_type = _trouver_colonne(header, "Type")
            col_date = _trouver_colonne(header, "Date")
            col_desc1 = _trouver_colonne(header, "Description 1")
            col_desc2 = _trouver_colonne(header, "Description 2")
            col_cad = _trouver_colonne(header, "CAD")

            if not all([col_type, col_date, col_desc1, col_cad]):
                logger.error("Colonnes requises manquantes dans le CSV")
                return []

            idx = {col: header.index(col) for col in [col_type, col_date, col_desc1, col_cad]}
            idx_desc2 = header.index(col_desc2) if col_desc2 else None

            for lineno, row in enumerate(reader, start=2):
                try:
                    if len(row) <= max(idx.values()):
                        continue
                    type_compte = row[idx[col_type]].strip().strip('"')
                    if type_compte != _TYPE_VISA:
                        continue

                    date_str = row[idx[col_date]].strip().strip('"')
                    txn_date = datetime.strptime(date_str, "%m/%d/%Y").date()

                    montant_str = row[idx[col_cad]].strip().strip('"')
                    if not montant_str:
                        continue
                    montant = Decimal(montant_str)

                    desc1 = row[idx[col_desc1]].strip().strip('"')
                    desc2 = ""
                    if idx_desc2 is not None and len(row) > idx_desc2:
                        desc2 = row[idx_desc2].strip().strip('"')
                    narration = f"{desc1} {desc2}".strip() if desc2 else desc1
                    payee = nettoyer_beneficiaire(desc1)

                    sig = _signature(txn_date, montant, narration)
                    if sig in existing_sigs:
                        logger.info(
                            "Doublon detecte ligne %d: %s %s %s",
                            lineno, txn_date, montant, narration[:40],
                        )
                        continue

                    meta = data.new_metadata(
                        str(path), lineno,
                        {
                            "source": "rbc-carte-csv",
                            "categorisation": "non-classe",
                            "fichier_source": path.name,
                            "ligne": str(lineno),
                        },
                    )

                    # Montant tel quel pour la carte (négatif = crédit, positif = débit)
                    posting_carte = data.Posting(
                        account=self._account,
                        units=data.Amount(montant, "CAD"),
                        cost=None, price=None, flag=None, meta=None,
                    )
                    posting_contrepartie = data.Posting(
                        account="Depenses:Non-Classe",
                        units=data.Amount(-montant, "CAD"),
                        cost=None, price=None, flag=None, meta=None,
                    )

                    txn = data.Transaction(
                        meta=meta, date=txn_date, flag="!",
                        payee=payee, narration=narration,
                        tags=EMPTY_SET, links=EMPTY_SET,
                        postings=[posting_carte, posting_contrepartie],
                    )

                    transactions.append(txn)
                    existing_sigs.add(sig)

                except (KeyError, ValueError, IndexError) as e:
                    logger.warning("Erreur ligne %d du CSV carte: %s", lineno, e)
                    continue

        return transactions


def _signature(txn_date, montant: Decimal, narration: str) -> str:
    return f"{txn_date}|{montant}|{narration[:20]}"


def _construire_signatures_existantes(existing: data.Entries) -> set[str]:
    sigs: set[str] = set()
    for entry in existing:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.postings:
            montant = entry.postings[0].units.number
            narration = entry.narration or ""
            sigs.add(_signature(entry.date, montant, narration))
    return sigs
