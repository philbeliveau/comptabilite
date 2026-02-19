"""Extension Fava: Export CPA (stub pour Phase 5).

Placeholder pour la generation du package complet pour le comptable.
L'implementation reelle sera faite dans la Phase 5.
"""

from __future__ import annotations

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase


class ExportCPAExtension(FavaExtensionBase):
    """Stub pour l'export CPA -- implementation Phase 5."""

    report_title = "Export CPA"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)

    def after_load_file(self) -> None:
        """Stub -- rien a charger pour le moment."""
        pass
