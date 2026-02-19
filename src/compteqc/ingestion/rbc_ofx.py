"""Importateur OFX/QFX pour RBC."""

from __future__ import annotations

import logging
from pathlib import Path

import beangulp
from beancount.core import data
from beancount.core.data import EMPTY_SET
from ofxtools.Parser import OFXTree

from compteqc.ingestion.normalisation import nettoyer_beneficiaire

logger = logging.getLogger(__name__)


class RBCOfxImporter(beangulp.Importer):
    """Importateur pour les fichiers OFX/QFX de comptes RBC.

    Utilise ofxtools pour parser les fichiers OFX v1 (SGML) et v2 (XML).
    La deduplication se fait par FITID (identifiant unique de transaction).
    """

    def __init__(self, account: str, account_id: str):
        """Initialise l'importateur OFX RBC.

        Args:
            account: Nom du compte Beancount (ex: "Actifs:Banque:RBC:Cheques").
            account_id: Le ACCTID RBC pour identifier le bon compte.
        """
        self._account = account
        self._account_id = account_id

    def identify(self, filepath: str) -> bool:
        """Retourne True si le fichier est un OFX/QFX pour le bon compte RBC."""
        path = Path(filepath)
        if path.suffix.lower() not in (".ofx", ".qfx"):
            return False
        try:
            tree = OFXTree()
            tree.parse(str(path))
            ofx = tree.convert()
            for stmt in ofx.statements:
                if stmt.account.acctid == self._account_id:
                    return True
            return False
        except Exception:
            return False

    def account(self, filepath: str) -> str:
        """Retourne le compte Beancount associe."""
        return self._account

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        """Extrait les transactions du fichier OFX/QFX.

        La deduplication se fait par FITID: si un FITID existe deja dans
        les transactions existantes, il est considere comme doublon certain.

        Args:
            filepath: Chemin du fichier OFX/QFX.
            existing: Transactions existantes pour deduplication.

        Returns:
            Liste de transactions Beancount.

        Raises:
            ValueError: Si le fichier OFX est invalide ou ne contient pas
                le bon compte.
        """
        path = Path(filepath)

        try:
            tree = OFXTree()
            tree.parse(str(path))
            ofx = tree.convert()
        except Exception as e:
            raise ValueError(f"Fichier OFX invalide: {path} - {e}") from e

        # Collecter les FITID existants pour deduplication
        existing_fitids = _collecter_fitids(existing)

        transactions: data.Entries = []
        found_account = False

        for stmt in ofx.statements:
            if stmt.account.acctid != self._account_id:
                continue
            found_account = True

            for tx in stmt.transactions:
                fitid = str(tx.fitid)

                # Deduplication par FITID
                if fitid in existing_fitids:
                    logger.info("Doublon OFX detecte: FITID=%s", fitid)
                    continue

                # Construire narration depuis NAME + MEMO
                name = str(tx.name or "").strip()
                memo = str(tx.memo or "").strip()
                narration = f"{name} {memo}".strip() if memo else name
                payee = nettoyer_beneficiaire(narration)

                # Le montant est deja un Decimal via ofxtools
                montant = tx.trnamt

                meta = data.new_metadata(
                    str(path),
                    0,
                    {
                        "fitid": fitid,
                        "source": "rbc-ofx",
                        "categorisation": "non-classe",
                        "fichier_source": path.name,
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
                    date=tx.dtposted.date(),
                    flag="!",
                    payee=payee,
                    narration=narration,
                    tags=EMPTY_SET,
                    links=EMPTY_SET,
                    postings=[posting_banque, posting_contrepartie],
                )

                transactions.append(txn)
                existing_fitids.add(fitid)

        if not found_account:
            raise ValueError(
                f"Compte {self._account_id} non trouve dans le fichier OFX: {path}"
            )

        return transactions


def _collecter_fitids(existing: data.Entries) -> set[str]:
    """Collecte les FITID des transactions existantes."""
    fitids: set[str] = set()
    for entry in existing:
        if not isinstance(entry, data.Transaction):
            continue
        fitid = entry.meta.get("fitid")
        if fitid:
            fitids.add(str(fitid))
    return fitids
