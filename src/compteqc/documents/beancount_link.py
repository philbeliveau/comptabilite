"""Generation de directives Beancount document pour lier recus aux transactions.

Produit des directives `document` au format Beancount standard et les
ecrit dans le fichier mensuel du ledger.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generer_directive_document(
    date: datetime.date,
    compte: str,
    chemin_fichier: str,
) -> str:
    """Genere une directive document Beancount.

    Args:
        date: Date de la directive.
        compte: Compte Beancount associe (ex: Depenses:Bureau:Fournitures).
        chemin_fichier: Chemin relatif au ledger root (ex: documents/2026/01/recu.jpg).

    Returns:
        Directive Beancount au format: YYYY-MM-DD document Compte "chemin"
    """
    return f'{date.isoformat()} document {compte} "{chemin_fichier}"'


def ecrire_directive(
    directive: str,
    ledger_dir: Path,
    annee: int,
    mois: int,
) -> Path:
    """Ajoute une directive document au fichier mensuel Beancount.

    Args:
        directive: La directive document a ecrire.
        ledger_dir: Repertoire racine du ledger.
        annee: Annee du fichier mensuel.
        mois: Mois du fichier mensuel.

    Returns:
        Chemin du fichier dans lequel la directive a ete ecrite.
    """
    fichier = ledger_dir / f"{annee}-{mois:02d}.beancount"

    # S'assurer que le fichier existe
    if not fichier.exists():
        logger.info("Creation du fichier mensuel: %s", fichier)
        fichier.touch()

    # Ajouter la directive avec un saut de ligne
    with open(fichier, "a", encoding="utf-8") as f:
        f.write(f"\n{directive}\n")

    logger.info("Directive document ecrite dans %s", fichier)
    return fichier
