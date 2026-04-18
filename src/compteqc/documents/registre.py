"""Registre YAML des documents fiscaux televerses.

Le registre conserve l'etat des documents de depense et de revenu afin que
les surfaces Fava, MCP et rapports puissent partager le meme statut
d'appariement/normalisation sans dupliquer de logique en memoire.
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from compteqc.documents.extraction import DonneesRecu

DocumentKind = Literal["expense", "revenue"]
PricingMode = Literal["tax_included", "pre_tax", "explicit_tax_lines", "unknown"]
NormalizationStatus = Literal[
    "matched_and_normalized",
    "matched_needs_review",
    "unmatched",
    "already_normalized",
]


class DocumentFiscal(BaseModel):
    """Document televerse avec etat de normalisation fiscal."""

    id: str = Field(default_factory=lambda: f"doc-{uuid.uuid4().hex[:12]}")
    chemin_document: str
    nom_fichier: str
    fournisseur: str
    date: str
    sous_total: Decimal
    montant_tps: Decimal | None = None
    montant_tvq: Decimal | None = None
    total: Decimal
    description: str = ""
    confiance: float = 0.0
    document_kind: DocumentKind = "expense"
    pricing_mode: PricingMode = "explicit_tax_lines"
    normalization_status: NormalizationStatus = "unmatched"
    matched_transaction_ref: str | None = None
    traitement_taxes: str | None = None
    review_reason: str | None = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

    @classmethod
    def depuis_extraction(
        cls,
        donnees: DonneesRecu,
        chemin_document: str,
        nom_fichier: str,
        document_kind: DocumentKind,
        pricing_mode: PricingMode,
    ) -> "DocumentFiscal":
        return cls(
            chemin_document=chemin_document,
            nom_fichier=nom_fichier,
            fournisseur=str(donnees.fournisseur),
            date=str(donnees.date),
            sous_total=donnees.sous_total,
            montant_tps=donnees.montant_tps,
            montant_tvq=donnees.montant_tvq,
            total=donnees.total,
            description=str(donnees.description or ""),
            confiance=float(donnees.confiance),
            document_kind=document_kind,
            pricing_mode=pricing_mode,
            normalization_status=(
                "matched_needs_review"
                if document_kind == "revenue" and pricing_mode == "unknown"
                else "unmatched"
            ),
            review_reason=(
                "Mode de prix a confirmer avant normalisation."
                if document_kind == "revenue" and pricing_mode == "unknown"
                else None
            ),
        )


class RegistreDocumentsFiscaux:
    """Registre persistant de documents televerses."""

    def __init__(self, chemin: Path | None = None) -> None:
        self.chemin = chemin or Path("ledger/documents/registre.yaml")
        self._documents: list[DocumentFiscal] = []
        self._charger()

    def _charger(self) -> None:
        if not self.chemin.exists():
            return
        with open(self.chemin, encoding="utf-8") as f:
            donnees = yaml.safe_load(f) or []
        if isinstance(donnees, list):
            self._documents = [DocumentFiscal.model_validate(item) for item in donnees]

    def _sauvegarder(self) -> None:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        donnees = [doc.model_dump(mode="json") for doc in self._documents]
        with open(self.chemin, "w", encoding="utf-8") as f:
            yaml.dump(
                donnees,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    def ajouter(self, document: DocumentFiscal) -> DocumentFiscal:
        self._documents.append(document)
        self._sauvegarder()
        return document

    def obtenir(self, document_id: str) -> DocumentFiscal | None:
        for document in self._documents:
            if document.id == document_id:
                return document
        return None

    def trouver_par_chemin(self, chemin_document: str) -> DocumentFiscal | None:
        for document in reversed(self._documents):
            if document.chemin_document == chemin_document:
                return document
        return None

    def mettre_a_jour(self, document_id: str, **champs) -> DocumentFiscal:
        for index, document in enumerate(self._documents):
            if document.id != document_id:
                continue
            donnees = document.model_dump()
            donnees.update(champs)
            donnees["updated_at"] = datetime.datetime.now()
            maj = DocumentFiscal.model_validate(donnees)
            self._documents[index] = maj
            self._sauvegarder()
            return maj
        raise ValueError(f"Document fiscal introuvable: {document_id}")

    def lister(self) -> list[DocumentFiscal]:
        return list(self._documents)

    def lister_revenus(self) -> list[DocumentFiscal]:
        return [document for document in self._documents if document.document_kind == "revenue"]
