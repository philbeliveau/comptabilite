"""Extension Fava: Televersement de recus et factures.

Fournit une zone de glisser-deposer pour telecharger des recus/factures.
Se branche sur le module Phase 5 compteqc.documents.upload pour l'extraction
automatique quand il est disponible.  Apres extraction, propose des
correspondances avec les transactions existantes et permet de lier un recu
a une transaction via une directive document Beancount.
"""

from __future__ import annotations

from pathlib import Path

from flask import g, jsonify, request
from werkzeug.utils import redirect

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

    @staticmethod
    def _detect_file_type(filename: str) -> str:
        """Determine file_type from extension."""
        ext = Path(filename).suffix.lower()
        if ext in {".jpg", ".jpeg", ".png"}:
            return "image"
        if ext == ".pdf":
            return "pdf"
        return "other"

    @extension_endpoint("upload", ["POST"])
    def upload(self):
        """Endpoint POST pour telecharger un fichier -- retourne JSON."""
        fichier = request.files.get("fichier")

        if not fichier or not fichier.filename:
            return jsonify({"status": "error", "message": "Aucun fichier selectionne."}), 400

        filename = fichier.filename
        file_type = self._detect_file_type(filename)

        ledger_path = Path(self.ledger.beancount_file_path)
        documents_dir = ledger_path.parent / "documents"
        documents_dir.mkdir(parents=True, exist_ok=True)

        dest = documents_dir / filename
        fichier.save(str(dest))

        if self._upload_disponible:
            try:
                from compteqc.documents.upload import telecharger_recu, renommer_recu
                from compteqc.documents.extraction import extraire_recu
                from compteqc.documents.matching import proposer_correspondances
                from beancount.core import data as beancount_data

                ledger_dir = ledger_path.parent
                stored = telecharger_recu(dest, ledger_dir)
                donnees = extraire_recu(stored)

                # Renommer avec le slug fournisseur
                renamed = renommer_recu(stored, donnees)
                chemin_relatif = str(renamed.relative_to(ledger_path.parent))

                # Proposer des correspondances
                correspondances = proposer_correspondances(
                    donnees, self.ledger.all_entries,
                )

                # Recharger le ledger
                self.ledger.load_file()

                # Construire l'URL du endpoint /link
                link_url = f"/{g.beancount_file_slug}/extension/{self.name}/link"

                # Construire le tableau de correspondances
                entries = self.ledger.all_entries
                corr_list = []
                for corr in correspondances:
                    compte = ""
                    entry_hash = ""
                    if corr.transaction_index < len(entries):
                        entry = entries[corr.transaction_index]
                        if isinstance(entry, beancount_data.Transaction):
                            if entry.postings:
                                compte = entry.postings[0].account
                            from fava.beans.funcs import hash_entry
                            entry_hash = hash_entry(entry)

                    corr_list.append({
                        "date": str(corr.date),
                        "narration": corr.narration,
                        "montant": str(corr.montant),
                        "score": round(corr.score, 4),
                        "entry_hash": entry_hash,
                        "compte": compte,
                    })

                extracted = {
                    "fournisseur": str(donnees.fournisseur),
                    "date": str(donnees.date),
                    "total": str(donnees.total),
                    "confiance": round(float(getattr(donnees, "confiance", 0.0)), 4),
                }

                return jsonify({
                    "status": "ok",
                    "filename": filename,
                    "file_type": file_type,
                    "extracted": extracted,
                    "correspondances": corr_list,
                    "chemin_recu": chemin_relatif,
                    "link_url": link_url,
                })
            except Exception as e:
                # Fallback si l'extraction echoue
                self.ledger.load_file()
                return jsonify({
                    "status": "ok",
                    "filename": filename,
                    "file_type": file_type,
                    "extracted": None,
                    "error_extraction": str(e),
                    "correspondances": [],
                })
        else:
            # Phase 5 non disponible -- enregistrer seulement
            self.ledger.load_file()
            return jsonify({
                "status": "ok",
                "filename": filename,
                "file_type": file_type,
                "extracted": None,
                "correspondances": [],
            })

    # ------------------------------------------------------------------
    # /link endpoint -- lie un recu a une transaction
    # ------------------------------------------------------------------

    @extension_endpoint("link", ["POST"])
    def link(self) -> str:
        """POST /link -- lie un recu a une transaction via metadata + document directive."""
        import datetime

        chemin_recu = request.form.get("chemin_recu", "")
        entry_hash = request.form.get("entry_hash", "")
        date_str = request.form.get("date_txn", "")
        compte = request.form.get("compte", "")

        if not chemin_recu or not entry_hash:
            return (
                "<html><body>"
                "<h2>Erreur</h2>"
                "<p>Parametres manquants.</p>"
                '<a href="javascript:history.back()">Retour</a>'
                "</body></html>"
            )

        # 1. Ajouter metadata "document" sur la transaction
        self.ledger.file.insert_metadata(entry_hash, "document", chemin_recu)

        # 2. Inserer une directive document Beancount (clickable dans Fava)
        if date_str and compte:
            from beancount.core.data import Document, new_metadata
            date_txn = datetime.date.fromisoformat(date_str)
            ledger_dir = Path(self.ledger.beancount_file_path).parent
            chemin_absolu = str(ledger_dir / chemin_recu)
            meta = new_metadata("<compteqc>", 0)
            doc = Document(meta, date_txn, compte, chemin_absolu, set(), set())
            self.ledger.file.insert_entries([doc])

        self.ledger.load_file()

        recus_url = f"/{g.beancount_file_slug}/extension/{self.name}/"
        return redirect(recus_url, code=303)
