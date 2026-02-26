"""Extension Fava: Centre d'operations CompteQC.

Expose toutes les commandes CLI via le navigateur: import de fichiers
bancaires, re-entrainement ML, journal auto-approuve, et liens vers
les autres onglets et rapports Fava.
"""

from __future__ import annotations

import copy
import logging
import tempfile
from decimal import Decimal
from pathlib import Path

from flask import g, jsonify, request

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase, extension_endpoint

logger = logging.getLogger(__name__)


class OperationsExtension(FavaExtensionBase):
    """Centre d'operations -- launchpad pour toutes les commandes CompteQC."""

    report_title = "Operations"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)

    # ------------------------------------------------------------------
    # Helper: tab URLs for template links
    # ------------------------------------------------------------------

    def tab_urls(self) -> dict[str, str]:
        """Retourne un dict de noms d'onglets vers leurs URLs Fava."""
        slug = g.beancount_file_slug

        urls: dict[str, str] = {
            # Extensions CompteQC
            "approbation": f"/{slug}/extension/ApprobationExtension/",
            "paie_qc": f"/{slug}/extension/PaieQCExtension/",
            "recus": f"/{slug}/extension/RecusExtension/",
            "export_cpa": f"/{slug}/extension/ExportCPAExtension/",
            "echeances": f"/{slug}/extension/EcheancesExtension/",
            "taxes_qc": f"/{slug}/extension/TaxesQCExtension/",
            "dpa_qc": f"/{slug}/extension/DpaQCExtension/",
            "pret_actionnaire": f"/{slug}/extension/PretActionnaireExtension/",
            # Rapports Fava natifs
            "trial_balance": f"/{slug}/trial_balance/",
            "income_statement": f"/{slug}/income_statement/",
            "balance_sheet": f"/{slug}/balance_sheet/",
        }
        return urls

    # ------------------------------------------------------------------
    # POST /import -- Import de fichier bancaire
    # ------------------------------------------------------------------

    @extension_endpoint("import", ["POST"])
    def import_fichier(self):
        """Importe un fichier bancaire CSV/OFX dans le ledger."""
        try:
            fichier = request.files.get("fichier")
            if not fichier or not fichier.filename:
                return jsonify({"status": "error", "message": "Aucun fichier selectionne."}), 400

            compte = request.form.get("compte", "AUTO").upper()
            source_type = request.form.get("source_type", "corporate")

            if source_type not in ("corporate", "personal"):
                return jsonify({"status": "error", "message": f"source_type invalide: {source_type}"}), 400

            # Sauvegarder dans un fichier temporaire
            suffix = Path(fichier.filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                fichier.save(tmp)
                tmp_path = Path(tmp.name)

            # Chemins du ledger
            chemin_main = Path(self.ledger.beancount_file_path)
            chemin_regles = chemin_main.parent.parent / "rules" / "categorisation.yaml"

            # Charger les entrees existantes pour deduplication
            from beancount import loader
            entries_existantes, _errors, _options = loader.load_file(str(chemin_main))

            # Detecter les importateurs
            from compteqc.cli.importer import _detecter_importateurs, _importer_avec

            try:
                importateurs = _detecter_importateurs(str(tmp_path), compte)
            except SystemExit:
                return jsonify({"status": "error", "message": "Format de fichier non reconnu."}), 400

            total_importees = 0
            total_regles = 0
            total_ia_auto = 0
            total_pending = 0

            for imp in importateurs:
                nb_imp, nb_reg, nb_ia, nb_pend = _importer_avec(
                    imp, tmp_path, chemin_main, chemin_regles,
                    entries_existantes, source_type=source_type,
                )
                total_importees += nb_imp
                total_regles += nb_reg
                total_ia_auto += nb_ia
                total_pending += nb_pend

                # Recharger pour le prochain importateur
                if nb_imp > 0:
                    entries_existantes, _errors, _options = loader.load_file(str(chemin_main))

            # Nettoyer le fichier temporaire
            try:
                tmp_path.unlink()
            except OSError:
                pass

            # Recharger le ledger Fava
            self.ledger.load_file()

            return jsonify({
                "status": "ok",
                "importees": total_importees,
                "regles": total_regles,
                "ia_auto": total_ia_auto,
                "pending": total_pending,
            })

        except Exception as e:
            logger.exception("Erreur lors de l'import")
            return jsonify({"status": "error", "message": str(e)}), 500

    # ------------------------------------------------------------------
    # POST /retrain -- Re-entrainement du modele ML
    # ------------------------------------------------------------------

    @extension_endpoint("retrain", ["POST"])
    def retrain(self):
        """Re-entraine le modele ML depuis les transactions approuvees."""
        try:
            from beancount.core import data as beancount_data
            from compteqc.categorisation.ml import PredicteurML

            entries = self.ledger.all_entries

            # Extraire les donnees d'entrainement
            donnees: list[tuple[str, str, str]] = []
            for entry in entries:
                if not isinstance(entry, beancount_data.Transaction):
                    continue
                if entry.flag != "*":
                    continue
                if "pending" in (entry.tags or set()):
                    continue
                payee = entry.payee or ""
                narration = entry.narration or ""
                for posting in entry.postings:
                    if (
                        posting.account.startswith("Depenses:")
                        and posting.account != "Depenses:Non-Classe"
                    ):
                        donnees.append((payee, narration, posting.account))
                        break

            if not donnees:
                return jsonify({
                    "status": "warning",
                    "message": "Aucune donnee d'entrainement trouvee.",
                })

            predicteur = PredicteurML()
            predicteur.entrainer(donnees)

            if not predicteur.est_entraine:
                return jsonify({
                    "status": "warning",
                    "message": f"Donnees insuffisantes: {len(donnees)} transactions "
                               f"(minimum {PredicteurML.MIN_TRAINING_SIZE}).",
                })

            # Sauvegarder le modele
            import joblib
            chemin_modele = Path("data/ml/modele.pkl")
            chemin_modele.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(predicteur, chemin_modele)

            comptes = set(c for _, _, c in donnees)
            return jsonify({
                "status": "ok",
                "transactions": len(donnees),
                "comptes": len(comptes),
            })

        except Exception as e:
            logger.exception("Erreur lors du retrain")
            return jsonify({"status": "error", "message": str(e)}), 500

    # ------------------------------------------------------------------
    # GET /journal -- Transactions auto-approuvees recentes
    # ------------------------------------------------------------------

    @extension_endpoint("journal", ["GET"])
    def journal(self):
        """Retourne les transactions auto-approuvees (confiance >= 0.95)."""
        try:
            from beancount.core import data as beancount_data

            entries = self.ledger.all_entries
            resultats: list[dict] = []

            for entry in reversed(entries):
                if not isinstance(entry, beancount_data.Transaction):
                    continue
                meta = entry.meta or {}
                confiance_str = meta.get("confiance", "")
                categorisation = meta.get("categorisation", "")

                if categorisation not in ("ml", "llm"):
                    continue
                try:
                    confiance = float(confiance_str)
                except (ValueError, TypeError):
                    continue
                if confiance < 0.95:
                    continue
                if "pending" in (entry.tags or set()):
                    continue

                # Calculer le montant (premier posting expense)
                montant = Decimal(0)
                compte = ""
                for posting in entry.postings:
                    if posting.account.startswith("Depenses:") or posting.account == "Passifs:Pret-Actionnaire":
                        montant = posting.units.number if posting.units else Decimal(0)
                        compte = posting.account
                        break

                resultats.append({
                    "date": str(entry.date),
                    "payee": entry.payee or "",
                    "narration": entry.narration or "",
                    "montant": str(montant),
                    "compte": compte,
                    "confiance": str(confiance),
                    "source": categorisation,
                })

                if len(resultats) >= 50:
                    break

            return jsonify(resultats)

        except Exception as e:
            logger.exception("Erreur lors du chargement du journal")
            return jsonify({"status": "error", "message": str(e)}), 500
