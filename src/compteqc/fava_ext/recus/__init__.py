"""Extension Fava: Televersement de recus et factures.

Fournit une zone de glisser-deposer pour telecharger des recus/factures.
Se branche sur le module Phase 5 compteqc.documents.upload pour l'extraction
automatique quand il est disponible.  Apres extraction, propose des
correspondances avec les transactions existantes et permet de lier un recu
a une transaction via une directive document Beancount.
"""

from __future__ import annotations

from pathlib import Path

from flask import g, request
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
                from compteqc.documents.upload import telecharger_recu, renommer_recu
                from compteqc.documents.extraction import extraire_recu
                from compteqc.documents.matching import proposer_correspondances

                ledger_dir = ledger_path.parent
                stored = telecharger_recu(dest, ledger_dir)
                donnees = extraire_recu(stored)

                # Renommer avec le slug fournisseur
                renamed = renommer_recu(stored, donnees)
                chemin_relatif = renamed.relative_to(ledger_path.parent)

                # Proposer des correspondances
                correspondances = proposer_correspondances(
                    donnees, self.ledger.all_entries,
                )

                # Recharger le ledger
                self.ledger.load_file()

                # Construire l'URL du endpoint /link
                link_url = f"/{g.beancount_file_slug}/extension/{self.name}/link"

                return self._html_correspondances(
                    fichier.filename,
                    donnees,
                    chemin_relatif,
                    correspondances,
                    link_url,
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

    # ------------------------------------------------------------------
    # HTML builder for match results
    # ------------------------------------------------------------------

    def _html_correspondances(
        self,
        nom_fichier: str,
        donnees,  # DonneesRecu
        chemin_relatif: Path,
        correspondances: list,  # list[Correspondance]
        link_url: str,
    ) -> str:
        """Construit la page HTML montrant les correspondances proposees."""
        from html import escape
        from beancount.core import data as beancount_data

        html_parts: list[str] = [
            "<html><head>",
            "<style>",
            ".cqc-card{border:1px solid #ddd;border-radius:8px;padding:16px;margin:12px 0;background:#fafafa}",
            ".cqc-table{width:100%;border-collapse:collapse;margin:12px 0}",
            ".cqc-table th,.cqc-table td{border:1px solid #ddd;padding:8px;text-align:left}",
            ".cqc-table th{background:#f5f5f5}",
            ".cqc-btn{display:inline-block;padding:6px 14px;background:#4a90d9;color:#fff;"
            "border:none;border-radius:4px;cursor:pointer;font-size:0.9em}",
            ".cqc-btn:hover{background:#357abd}",
            "a.cqc-back{display:inline-block;margin-top:12px;color:#4a90d9;text-decoration:none}",
            "</style>",
            "</head><body>",
            '<div class="cqc-card">',
            f"<h2>Recu telecharge et analyse</h2>",
            f"<p><strong>Fichier :</strong> {escape(nom_fichier)}</p>",
            f"<p><strong>Fournisseur :</strong> {escape(str(donnees.fournisseur))}</p>",
            f"<p><strong>Date :</strong> {escape(str(donnees.date))}</p>",
            f"<p><strong>Total :</strong> {donnees.total} $</p>",
            "</div>",
        ]

        if correspondances:
            html_parts.append("<h3>Correspondances proposees</h3>")
            html_parts.append('<table class="cqc-table">')
            html_parts.append(
                "<thead><tr>"
                "<th>Date</th><th>Narration</th><th>Montant</th>"
                "<th>Score</th><th>Action</th>"
                "</tr></thead><tbody>"
            )

            entries = self.ledger.all_entries
            for corr in correspondances:
                # Trouver le compte du premier posting
                compte = ""
                if corr.transaction_index < len(entries):
                    entry = entries[corr.transaction_index]
                    if (
                        isinstance(entry, beancount_data.Transaction)
                        and entry.postings
                    ):
                        compte = entry.postings[0].account

                # Calculer le hash de l'entree pour l'API Fava
                entry_hash = ""
                if corr.transaction_index < len(entries):
                    entry = entries[corr.transaction_index]
                    if isinstance(entry, beancount_data.Transaction):
                        from fava.beans.funcs import hash_entry
                        entry_hash = hash_entry(entry)

                score_pct = f"{corr.score * 100:.0f}%"
                html_parts.append(
                    "<tr>"
                    f"<td>{escape(str(corr.date))}</td>"
                    f"<td>{escape(corr.narration)}</td>"
                    f"<td>{corr.montant} $</td>"
                    f"<td>{score_pct}</td>"
                    "<td>"
                    f'<form method="POST" action="{escape(link_url)}" style="margin:0">'
                    f'<input type="hidden" name="chemin_recu" value="{escape(str(chemin_relatif))}">'
                    f'<input type="hidden" name="entry_hash" value="{escape(entry_hash)}">'
                    f'<input type="hidden" name="date_txn" value="{escape(str(corr.date))}">'
                    f'<input type="hidden" name="compte" value="{escape(compte)}">'
                    '<button type="submit" class="cqc-btn">Lier</button>'
                    "</form>"
                    "</td>"
                    "</tr>"
                )

            html_parts.append("</tbody></table>")
        else:
            html_parts.append(
                '<div class="cqc-card">'
                "<p>Aucune correspondance trouvee parmi les transactions existantes.</p>"
                "</div>"
            )

        html_parts.append(
            '<a class="cqc-back" href="javascript:history.back()">&#8592; Retour</a>'
        )
        html_parts.append("</body></html>")
        return "\n".join(html_parts)

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
