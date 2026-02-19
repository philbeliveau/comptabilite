"""Utilitaires de normalisation pour le pipeline d'ingestion CompteQC."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path


def nettoyer_beneficiaire(brut: str) -> str:
    """Normalise un nom de beneficiaire brut.

    - Normalise les espaces multiples
    - Retire les numeros de transaction/reference en fin de chaine
    - Capitalise en Title Case

    Args:
        brut: Le nom brut tel que lu du CSV/OFX.

    Returns:
        Le nom nettoye en Title Case.
    """
    # Normalise les espaces
    texte = re.sub(r"\s+", " ", brut.strip())

    # Retire les numeros de reference en fin de chaine (ex: REF87654, 1234567, #12345)
    texte = re.sub(r"\s+(REF\d+|#\d+|\d{5,})$", "", texte, flags=re.IGNORECASE)

    # Title Case
    texte = texte.title()

    return texte


def detecter_encodage(chemin: Path) -> str:
    """Detecte l'encodage d'un fichier texte.

    Essaie UTF-8, puis Latin-1, puis Windows-1252.

    Args:
        chemin: Le chemin du fichier a tester.

    Returns:
        Le nom de l'encodage qui fonctionne.

    Raises:
        ValueError: Si aucun encodage ne fonctionne.
    """
    for encodage in ("utf-8", "latin-1", "windows-1252"):
        try:
            chemin.read_text(encoding=encodage)
            return encodage
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Impossible de decoder le fichier {chemin}")


def archiver_fichier(
    source: Path, dest_dir: Path, nombre_transactions: int = 0
) -> Path:
    """Archive un fichier importe dans data/processed/YYYY-MM-DD/.

    Cree un fichier .meta.json avec les informations d'import.

    Args:
        source: Le chemin du fichier source a archiver.
        dest_dir: Le repertoire de base pour l'archivage (ex: data/processed/).
        nombre_transactions: Le nombre de transactions extraites du fichier.

    Returns:
        Le chemin du fichier archive.
    """
    today = date.today().isoformat()
    dossier = dest_dir / today
    dossier.mkdir(parents=True, exist_ok=True)

    dest = dossier / source.name
    shutil.copy2(source, dest)

    # Calculer le hash SHA-256 du fichier source
    sha256 = hashlib.sha256(source.read_bytes()).hexdigest()

    meta = {
        "date_import": datetime.now().isoformat(),
        "hash_sha256": sha256,
        "chemin_original": str(source.resolve()),
        "nombre_transactions": nombre_transactions,
    }

    meta_path = dest.with_suffix(dest.suffix + ".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return dest
