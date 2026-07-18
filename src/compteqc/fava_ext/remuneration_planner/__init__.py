"""Extension Fava: planificateur de remuneration proprietaire."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase

from compteqc.planification.remuneration import (
    analyser_scenario,
    construire_courbe_salaire,
    data_brackets_json,
    moyenne_depenses_recurrentes,
    reserves_depuis_ledger,
    scenarios_defaut,
)


class RemunerationPlannerExtension(FavaExtensionBase):
    """Vue interactive pour scenarios salaire/remuneration."""

    report_title = "Compensation Planner"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._date_reference = dt.date.today()
        self._project_root = self._detecter_racine()
        self._depenses_mensuelles = Decimal("0.00")
        self._courbe_salaire: list[dict] = []
        self._reserve = None

    def after_load_file(self) -> None:
        """Recharge les donnees de planification au chargement Fava."""
        self._date_reference = dt.date.today()
        self._project_root = self._detecter_racine()
        monthly_path = (
            self._project_root
            / "data"
            / "personal-spending"
            / "personal-spending-monthly-2026.csv"
        )
        self._depenses_mensuelles = moyenne_depenses_recurrentes(monthly_path)
        ledger_path = Path(
            getattr(
                self.ledger,
                "beancount_file_path",
                self._project_root / "ledger" / "main.beancount",
            )
        )
        self._courbe_salaire = [
            {
                "gross": float(ligne.salaire_brut_annuel),
                "net": float(ligne.net_annuel),
                "deductions": float(ligne.retenues_employe_annuelles),
                "employer": float(ligne.cotisations_employeur_annuelles),
                "corporateCost": float(ligne.cout_corporatif_annuel),
            }
            for ligne in construire_courbe_salaire(ledger_path)
        ]
        self._reserve = reserves_depuis_ledger(self.ledger.all_entries)

    def defaults(self) -> dict[str, object]:
        """Parametres initiaux de la vue interactive."""
        self._ensure_loaded()
        return {
            "dateReference": self._date_reference.isoformat(),
            "monthlyBaseline": float(self._depenses_mensuelles),
            "breathingRoom": 750,
            "emergencySavings": 0,
            "weddingTarget": 20000,
            "weddingDate": "2027-08-20",
            "houseTarget": 0,
            "houseDate": "2027-08-01",
            "fhsaTarget": 8000,
            "fhsaAlreadyFunded": 8000,
            "rrspTarget": 0,
            "targetNetMonthly": float(self._depenses_mensuelles),
            "corporateReserveTarget": 50000,
            "corporateTaxRate": 21,
            "extractionMode": "salary",
        }

    def salary_curve(self) -> list[dict]:
        """Courbe salaire -> net/cout, calculee avec le moteur paie Quebec."""
        self._ensure_loaded()
        return self._courbe_salaire

    def brackets(self) -> dict[str, list[dict[str, object]]]:
        """Tranches fiscales officielles 2026 demandees."""
        return data_brackets_json()

    def reserve(self) -> dict[str, float]:
        """Reserve corporative estimee depuis le ledger."""
        self._ensure_loaded()
        return {
            "cash": float(self._reserve.encaisse_corporative),
            "taxes": float(self._reserve.taxes_tps_tvq_net),
            "availableAfterTaxes": float(self._reserve.disponible_apres_taxes),
        }

    def scenario_rows(self) -> list[dict[str, object]]:
        """Scenarios preconfigures calcules cote Python pour le rendu initial."""
        self._ensure_loaded()
        ledger_path = Path(
            getattr(
                self.ledger,
                "beancount_file_path",
                self._project_root / "ledger" / "main.beancount",
            )
        )
        rows: list[dict[str, object]] = []
        for scenario in scenarios_defaut(self._depenses_mensuelles, self._date_reference):
            resultat = analyser_scenario(
                scenario,
                ledger_path,
                date_reference=self._date_reference,
                taux_impot_corporatif=Decimal("0.21"),
                reserve_ledger=self._reserve,
            )
            rows.append(
                {
                    "name": resultat.nom,
                    "netMonthly": float(resultat.net_mensuel_requis),
                    "netAnnual": float(resultat.net_annuel_requis),
                    "grossAnnual": float(resultat.salaire_brut_annuel_estime),
                    "employerCost": float(resultat.cotisations_employeur_annuelles),
                    "corporateCost": float(resultat.cout_corporatif_annuel),
                    "opportunityCost": float(resultat.cout_opportunite_retenu),
                    "reserveMargin": (
                        None
                        if resultat.marge_reserve_corporative is None
                        else float(resultat.marge_reserve_corporative)
                    ),
                }
            )
        return rows

    def custom_scenario_template(self) -> dict[str, object]:
        """Structure partagee avec le JavaScript pour la ligne personnalisable."""
        self._ensure_loaded()
        return {
            "name": "Custom scenario",
            "monthlyBaseline": float(self._depenses_mensuelles),
            "breathingRoom": 0,
            "emergencySavings": 0,
            "weddingTarget": 20000,
            "weddingDate": "2027-08-20",
            "houseTarget": 0,
            "houseDate": "2027-08-01",
            "fhsaTarget": 8000,
            "fhsaAlreadyFunded": 8000,
            "rrspTarget": 0,
            "corporateReserveTarget": 50000,
        }

    def _detecter_racine(self) -> Path:
        ledger_path = Path(
            getattr(
                self.ledger,
                "beancount_file_path",
                "/Users/philippebeliveau/Desktop/Notebook/comptabilite/ledger/main.beancount",
            )
        )
        if ledger_path.name:
            return ledger_path.parent.parent
        return Path.cwd()

    def _ensure_loaded(self) -> None:
        if not self._courbe_salaire or self._reserve is None:
            self.after_load_file()
