"""Importateur CSV pour compte-chèques RBC."""

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

# Colonnes requises dans le format RBC réel
_COLONNES_REQUISES = {"Description 1", "CAD"}

# Préfixe du type de compte pour chèques (gère l'encodage: "Chèques", "Ch?ques", etc.)
_TYPE_CHEQUES_PREFIX = "Ch"


def _est_header_rbc(header: list[str]) -> bool:
    """Vérifie que le header correspond au format RBC."""
    header_set = {col.strip().strip('"') for col in header}
    # Chercher les colonnes clés indépendamment de l'encodage du "é"
    has_desc1 = any("Description 1" in col for col in header_set)
    has_cad = any(col.strip().startswith("CAD") for col in header_set)
    has_type = any("Type" in col for col in header_set)
    return has_desc1 and has_cad and has_type


def _trouver_colonne(header: list[str], *candidats: str) -> str | None:
    """Trouve le nom exact d'une colonne parmi des candidats (correspondance partielle)."""
    for col in header:
        col_stripped = col.strip().strip('"')
        for candidat in candidats:
            if candidat in col_stripped:
                return col_stripped
    return None


class RBCChequesImporter(beangulp.Importer):
    """Importateur pour les CSV de compte-chèques RBC.

    Format réel RBC:
    - Colonnes: Type de compte, Numéro du compte, Date de l'opération,
      Numéro du chèque, Description 1, Description 2, CAD, USD
    - Fichier peut contenir des lignes Chèques ET Visa (fichier combiné)
    - Cet importateur ne traite que les lignes "Chèques"
    - Montants positifs = dépôts, négatifs = débits
    """

    def __init__(self, account: str = "Actifs:Banque:RBC:Cheques"):
        self._account = account

    def identify(self, filepath: str) -> bool:
        """Retourne True si le fichier contient des transactions chèques RBC."""
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
                # Vérifier qu'il y a au moins une ligne Chèques
                col_type = _trouver_colonne(header, "Type")
                if col_type is None:
                    return False
                idx_type = [h.strip().strip('"') for h in header].index(col_type)
                for row in reader:
                    if len(row) > idx_type:
                        val = row[idx_type].strip().strip('"')
                        if val.startswith(_TYPE_CHEQUES_PREFIX):
                            return True
                return False
        except Exception:
            return False

    def account(self, filepath: str) -> str:
        return self._account

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        """Extrait les transactions chèques du CSV RBC."""
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

            # Trouver les indices des colonnes
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
                    # Filtrer: seulement les lignes Chèques
                    if len(row) <= max(idx.values()):
                        continue
                    type_compte = row[idx[col_type]].strip().strip('"')
                    if not type_compte.startswith(_TYPE_CHEQUES_PREFIX):
                        continue

                    # Parser la date (format M/D/YYYY)
                    date_str = row[idx[col_date]].strip().strip('"')
                    txn_date = datetime.strptime(date_str, "%m/%d/%Y").date()

                    # Parser le montant (CAD)
                    montant_str = row[idx[col_cad]].strip().strip('"')
                    if not montant_str:
                        continue
                    montant = Decimal(montant_str)

                    # Construire la narration
                    desc1 = row[idx[col_desc1]].strip().strip('"')
                    desc2 = ""
                    if idx_desc2 is not None and len(row) > idx_desc2:
                        desc2 = row[idx_desc2].strip().strip('"')
                    narration = f"{desc1} {desc2}".strip() if desc2 else desc1
                    payee = nettoyer_beneficiaire(narration)

                    # Déduplication
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
                            "source": "rbc-cheques-csv",
                            "categorisation": "non-classe",
                            "fichier_source": path.name,
                            "ligne": str(lineno),
                        },
                    )

                    posting_banque = data.Posting(
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
                        postings=[posting_banque, posting_contrepartie],
                    )

                    transactions.append(txn)
                    existing_sigs.add(sig)

                except (KeyError, ValueError, IndexError) as e:
                    logger.warning("Erreur ligne %d du CSV cheques: %s", lineno, e)
                    continue

        return transactions


def _signature(txn_date, montant: Decimal, narration: str) -> str:
    """Crée une signature pour déduplication CSV."""
    return f"{txn_date}|{montant}|{narration[:20]}"


def _construire_signatures_existantes(existing: data.Entries) -> set[str]:
    """Construit les signatures de déduplication à partir des transactions existantes."""
    sigs: set[str] = set()
    for entry in existing:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.postings:
            montant = entry.postings[0].units.number
            narration = entry.narration or ""
            sigs.add(_signature(entry.date, montant, narration))
    return sigs
