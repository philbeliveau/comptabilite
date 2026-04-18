"""Extraction de donnees structurees depuis un document via Claude Vision.

Utilise l'API Anthropic avec messages.create() et structured output Pydantic
pour extraire contrepartie, date, montants et taxes depuis une image ou un PDF.
Le flux "expense" conserve le comportement historique de recu fournisseur;
le flux "revenue" reste plus conservateur et n'invente pas de lignes de taxes
si elles ne sont pas visibles.
"""

from __future__ import annotations

import base64
import logging
import os
from decimal import Decimal
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

load_dotenv()

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
}

_PROMPT_EXTRACTION_DEPENSE = """\
Extract from this expense receipt:
- Vendor name (fournisseur)
- Date in YYYY-MM-DD format
- Subtotal before tax (sous_total)
- GST/TPS amount (5%) (montant_tps)
- QST/TVQ amount (9.975%) (montant_tvq)
- Total amount (total)
- Brief description of what was purchased (description)

If a tax line is not visible but the subtotal is visible, calculate TPS/TVQ from the subtotal.
If the date is not readable, use 'UNKNOWN'.
Rate your overall confidence from 0.0 to 1.0 based on image quality and readability.
"""

_PROMPT_EXTRACTION_REVENU = """\
Extract from this client revenue document:
- Client or counterparty name (fournisseur)
- Date in YYYY-MM-DD format
- Subtotal before tax if explicitly shown (sous_total)
- GST/TPS amount if explicitly shown (montant_tps)
- QST/TVQ amount if explicitly shown (montant_tvq)
- Total amount received or billed (total)
- Brief description of the service/payment (description)

Important:
- Do not invent or infer GST/QST lines if they are not visibly shown.
- If only a total is visible, set sous_total equal to total and leave tax amounts null.
- If the date is not readable, use 'UNKNOWN'.
- Rate your overall confidence from 0.0 to 1.0 based on image quality and readability.
"""

DocumentKind = Literal["expense", "revenue"]
PricingMode = Literal["tax_included", "pre_tax", "explicit_tax_lines", "unknown"]
NormalizationStatus = Literal[
    "matched_and_normalized",
    "matched_needs_review",
    "unmatched",
    "already_normalized",
]


class DonneesRecu(BaseModel):
    """Donnees structurees extraites d'un recu."""

    fournisseur: str = Field(description="Nom du fournisseur/vendeur")
    date: str = Field(description="Date du recu au format YYYY-MM-DD ou 'UNKNOWN'")
    sous_total: Decimal = Field(description="Sous-total avant taxes")
    montant_tps: Decimal | None = Field(default=None, description="Montant TPS (5%)")
    montant_tvq: Decimal | None = Field(default=None, description="Montant TVQ (9.975%)")
    total: Decimal = Field(description="Montant total")
    description: str = Field(default="", description="Description de l'achat")
    confiance: float = Field(ge=0.0, le=1.0, description="Confiance de l'extraction 0.0-1.0")
    document_kind: DocumentKind = Field(default="expense", description="Nature du document")
    pricing_mode: PricingMode = Field(
        default="explicit_tax_lines",
        description="Mode de prix confirme par l'operateur",
    )
    normalization_status: NormalizationStatus = Field(
        default="unmatched",
        description="Etat courant d'appariement ou normalisation",
    )


# Lazy client initialization (same pattern as categorisation/llm.py)
_client = None


def _get_client():
    """Initialise le client Anthropic de facon lazy."""
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        )
    return _client


def extraire_recu(
    image_path: Path,
    modele: str = "claude-sonnet-4-5-20250929",
    document_kind: DocumentKind = "expense",
) -> DonneesRecu:
    """Extrait les donnees structurees d'un recu via Claude Vision.

    Args:
        image_path: Chemin vers l'image ou PDF du recu.
        modele: Modele Claude a utiliser.
        document_kind: Nature du document a extraire.

    Returns:
        DonneesRecu avec les champs extraits et un score de confiance.
    """
    suffix = image_path.suffix.lower()
    media_type = _MEDIA_TYPES.get(suffix)
    if not media_type:
        raise ValueError(f"Type de fichier non supporte: {suffix}")

    data = image_path.read_bytes()
    data_b64 = base64.standard_b64encode(data).decode("ascii")

    # Build content block based on file type
    if suffix == ".pdf":
        source_block = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": data_b64,
            },
        }
    else:
        source_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data_b64,
            },
        }

    client = _get_client()

    # Use messages.create with tool_use for structured extraction
    # We define a tool that matches our DonneesRecu schema
    tool_schema = {
        "name": "extraire_donnees_recu",
        "description": "Extraire les donnees structurees d'un recu",
        "input_schema": DonneesRecu.model_json_schema(),
    }

    prompt = (
        _PROMPT_EXTRACTION_REVENU
        if document_kind == "revenue"
        else _PROMPT_EXTRACTION_DEPENSE
    )

    response = client.messages.create(
        model=modele,
        max_tokens=1024,
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": "extraire_donnees_recu"},
        messages=[
            {
                "role": "user",
                "content": [
                    source_block,
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    # Extract the tool use block
    for block in response.content:
        if block.type == "tool_use":
            resultat = DonneesRecu.model_validate(block.input)
            resultat.document_kind = document_kind
            resultat.pricing_mode = (
                "explicit_tax_lines" if document_kind == "expense" else "unknown"
            )
            resultat.normalization_status = "unmatched"

            if resultat.confiance < 0.5:
                logger.warning(
                    "Extraction a faible confiance (%.2f) pour %s. "
                    "Verifiez les donnees manuellement.",
                    resultat.confiance,
                    image_path.name,
                )

            return resultat

    # Fallback if no tool_use block found
    raise RuntimeError("Claude n'a pas retourne de bloc tool_use pour l'extraction")
