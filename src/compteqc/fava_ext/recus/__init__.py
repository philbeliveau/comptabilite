"""Extension Fava: Televersement de recus et factures.

Fournit une zone de glisser-deposer pour telecharger des recus/factures.
Se branche sur le module Phase 5 compteqc.documents.upload pour l'extraction
automatique quand il est disponible.  Apres extraction, propose des
correspondances avec les transactions existantes et permet de lier un recu
a une transaction via une directive document Beancount.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from beancount.core import data as beancount_data
from beancount.core.data import Document, new_metadata
from fava.beans.funcs import hash_entry
from fava.core import FavaLedger
from fava.core.file import get_entry_slice
from fava.ext import FavaExtensionBase, extension_endpoint
from flask import g, jsonify, request
from werkzeug.utils import redirect

from compteqc.documents.extraction import DonneesRecu
from compteqc.documents.prefill_depenses import suggerer_prefill_ap_depense
from compteqc.documents.registre import DocumentFiscal, RegistreDocumentsFiscaux
from compteqc.quebec.taxes import (
    calculer_resume_taxes_revenu,
    determiner_traitement_document_revenu,
    preparer_normalisation_transaction_revenu,
    proposer_correspondances_revenu,
    transaction_reference,
)

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
        self._revenue_review_items: list[dict] = []

    def after_load_file(self) -> None:
        """Verifie la disponibilite du module Phase 5 et charge les recus recents."""
        try:
            from compteqc.documents.extraction import extraire_recu  # noqa: F401
            from compteqc.documents.upload import telecharger_recu  # noqa: F401
            self._upload_disponible = True
        except (ImportError, Exception):
            self._upload_disponible = False

        # Scanner les entrees recentes avec document directive
        self._recent_uploads = self._charger_recents()
        self._revenue_review_items = self._charger_revue_revenus()

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

    def revenue_review_items(self) -> list[dict]:
        """Documents de revenu restant a revoir."""
        return self._revenue_review_items

    def ui_message(self) -> dict | None:
        """Message de retour simple apres action."""
        message = request.args.get("message", "").strip()
        if not message:
            return None
        return {
            "niveau": request.args.get("niveau", "info"),
            "texte": message,
        }

    @staticmethod
    def _detect_file_type(filename: str) -> str:
        """Determine file_type from extension."""
        ext = Path(filename).suffix.lower()
        if ext in {".jpg", ".jpeg", ".png"}:
            return "image"
        if ext == ".pdf":
            return "pdf"
        return "other"

    def _registry(self) -> RegistreDocumentsFiscaux:
        ledger_path = Path(self.ledger.beancount_file_path)
        return RegistreDocumentsFiscaux(ledger_path.parent / "documents" / "registre.yaml")

    def _charger_revue_revenus(self) -> list[dict]:
        try:
            items = []
            for document in self._registry().lister_revenus():
                if (
                    document.normalization_status not in {"unmatched", "matched_needs_review"}
                    and not document.review_reason
                ):
                    continue
                items.append(
                    {
                        "id": document.id,
                        "date": document.date,
                        "fournisseur": document.fournisseur,
                        "total": document.total,
                        "status": document.normalization_status,
                        "review_reason": document.review_reason or "",
                    }
                )
            items.sort(key=lambda item: (item["date"], item["fournisseur"]), reverse=True)
            return items[:10]
        except Exception:
            return []

    def _find_entry_by_reference(self, reference: str):
        for entry in self.ledger.all_entries:
            if (
                isinstance(entry, beancount_data.Transaction)
                and transaction_reference(entry) == reference
            ):
                return entry
        return None

    def _build_extracted_payload(self, document: DocumentFiscal) -> dict:
        return {
            "document_id": document.id,
            "fournisseur": document.fournisseur,
            "date": document.date,
            "total": str(document.total),
            "sous_total": str(document.sous_total),
            "montant_tps": str(document.montant_tps) if document.montant_tps is not None else None,
            "montant_tvq": str(document.montant_tvq) if document.montant_tvq is not None else None,
            "description": document.description or "",
            "confiance": round(float(document.confiance), 4),
            "document_kind": document.document_kind,
            "pricing_mode": document.pricing_mode,
            "normalization_status": document.normalization_status,
            "traitement_taxes": document.traitement_taxes,
            "review_reason": document.review_reason,
        }

    def _build_ar_prefill_url(self, document: DocumentFiscal) -> str | None:
        resultat = calculer_resume_taxes_revenu(document)
        if resultat.resume is None:
            return None

        base_url = f"/{g.beancount_file_slug}/extension/ComptesFournisseursExtension/"
        params = {
            "prefill": "1",
            "tab": "ar",
            "nom_client": document.fournisseur,
            "date": document.date if document.date != "UNKNOWN" else "",
            "description": document.description or "Service",
            "montant": str(resultat.resume.sous_total),
            "tps_applicable": "1" if resultat.resume.tps > 0 else "0",
            "tvq_applicable": "1" if resultat.resume.tvq > 0 else "0",
            "notes": f"Document revenu {document.nom_fichier}",
        }
        query = urlencode(
            {
                cle: valeur
                for cle, valeur in params.items()
                if valeur not in {"", None}
            }
        )
        return f"{base_url}?{query}"

    def _build_ap_prefill_url(self, donnees: DonneesRecu) -> tuple[str, dict]:
        suggestion = suggerer_prefill_ap_depense(donnees)
        base_url = f"/{g.beancount_file_slug}/extension/ComptesFournisseursExtension/"
        notes = suggestion.note or ""
        params = {
            "prefill": "1",
            "tab": "ap",
            "fournisseur": donnees.fournisseur,
            "date": donnees.date if donnees.date != "UNKNOWN" else "",
            "montant": str(suggestion.montant_ht),
            "description": donnees.description or "",
            "taux_itc": str(suggestion.taux_itc),
            "taux_itr": str(suggestion.taux_itr),
            "notes": notes,
        }
        if suggestion.categorie_depense:
            params["categorie"] = suggestion.categorie_depense
        if suggestion.tps_applicable:
            params["tps"] = str(donnees.montant_tps or "")
        if suggestion.tvq_applicable:
            params["tvq"] = str(donnees.montant_tvq or "")

        query = urlencode(
            {
                cle: valeur
                for cle, valeur in params.items()
                if valeur not in {"", None}
            }
        )
        return (
            f"{base_url}?{query}",
            {
                "categorie_depense": suggestion.categorie_depense,
                "montant_ht": str(suggestion.montant_ht),
                "taux_itc": str(suggestion.taux_itc),
                "taux_itr": str(suggestion.taux_itr),
                "allocation_ratio": str(suggestion.allocation_ratio),
                "note": suggestion.note,
                "justification": suggestion.justification,
            },
        )

    def _insert_document_directive(
        self,
        chemin_recu: str,
        entry: beancount_data.Transaction,
    ) -> None:
        compte_document = ""
        for posting in entry.postings:
            if posting.account.startswith("Actifs:Banque"):
                compte_document = posting.account
                break
        if not compte_document and entry.postings:
            compte_document = entry.postings[0].account
        if not compte_document:
            return

        ledger_dir = Path(self.ledger.beancount_file_path).parent
        chemin_absolu = str(ledger_dir / chemin_recu)
        for existing in self.ledger.all_entries:
            if (
                isinstance(existing, Document)
                and existing.date == entry.date
                and existing.account == compte_document
                and existing.filename == chemin_absolu
            ):
                return
        meta = new_metadata("<compteqc>", 0)
        doc = Document(meta, entry.date, compte_document, chemin_absolu, set(), set())
        self.ledger.file.insert_entries([doc])

    @staticmethod
    def _entry_has_document_metadata(
        entry: beancount_data.Transaction,
        chemin_recu: str,
    ) -> bool:
        return entry.meta.get("document") == chemin_recu

    @staticmethod
    def _entry_slice_est_safely_rewritable(source_slice: str) -> bool:
        # Avoid printer-based rewrites when the original slice contains comments,
        # because they would be lost by round-tripping through the Beancount AST.
        return ";" not in source_slice

    @extension_endpoint("upload", ["POST"])
    def upload(self):
        """Endpoint POST pour telecharger un fichier -- retourne JSON."""
        fichier = request.files.get("fichier")
        document_kind = request.form.get("document_kind", "expense").strip() or "expense"
        pricing_mode = request.form.get("pricing_mode", "").strip()
        if document_kind not in {"expense", "revenue"}:
            return jsonify({"status": "error", "message": "Type de document invalide."}), 400
        if document_kind == "expense":
            pricing_mode = "explicit_tax_lines"
        elif pricing_mode not in {"tax_included", "pre_tax", "explicit_tax_lines", "unknown"}:
            return jsonify({"status": "error", "message": "Mode de prix invalide."}), 400

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
                from compteqc.documents.extraction import extraire_recu
                from compteqc.documents.matching import proposer_correspondances
                from compteqc.documents.upload import renommer_recu, telecharger_recu

                ledger_dir = ledger_path.parent
                stored = telecharger_recu(dest, ledger_dir)
                donnees = extraire_recu(stored, document_kind=document_kind)

                # Renommer avec le slug fournisseur
                renamed = renommer_recu(stored, donnees)
                chemin_relatif = str(renamed.relative_to(ledger_path.parent))
                registre = self._registry()
                document = DocumentFiscal.depuis_extraction(
                    donnees,
                    chemin_document=chemin_relatif,
                    nom_fichier=renamed.name,
                    document_kind=document_kind,
                    pricing_mode=pricing_mode,
                )
                if document_kind == "revenue":
                    document.traitement_taxes = determiner_traitement_document_revenu(document)
                document = registre.ajouter(document)

                if document_kind == "revenue":
                    correspondances_revenus = proposer_correspondances_revenu(
                        document,
                        self.ledger.all_entries,
                    )
                    correspondances = []
                    for corr in correspondances_revenus:
                        entry = self._find_entry_by_reference(corr.transaction_ref)
                        correspondances.append({
                            "date": str(corr.date),
                            "narration": corr.narration,
                            "payee": corr.payee,
                            "montant": str(corr.montant),
                            "score": round(corr.score, 4),
                            "entry_hash": hash_entry(entry) if entry else "",
                            "transaction_ref": corr.transaction_ref,
                            "already_normalized": corr.already_normalized,
                            "needs_review": corr.needs_review,
                            "review_reason": corr.review_reason,
                            "compte": entry.postings[0].account if entry and entry.postings else "",
                        })
                else:
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
                if document_kind == "revenue":
                    corr_list = correspondances
                else:
                    for corr in correspondances:
                        compte = ""
                        entry_hash = ""
                        if corr.transaction_index < len(entries):
                            entry = entries[corr.transaction_index]
                            if isinstance(entry, beancount_data.Transaction):
                                if entry.postings:
                                    compte = entry.postings[0].account
                                entry_hash = hash_entry(entry)

                        corr_list.append({
                            "date": str(corr.date),
                            "narration": corr.narration,
                            "montant": str(corr.montant),
                            "score": round(corr.score, 4),
                            "entry_hash": entry_hash,
                            "compte": compte,
                        })

                extracted = self._build_extracted_payload(document)
                resume_revenu = None
                ap_prefill_url = None
                ap_prefill = None
                if document_kind == "revenue":
                    resultat_resume = calculer_resume_taxes_revenu(document)
                    if resultat_resume.resume is not None:
                        resume_revenu = {
                            "sous_total": str(resultat_resume.resume.sous_total),
                            "tps": str(resultat_resume.resume.tps),
                            "tvq": str(resultat_resume.resume.tvq),
                            "total": str(resultat_resume.resume.total),
                            "traitement": resultat_resume.resume.traitement,
                        }
                    elif resultat_resume.review_reason:
                        registre.mette_a_jour(
                            document.id,
                            normalization_status="matched_needs_review",
                            review_reason=resultat_resume.review_reason,
                        )
                        extracted["normalization_status"] = "matched_needs_review"
                        extracted["review_reason"] = resultat_resume.review_reason
                else:
                    ap_prefill_url, ap_prefill = self._build_ap_prefill_url(donnees)

                return jsonify({
                    "status": "ok",
                    "filename": filename,
                    "file_type": file_type,
                    "extracted": extracted,
                    "correspondances": corr_list,
                    "chemin_recu": chemin_relatif,
                    "link_url": link_url,
                    "resume_revenu": resume_revenu,
                    "ap_prefill_url": ap_prefill_url,
                    "ap_prefill": ap_prefill,
                    "ar_prefill_url": (
                        self._build_ar_prefill_url(document)
                        if document_kind == "revenue"
                        else None
                    ),
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
        from datetime import date

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
        entry = self.ledger.get_entry(entry_hash)
        if (
            isinstance(entry, beancount_data.Transaction)
            and not self._entry_has_document_metadata(entry, chemin_recu)
        ):
            self.ledger.file.insert_metadata(entry_hash, "document", chemin_recu)
        document = self._registry().trouver_par_chemin(chemin_recu)
        if document is not None and isinstance(entry, beancount_data.Transaction):
            self._registry().mettre_a_jour(
                document.id,
                matched_transaction_ref=transaction_reference(entry),
            )

        # 2. Inserer une directive document Beancount (clickable dans Fava)
        if date_str and compte:
            date_txn = date.fromisoformat(date_str)
            ledger_dir = Path(self.ledger.beancount_file_path).parent
            chemin_absolu = str(ledger_dir / chemin_recu)
            meta = new_metadata("<compteqc>", 0)
            doc = Document(meta, date_txn, compte, chemin_absolu, set(), set())
            self.ledger.file.insert_entries([doc])

        self.ledger.load_file()

        recus_url = f"/{g.beancount_file_slug}/extension/{self.name}/"
        return redirect(recus_url, code=303)

    @extension_endpoint("normaliser_revenu", ["POST"])
    def normaliser_revenu(self) -> str:
        """POST /normaliser_revenu -- reecrit un depot brut de revenu a partir du document."""
        document_id = request.form.get("document_id", "").strip()
        entry_hash = request.form.get("entry_hash", "").strip()
        score_str = request.form.get("score", "").strip()
        score = float(score_str) if score_str else None

        if not document_id or not entry_hash:
            return redirect(self._redirect_url("Parametres manquants.", "erreur"), code=303)

        registre = self._registry()
        document = registre.obtenir(document_id)
        if document is None:
            return redirect(self._redirect_url("Document introuvable.", "erreur"), code=303)

        entry = self.ledger.get_entry(entry_hash)
        if not isinstance(entry, beancount_data.Transaction):
            return redirect(
                self._redirect_url("Transaction cible introuvable.", "erreur"),
                code=303,
            )

        resultat = preparer_normalisation_transaction_revenu(document, entry, score=score)
        if resultat.status == "matched_and_normalized" and resultat.entry_source:
            source_slice, sha256sum = get_entry_slice(entry)
            if not self._entry_slice_est_safely_rewritable(source_slice):
                registre.mette_a_jour(
                    document.id,
                    normalization_status="matched_needs_review",
                    matched_transaction_ref=transaction_reference(entry),
                    review_reason=(
                        "La transaction contient des commentaires ou annotations non preservables "
                        "par la reecriture automatique; normalisation manuelle requise."
                    ),
                    traitement_taxes=(
                        resultat.resume.traitement
                        if resultat.resume
                        else document.traitement_taxes
                    ),
                )
                self.ledger.load_file()
                return redirect(
                    self._redirect_url(
                        "Reecriture automatique refusee pour preserver les annotations existantes.",
                        "attention",
                    ),
                    code=303,
                )
            self.ledger.file.save_entry_slice(entry_hash, resultat.entry_source, sha256sum)
            self._insert_document_directive(document.chemin_document, entry)
            registre.mette_a_jour(
                document.id,
                normalization_status="matched_and_normalized",
                matched_transaction_ref=transaction_reference(entry),
                traitement_taxes=(
                    resultat.resume.traitement
                    if resultat.resume
                    else document.traitement_taxes
                ),
                review_reason=None,
            )
            self.ledger.load_file()
            return redirect(self._redirect_url("Depot revenu normalise.", "info"), code=303)

        if resultat.status == "already_normalized":
            if not self._entry_has_document_metadata(entry, document.chemin_document):
                self.ledger.file.insert_metadata(entry_hash, "document", document.chemin_document)
            self._insert_document_directive(document.chemin_document, entry)
            registre.mette_a_jour(
                document.id,
                normalization_status="already_normalized",
                matched_transaction_ref=transaction_reference(entry),
                traitement_taxes=(
                    resultat.resume.traitement
                    if resultat.resume
                    else document.traitement_taxes
                ),
                review_reason=None,
            )
            self.ledger.load_file()
            return redirect(
                self._redirect_url("Transaction deja normalisee; document lie.", "info"),
                code=303,
            )

        registre.mette_a_jour(
            document.id,
            normalization_status="matched_needs_review",
            matched_transaction_ref=transaction_reference(entry),
            review_reason=resultat.review_reason,
            traitement_taxes=(
                resultat.resume.traitement
                if resultat.resume
                else document.traitement_taxes
            ),
        )
        self.ledger.load_file()
        return redirect(
            self._redirect_url(
                resultat.review_reason or "Revue manuelle requise.",
                "attention",
            ),
            code=303,
        )

    def _redirect_url(self, message: str, niveau: str) -> str:
        params = urlencode({"message": message, "niveau": niveau})
        return f"/{g.beancount_file_slug}/extension/{self.name}/?{params}"
