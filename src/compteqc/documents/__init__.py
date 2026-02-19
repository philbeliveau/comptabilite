"""Module de gestion des documents (recus, factures) pour CompteQC.

Pipeline: telecharger -> extraire -> proposer correspondances -> lier dans Beancount.
"""

from __future__ import annotations

from compteqc.documents.beancount_link import ecrire_directive, generer_directive_document
from compteqc.documents.extraction import DonneesRecu, extraire_recu
from compteqc.documents.matching import Correspondance, proposer_correspondances
from compteqc.documents.upload import renommer_recu, telecharger_recu

__all__ = [
    "DonneesRecu",
    "Correspondance",
    "telecharger_recu",
    "renommer_recu",
    "extraire_recu",
    "proposer_correspondances",
    "generer_directive_document",
    "ecrire_directive",
]
