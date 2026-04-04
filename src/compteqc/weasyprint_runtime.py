"""Bootstrap runtime for WeasyPrint native libraries on macOS."""

from __future__ import annotations

import os
import platform
from pathlib import Path


def prepare_weasyprint_runtime() -> None:
    """Expose Homebrew libraries so WeasyPrint can load GTK/Pango on macOS."""
    if platform.system() != "Darwin":
        return

    homebrew_lib = Path("/opt/homebrew/lib")
    if not homebrew_lib.exists():
        return

    current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    chemins = [path for path in current.split(":") if path]
    if str(homebrew_lib) not in chemins:
        chemins.insert(0, str(homebrew_lib))
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(chemins)
