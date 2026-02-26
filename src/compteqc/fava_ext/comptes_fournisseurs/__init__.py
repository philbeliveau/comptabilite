"""Extension Fava: Comptes a payer / a recevoir -- gestion AP/AR combinee.

Affiche les KPIs, listes de factures (AR) et factures fournisseurs (AP),
et un graphique de vieillissement par age.
"""

from __future__ import annotations

import datetime
import json
import logging
from decimal import Decimal
from pathlib import Path

from flask import request
from werkzeug.utils import redirect

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase, extension_endpoint

from compteqc.factures.modeles import Facture, LigneFacture, InvoiceStatus
from compteqc.factures.journal import generer_ecriture_facture
from compteqc.factures.registre import RegistreFactures
from compteqc.fournisseurs.registre import RegistreFournisseurs
from compteqc.vieillissement import (
    calculer_vieillissement_ar,
    calculer_vieillissement_ap,
)

logger = logging.getLogger(__name__)


class ComptesFournisseursExtension(FavaExtensionBase):
    """Gestion combinee des comptes a payer et a recevoir."""

    report_title = "Comptes a payer / a recevoir"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._registre_ar: RegistreFactures | None = None
        self._registre_ap: RegistreFournisseurs | None = None

    def after_load_file(self) -> None:
        """Recharge les registres AR et AP apres chargement du ledger."""
        try:
            self._registre_ar = RegistreFactures()
            self._registre_ap = RegistreFournisseurs()
        except Exception:
            logger.exception("Erreur lors du chargement des registres AP/AR")

    def kpis(self) -> dict:
        """KPI data for the header row: AR total, AR overdue, AP total, net position."""
        today = datetime.date.today()
        ar_impayees = [
            f for f in (self._registre_ar.lister() if self._registre_ar else [])
            if f.solde > 0
        ]
        ap_impayees = self._registre_ap.lister_impayees() if self._registre_ap else []

        ar_total = sum((f.solde for f in ar_impayees), Decimal("0"))
        ar_en_retard = [f for f in ar_impayees if today > f.date_echeance]
        ap_total = sum((f.solde for f in ap_impayees), Decimal("0"))

        return {
            "ar_total": ar_total,
            "ar_en_retard": sum((f.solde for f in ar_en_retard), Decimal("0")),
            "ar_en_retard_count": len(ar_en_retard),
            "ap_total": ap_total,
            "position_nette": ar_total - ap_total,
        }

    def factures_ar(self) -> list[dict]:
        """AR invoices with aging info for the table display."""
        if not self._registre_ar:
            return []
        today = datetime.date.today()
        result = []
        for f in self._registre_ar.lister():
            if f.solde <= 0:
                continue
            jours = (today - f.date_echeance).days
            if jours <= 30:
                age_class = "cqc-aging-current"
            elif jours <= 60:
                age_class = "cqc-aging-30-60"
            elif jours <= 90:
                age_class = "cqc-aging-60-90"
            else:
                age_class = "cqc-aging-90-plus"
            result.append({
                "numero": f.numero,
                "nom_client": f.nom_client,
                "date": f.date,
                "date_echeance": f.date_echeance,
                "total": f.total,
                "montant_paye": getattr(f, "montant_paye", Decimal("0")),
                "solde": f.solde,
                "statut": f.statut.value if hasattr(f.statut, "value") else str(f.statut),
                "jours_retard": max(jours, 0),
                "age_class": age_class,
            })
        return sorted(result, key=lambda x: x["date_echeance"])

    def factures_ap(self) -> list[dict]:
        """AP bills with aging info for the table display."""
        if not self._registre_ap:
            return []
        today = datetime.date.today()
        result = []
        for f in self._registre_ap.lister_impayees():
            if f.solde <= 0:
                continue
            jours = (today - f.date_echeance).days
            if jours <= 30:
                age_class = "cqc-aging-current"
            elif jours <= 60:
                age_class = "cqc-aging-30-60"
            elif jours <= 90:
                age_class = "cqc-aging-60-90"
            else:
                age_class = "cqc-aging-90-plus"
            result.append({
                "numero_interne": f.numero_interne,
                "fournisseur": f.fournisseur,
                "numero_reference": f.numero_reference,
                "date_facture": f.date_facture,
                "date_echeance": f.date_echeance,
                "total": f.total,
                "montant_paye": f.montant_paye,
                "solde": f.solde,
                "statut": f.statut.value if hasattr(f.statut, "value") else str(f.statut),
                "jours_retard": max(jours, 0),
                "age_class": age_class,
            })
        return sorted(result, key=lambda x: x["date_echeance"])

    def aging_chart_json(self) -> str:
        """JSON config for Chart.js horizontal stacked bar chart."""
        ar_factures = self._registre_ar.lister() if self._registre_ar else []
        ap_factures = self._registre_ap.lister_impayees() if self._registre_ap else []

        ar_aging = calculer_vieillissement_ar(ar_factures)
        ap_aging = calculer_vieillissement_ap(ap_factures)

        config = {
            "labels": ["Comptes clients (AR)", "Comptes fournisseurs (AP)"],
            "datasets": [
                {
                    "label": "Courant (0-30j)",
                    "data": [
                        float(ar_aging.totaux_par_tranche["0-30"]),
                        float(ap_aging.totaux_par_tranche["0-30"]),
                    ],
                    "backgroundColor": "#93C5FD",
                },
                {
                    "label": "31-60 jours",
                    "data": [
                        float(ar_aging.totaux_par_tranche["31-60"]),
                        float(ap_aging.totaux_par_tranche["31-60"]),
                    ],
                    "backgroundColor": "#3B82F6",
                },
                {
                    "label": "61-90 jours",
                    "data": [
                        float(ar_aging.totaux_par_tranche["61-90"]),
                        float(ap_aging.totaux_par_tranche["61-90"]),
                    ],
                    "backgroundColor": "#1D4ED8",
                },
                {
                    "label": "91+ jours",
                    "data": [
                        float(ar_aging.totaux_par_tranche["91+"]),
                        float(ap_aging.totaux_par_tranche["91+"]),
                    ],
                    "backgroundColor": "#1E3A5F",
                },
            ],
            "options": {
                "indexAxis": "y",
                "plugins": {
                    "tooltip": {
                        "callbacks": {
                            "label": "__CURRENCY_CALLBACK__",
                        },
                    },
                },
                "scales": {
                    "x": {
                        "stacked": True,
                        "ticks": {
                            "callback": "__DOLLAR_CALLBACK__",
                        },
                    },
                    "y": {
                        "stacked": True,
                    },
                },
            },
        }
        # Serialize to JSON; the callback placeholders are replaced in the template
        # with actual JS functions via the data-chart attribute processing.
        # For Chart.js canvas rendering, callbacks must be JS functions, not JSON strings.
        # We provide the data and options separately; the template handles JS callbacks.
        return json.dumps(config)

    def expense_accounts(self) -> list[str]:
        """List of expense accounts from the ledger for AP form category dropdown."""
        from beancount.core import data

        seen: set[str] = set()
        for entry in self.ledger.all_entries:
            if isinstance(entry, data.Open) and entry.account.startswith("Depenses:"):
                seen.add(entry.account)
        return sorted(seen)

    def client_names(self) -> list[str]:
        """List of unique client names from existing AR invoices for autocomplete."""
        if not self._registre_ar:
            return []
        return sorted(set(f.nom_client for f in self._registre_ar.lister() if f.nom_client))

    def vendor_names(self) -> list[str]:
        """List of unique vendor names from existing AP bills for autocomplete."""
        if not self._registre_ap:
            return []
        return sorted(set(f.fournisseur for f in self._registre_ap.lister() if f.fournisseur))

    def today_str(self) -> str:
        """Today's date as ISO string for form defaults."""
        return datetime.date.today().isoformat()

    def echeance_default_str(self) -> str:
        """Default due date (today + 30 days) as ISO string."""
        return (datetime.date.today() + datetime.timedelta(days=30)).isoformat()

    # ------------------------------------------------------------------
    # POST endpoints for invoice/bill creation
    # ------------------------------------------------------------------

    @extension_endpoint("creer_facture", ["POST"])
    def creer_facture(self):
        """POST: Create a new AR invoice from form data."""
        form = request.form

        # Parse client info
        nom_client = form.get("nom_client", "").strip()
        date_str = form.get("date", "")
        echeance_str = form.get("date_echeance", "")
        notes = form.get("notes", "")

        date_facture = datetime.date.fromisoformat(date_str)
        date_echeance = datetime.date.fromisoformat(echeance_str)

        # Parse dynamic line items (indexed: description_0, quantite_0, prix_unitaire_0, tps_0, tvq_0, ...)
        lignes: list[LigneFacture] = []
        i = 0
        while f"description_{i}" in form:
            desc = form.get(f"description_{i}", "").strip()
            qte = int(form.get(f"quantite_{i}", "1"))
            prix = Decimal(form.get(f"prix_unitaire_{i}", "0"))
            tps = f"tps_{i}" in form  # Checkbox: present = checked
            tvq = f"tvq_{i}" in form
            if desc and prix > 0:
                lignes.append(LigneFacture(
                    description=desc,
                    quantite=qte,
                    prix_unitaire=prix,
                    tps_applicable=tps,
                    tvq_applicable=tvq,
                ))
            i += 1

        if not lignes or not nom_client:
            return redirect(request.referrer or "/")

        # Create invoice
        registre = RegistreFactures()
        numero = registre.prochain_numero(date_facture.year)
        facture = Facture(
            numero=numero,
            nom_client=nom_client,
            date=date_facture,
            date_echeance=date_echeance,
            lignes=lignes,
            statut=InvoiceStatus.DRAFT,
            notes=notes,
        )
        registre.ajouter(facture)

        # Generate and append Beancount journal entry
        ecriture = generer_ecriture_facture(facture)
        ledger_path = Path(self.ledger.beancount_file_path)
        journal_path = ledger_path.parent / "factures" / "journal.beancount"
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        with open(journal_path, "a", encoding="utf-8") as f:
            f.write("\n" + ecriture + "\n")

        # Reload ledger to pick up new entry
        self.ledger.load_file()

        return redirect(request.referrer or "/")
