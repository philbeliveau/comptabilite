"""Extension Fava: Export CPA.

Affiche le perimetre d'un export CPA a partir du filtre Fava courant.
Le package complet n'est pas encore genere depuis l'UI, mais la page
permet de valider exactement quelles transactions seront incluses.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

from beancount.core import data as beancount_data
from flask import has_request_context, jsonify, request, send_file
from fava.core import FavaLedger
from fava.core.filters import AdvancedFilter, FilterError
from fava.ext import FavaExtensionBase, extension_endpoint

from compteqc.rapports.cpa_package import CpaPackageError, generer_package_cpa


class ExportCPAExtension(FavaExtensionBase):
    """Apercu filtre du perimetre d'export CPA."""

    report_title = "Export CPA"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)

    def after_load_file(self) -> None:
        """Aucun cache a preparer pour cet apercu."""

    def filtre_actif(self) -> str:
        """Retourne le filtre Fava passe dans l'URL courante."""
        if not has_request_context():
            return ""
        return (request.args.get("filter") or "").strip()

    def date_debut_active(self) -> str:
        """Retourne la date debut choisie dans l'URL courante."""
        if not has_request_context():
            return ""
        return (request.args.get("date_debut") or "").strip()

    def date_fin_active(self) -> str:
        """Retourne la date fin choisie dans l'URL courante."""
        if not has_request_context():
            return ""
        return (request.args.get("date_fin") or "").strip()

    @staticmethod
    def _parse_date(date_str: str) -> datetime.date | None:
        """Convertit une date ISO optionnelle."""
        if not date_str:
            return None
        return datetime.date.fromisoformat(date_str)

    def _filtre_transactions(
        self,
        filtre: str,
        date_debut: str = "",
        date_fin: str = "",
    ) -> list[beancount_data.Transaction]:
        """Filtre seulement les transactions, en preservant les autres directives."""
        transactions = [
            entry for entry in self.ledger.all_entries
            if isinstance(entry, beancount_data.Transaction)
        ]
        if filtre:
            transactions = list(AdvancedFilter(filtre).apply(transactions))

        debut = self._parse_date(date_debut)
        fin = self._parse_date(date_fin)
        if debut:
            transactions = [entry for entry in transactions if entry.date >= debut]
        if fin:
            transactions = [entry for entry in transactions if entry.date <= fin]
        return transactions

    def _entries_export(
        self,
        filtre: str,
        date_debut: str = "",
        date_fin: str = "",
    ) -> list[beancount_data.Directive]:
        """Retourne les entrees exportees avec directives de structure intactes."""
        transactions = self._filtre_transactions(filtre, date_debut, date_fin)
        autres_directives = [
            entry for entry in self.ledger.all_entries
            if not isinstance(entry, beancount_data.Transaction)
        ]
        return [*autres_directives, *transactions]

    def annee_par_defaut(self) -> int:
        """Infere l'annee a proposer dans le formulaire d'export."""
        filtre = self.filtre_actif()
        date_debut = self.date_debut_active()
        date_fin = self.date_fin_active()
        try:
            transactions = self._filtre_transactions(filtre, date_debut, date_fin)
        except (FilterError, ValueError):
            transactions = []
        if transactions:
            return max(entry.date.year for entry in transactions)
        if date_debut:
            return datetime.date.fromisoformat(date_debut).year
        if date_fin:
            return datetime.date.fromisoformat(date_fin).year
        return datetime.date.today().year

    @staticmethod
    def _montant_representatif(entry: beancount_data.Transaction) -> str:
        """Retourne le montant absolu le plus grand de la transaction."""
        plus_grand = Decimal("0")
        devise = "CAD"
        for posting in entry.postings:
            units = posting.units
            if units is None:
                continue
            valeur = abs(units.number)
            if valeur >= plus_grand:
                plus_grand = valeur
                devise = units.currency
        return f"{plus_grand:,.2f} {devise}"

    @staticmethod
    def _comptes_resume(entry: beancount_data.Transaction) -> str:
        """Retourne un resume compact des comptes touches."""
        comptes = [posting.account for posting in entry.postings]
        if len(comptes) <= 3:
            return ", ".join(comptes)
        return ", ".join(comptes[:3]) + f" +{len(comptes) - 3}"

    def export_context(self) -> dict[str, object]:
        """Construit le contexte rendu par le template d'export CPA."""
        filtre = self.filtre_actif()
        date_debut = self.date_debut_active()
        date_fin = self.date_fin_active()
        try:
            transactions = self._filtre_transactions(filtre, date_debut, date_fin)
        except (FilterError, ValueError) as exc:
            return {
                "filter": filtre,
                "date_debut": date_debut,
                "date_fin": date_fin,
                "error": str(exc),
                "transactions": [],
                "count": 0,
                "sources": [],
                "date_debut": None,
                "date_fin": None,
                "preview_truncated": False,
                "annee_defaut": self.annee_par_defaut(),
            }

        lignes = [
            {
                "date": entry.date.isoformat(),
                "payee": entry.payee or "",
                "narration": entry.narration or "",
                "fichier_source": (entry.meta or {}).get("fichier_source", ""),
                "montant": self._montant_representatif(entry),
                "comptes": self._comptes_resume(entry),
            }
            for entry in transactions[:200]
        ]
        sources = sorted(
            {
                fichier_source
                for entry in transactions
                if (fichier_source := (entry.meta or {}).get("fichier_source"))
            }
        )
        annee_defaut = (
            max(entry.date.year for entry in transactions)
            if transactions
            else self.annee_par_defaut()
        )
        return {
            "filter": filtre,
            "date_debut": date_debut or (transactions[0].date.isoformat() if transactions else ""),
            "date_fin": date_fin or (transactions[-1].date.isoformat() if transactions else ""),
            "error": "",
            "transactions": lignes,
            "count": len(transactions),
            "sources": sources,
            "preview_truncated": len(transactions) > len(lignes),
            "annee_defaut": annee_defaut,
        }

    @extension_endpoint("export", ["POST"])
    def export(self):
        """Genere le package CPA depuis le perimetre Fava courant et le telecharge."""
        try:
            annee = int((request.form.get("annee") or "").strip())
        except ValueError:
            return jsonify({"status": "error", "message": "Annee invalide."}), 400

        filtre = (request.form.get("filter") or "").strip()
        date_debut = (request.form.get("date_debut") or "").strip()
        date_fin = (request.form.get("date_fin") or "").strip()

        try:
            entries = self._entries_export(filtre, date_debut, date_fin)
        except (FilterError, ValueError) as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400

        if not any(isinstance(entry, beancount_data.Transaction) for entry in entries):
            return jsonify({
                "status": "error",
                "message": "Aucune transaction a exporter pour ce filtre.",
            }), 400

        ledger_dir = Path(self.ledger.beancount_file_path).resolve().parent
        output_dir = ledger_dir / "exports"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            zip_path = generer_package_cpa(
                entries=entries,
                annee=annee,
                output_dir=output_dir,
            )
        except CpaPackageError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400
        except Exception as exc:  # pragma: no cover - defensive path
            return jsonify({"status": "error", "message": str(exc)}), 500

        return send_file(
            zip_path,
            as_attachment=True,
            download_name=zip_path.name,
            mimetype="application/zip",
        )
