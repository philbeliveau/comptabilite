"""Extraction de donnees structurees depuis un recu via Claude Vision.

Utilise l'API Anthropic avec messages.create() et structured output Pydantic
pour extraire fournisseur, date, montants et taxes depuis une image ou un PDF.
"""

from __future__ import annotations

import base64
import logging
import os
from decimal import Decimal
from pathlib import Path

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

_PROMPT_EXTRACTION = """\
Extract from this receipt:
- Vendor name (fournisseur)
- Date in YYYY-MM-DD format
- Subtotal before tax (sous_total)
- GST/TPS amount (5%) (montant_tps)
- QST/TVQ amount (9.975%) (montant_tvq)
- Total amount (total)
- Brief description of what was purchased (description)

If a tax line is not visible, calculate it from the subtotal.
If the date is not readable, use 'UNKNOWN'.
Rate your overall confidence from 0.0 to 1.0 based on image quality and readability.
"""


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
) -> DonneesRecu:
    """Extrait les donnees structurees d'un recu via Claude Vision.

    Args:
        image_path: Chemin vers l'image ou PDF du recu.
        modele: Modele Claude a utiliser.

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
                    {"type": "text", "text": _PROMPT_EXTRACTION},
                ],
            }
        ],
    )

    # Extract the tool use block
    for block in response.content:
        if block.type == "tool_use":
            resultat = DonneesRecu.model_validate(block.input)

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
