"""Extension Fava: Theme Quebec pour CompteQC.

Injecte un module JavaScript sur chaque page pour appliquer
le theme aux couleurs du Quebec (bleu #003DA5 + blanc) et
afficher le branding CompteQC / Philippe Beliveau.
"""

from __future__ import annotations

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase


class ThemeQCExtension(FavaExtensionBase):
    """Theme Quebec global pour CompteQC."""

    report_title = None  # Pas de page de rapport propre
    has_js_module = True

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
