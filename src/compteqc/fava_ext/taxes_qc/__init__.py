"""Extension Fava: preparation trimestrielle des remises TPS/TVQ."""

from __future__ import annotations

import datetime
from decimal import Decimal

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase
from flask import g, has_request_context, request

from compteqc.quebec.taxes import (
    checklist_operateur_remise,
    lister_periodes_remise,
    preparer_remise_trimestrielle,
)


class TaxesQCExtension(FavaExtensionBase):
    """Vue operationnelle pour preparer la remise trimestrielle."""

    report_title = "Remise TPS/TVQ"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._date_reference = datetime.date.today()

    def after_load_file(self) -> None:
        """Garde une date de reference stable jusqu'au prochain reload."""
        self._date_reference = datetime.date.today()

    def preparation(self):
        """Retourne la preparation complete pour la periode selectionnee."""
        return preparer_remise_trimestrielle(
            self.ledger.all_entries,
            self._periode_code_selectionnee(),
            date_reference=self._date_reference,
            ledger_path=getattr(self.ledger, "beancount_file_path", None),
        )

    def period_options(self) -> list[dict]:
        """Construit la navigation par trimestre."""
        code_selectionne = self.preparation().periode.code
        options: list[dict] = []
        for periode in lister_periodes_remise(
            self.ledger.all_entries,
            date_reference=self._date_reference,
        ):
            options.append(
                {
                    "code": periode.code,
                    "label": periode.label,
                    "url": self._url_periode(periode.code),
                    "selected": periode.code == code_selectionne,
                    "est_terminee": periode.est_terminee,
                    "est_future": periode.est_future,
                }
            )
        return options

    def checklist(self) -> list[dict[str, str]]:
        """Checklist operateur rendue par le template."""
        return checklist_operateur_remise()

    def jours_avant_echeance(self) -> int:
        """Nombre de jours entre la date de reference et l'echeance."""
        preparation = self.preparation()
        return (preparation.periode.date_limite - self._date_reference).days

    def format_money(self, amount: Decimal) -> str:
        """Formate un montant CAD avec signe explicite."""
        return f"{amount:,.2f} $"

    def format_amount_class(self, amount: Decimal) -> str:
        """Classe CSS semantique pour les montants nets."""
        if amount > 0:
            return "cqc-positif"
        if amount < 0:
            return "cqc-negatif"
        return ""

    def warning_class(self, niveau: str) -> str:
        """Mappe un niveau de message vers la classe d'alerte."""
        mapping = {
            "attention": "cqc-alert-warning",
            "erreur": "cqc-alert-error",
            "info": "cqc-alert-info",
        }
        return mapping.get(niveau, "cqc-alert-info")

    def _periode_code_selectionnee(self) -> str | None:
        if has_request_context():
            code = request.args.get("periode", "").strip()
            return code or None
        return None

    def _url_periode(self, code: str) -> str:
        if not has_request_context():
            return f"?periode={code}"
        slug = g.beancount_file_slug
        return f"/{slug}/extension/TaxesQCExtension/?periode={code}"
