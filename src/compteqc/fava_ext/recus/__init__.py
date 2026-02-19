"""Extension Fava: Televersement de recus et factures.

Fournit une zone de glisser-deposer pour telecharger des recus/factures.
Se branche sur le module Phase 5 compteqc.documents.upload pour l'extraction
automatique quand il est disponible.
"""

from __future__ import annotations

from pathlib import Path

from flask import request
from fava.core import FavaLedger
from fava.ext import FavaExtensionBase, extension_endpoint


# ---------------------------------------------------------------------------
# Extension
# ---------------------------------------------------------------------------

class RecusExtension(FavaExtensionBase):
    """Televersement de recus et factures avec extraction IA."""

    report_title = "Recus"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._upload_disponible: bool = False
        self._recent_uploads: list[dict] = []

    def after_load_file(self) -> None:
        """Verifie la disponibilite du module Phase 5 et charge les recus recents."""
        try:
            from compteqc.documents.upload import telecharger_recu  # noqa: F401
            from compteqc.documents.extraction import extraire_recu  # noqa: F401
            self._upload_disponible = True
        except (ImportError, Exception):
            self._upload_disponible = False

        # Scanner les entrees recentes avec document directive
        self._recent_uploads = self._charger_recents()

    def _charger_recents(self) -> list[dict]:
        """Charge les 10 derniers fichiers du repertoire documents/."""
        from datetime import datetime

        recents: list[dict] = []
        try:
            ledger_path = Path(self.ledger.beancount_file_path)
            documents_dir = ledger_path.parent / "documents"
            if not documents_dir.exists():
                return recents
            fichiers = sorted(
                documents_dir.rglob("*"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            for f in fichiers:
                if f.is_file() and f.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".heic"}:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    recents.append({
                        "date": mtime.strftime("%Y-%m-%d %H:%M"),
                        "filename": f.name,
                        "chemin": str(f.relative_to(documents_dir)),
                    })
                    if len(recents) >= 10:
                        break
        except Exception:
            pass
        return recents

    def upload_disponible(self) -> bool:
        """Retourne True si le module d'upload Phase 5 est disponible."""
        return self._upload_disponible

    def recent_uploads(self) -> list[dict]:
        """Retourne la liste des recus recents."""
        return self._recent_uploads

    @extension_endpoint("upload", ["POST"])
    def upload(self) -> str:
        """Endpoint POST pour telecharger un fichier."""
        fichier = request.files.get("fichier")

        if not fichier or not fichier.filename:
            return (
                '<html><body>'
                '<h2>Erreur</h2>'
                '<p>Aucun fichier selectionne.</p>'
                '<a href="javascript:history.back()">Retour</a>'
                '</body></html>'
            )

        ledger_path = Path(self.ledger.beancount_file_path)
        documents_dir = ledger_path.parent / "documents"
        documents_dir.mkdir(parents=True, exist_ok=True)

        dest = documents_dir / fichier.filename
        fichier.save(str(dest))

        if self._upload_disponible:
            try:
                from compteqc.documents.upload import telecharger_recu
                from compteqc.documents.extraction import extraire_recu

                ledger_dir = ledger_path.parent
                stored = telecharger_recu(dest, ledger_dir)
                donnees = extraire_recu(stored)

                # Recharger le ledger
                self.ledger.load_file()

                return (
                    '<html><body>'
                    f'<h2>Fichier telecharge et analyse</h2>'
                    f'<p>Fichier : {fichier.filename}</p>'
                    f'<p>Donnees extraites : {donnees}</p>'
                    '<a href="javascript:history.back()">Retour</a>'
                    '</body></html>'
                )
            except Exception as e:
                # Fallback si l'extraction echoue
                self.ledger.load_file()
                return (
                    '<html><body>'
                    f'<h2>Fichier enregistre (extraction echouee)</h2>'
                    f'<p>Fichier : {fichier.filename}</p>'
                    f'<p>Erreur : {e}</p>'
                    '<a href="javascript:history.back()">Retour</a>'
                    '</body></html>'
                )
        else:
            # Phase 5 non disponible -- enregistrer seulement
            self.ledger.load_file()
            return (
                '<html><body>'
                f'<h2>Fichier enregistre</h2>'
                f'<p>Fichier : {fichier.filename}</p>'
                '<p>L\'extraction automatique sera disponible dans la Phase 5.</p>'
                '<a href="javascript:history.back()">Retour</a>'
                '</body></html>'
            )
