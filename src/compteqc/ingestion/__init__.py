"""Module d'ingestion de donnees bancaires pour CompteQC."""

from compteqc.ingestion.normalisation import archiver_fichier
from compteqc.ingestion.rbc_carte import RBCCarteImporter
from compteqc.ingestion.rbc_cheques import RBCChequesImporter
from compteqc.ingestion.rbc_ofx import RBCOfxImporter

__all__ = [
    "RBCChequesImporter",
    "RBCCarteImporter",
    "RBCOfxImporter",
    "archiver_fichier",
]
