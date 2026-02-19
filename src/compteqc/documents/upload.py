"""Telecharger et stocker les recus dans le repertoire du ledger.

Valide le type de fichier, redimensionne les images trop grandes,
et stocke les fichiers dans ledger/documents/{YYYY}/{MM}/.
"""

from __future__ import annotations

import logging
import re
import shutil
from datetime import date
from pathlib import Path

from PIL import Image

from compteqc.documents.extraction import DonneesRecu

logger = logging.getLogger(__name__)

_EXTENSIONS_VALIDES = {".jpg", ".jpeg", ".png", ".pdf"}
_MAX_DIMENSION = 1568  # Recommandation Anthropic pour Claude Vision


def telecharger_recu(source_path: Path, ledger_dir: Path) -> Path:
    """Telecharge un recu dans le repertoire documents du ledger.

    Args:
        source_path: Chemin vers le fichier source (image ou PDF).
        ledger_dir: Repertoire racine du ledger (ex: ledger/).

    Returns:
        Chemin vers le fichier stocke.

    Raises:
        ValueError: Si le type de fichier n'est pas supporte.
        FileNotFoundError: Si le fichier source n'existe pas.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {source_path}")

    ext = source_path.suffix.lower()
    if ext not in _EXTENSIONS_VALIDES:
        raise ValueError(
            f"Type de fichier non supporte: {ext}. "
            f"Types acceptes: {', '.join(sorted(_EXTENSIONS_VALIDES))}"
        )

    # Date courante pour l'organisation
    aujourd_hui = date.today()
    dest_dir = ledger_dir / "documents" / f"{aujourd_hui.year}" / f"{aujourd_hui.month:02d}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / f"{aujourd_hui.isoformat()}.recu{ext}"

    # Redimensionner les images trop grandes
    if ext in {".jpg", ".jpeg", ".png"}:
        _copier_et_redimensionner(source_path, dest_path)
    else:
        shutil.copy2(source_path, dest_path)

    logger.info("Recu telecharge: %s -> %s", source_path, dest_path)
    return dest_path


def renommer_recu(stored_path: Path, donnees: DonneesRecu) -> Path:
    """Renomme un recu stocke avec les donnees extraites.

    Args:
        stored_path: Chemin actuel du fichier stocke.
        donnees: Donnees extraites du recu.

    Returns:
        Nouveau chemin du fichier renomme.
    """
    slug = _slugifier(donnees.fournisseur)
    date_str = donnees.date if donnees.date != "UNKNOWN" else "date-inconnue"
    ext = stored_path.suffix.lower()

    nouveau_nom = f"{date_str}.{slug}{ext}"
    nouveau_chemin = stored_path.parent / nouveau_nom

    # Eviter les conflits
    compteur = 1
    while nouveau_chemin.exists() and nouveau_chemin != stored_path:
        nouveau_nom = f"{date_str}.{slug}.{compteur}{ext}"
        nouveau_chemin = stored_path.parent / nouveau_nom
        compteur += 1

    stored_path.rename(nouveau_chemin)
    logger.info("Recu renomme: %s -> %s", stored_path.name, nouveau_chemin.name)
    return nouveau_chemin


def _copier_et_redimensionner(source: Path, dest: Path) -> None:
    """Copie une image en la redimensionnant si necessaire."""
    with Image.open(source) as img:
        largeur, hauteur = img.size
        plus_grand = max(largeur, hauteur)

        if plus_grand > _MAX_DIMENSION:
            ratio = _MAX_DIMENSION / plus_grand
            nouvelle_largeur = int(largeur * ratio)
            nouvelle_hauteur = int(hauteur * ratio)
            img_redim = img.resize(
                (nouvelle_largeur, nouvelle_hauteur), Image.Resampling.LANCZOS
            )
            img_redim.save(dest)
            logger.info(
                "Image redimensionnee: %dx%d -> %dx%d",
                largeur, hauteur, nouvelle_largeur, nouvelle_hauteur,
            )
        else:
            shutil.copy2(source, dest)


def _slugifier(texte: str) -> str:
    """Convertit un texte en slug pour nom de fichier."""
    slug = texte.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:50] if slug else "inconnu"
