"""Tests de planification remuneration proprietaire."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

from compteqc.planification.remuneration import (
    FEDERAL_2026_BRACKETS,
    QUEBEC_2026_BRACKETS,
    ParametresScenario,
    analyser_scenario,
    besoin_net_mensuel,
    bracket_actif,
    charger_depenses_mensuelles,
    mensualite_objectif,
    moyenne_depenses_recurrentes,
)

PROJECT_ROOT = Path(__file__).parent.parent


def test_personal_spending_baseline_loads_from_csv():
    """La moyenne recurrente vient du CSV personnel, pas du ledger corporatif."""
    path = PROJECT_ROOT / "data/personal-spending/personal-spending-monthly-2026.csv"

    monthly = charger_depenses_mensuelles(path)

    assert monthly["2026-03"] == Decimal("4012.81")
    assert moyenne_depenses_recurrentes(path) == Decimal("3677.99")


def test_wedding_monthly_need_defaults_to_about_1450():
    """Le mariage du 2027-08-20 donne un besoin mensuel proche de 1450 $."""
    monthly = mensualite_objectif(
        Decimal("20000"),
        dt.date(2027, 8, 20),
        dt.date(2026, 6, 29),
    )

    assert Decimal("1440") <= monthly <= Decimal("1470")


def test_fhsa_default_already_funded_does_not_add_monthly_need():
    """Le CELIAPP/FHSA 2026 est deja finance par defaut."""
    params = ParametresScenario(
        "fhsa funded",
        depenses_mensuelles=Decimal("3677.99"),
        celiapp_cible_annuelle=Decimal("8000"),
        celiapp_deja_cotise=Decimal("8000"),
    )

    assert besoin_net_mensuel(params, dt.date(2026, 6, 29)) == Decimal("3677.99")


def test_brackets_use_requested_official_2026_thresholds():
    """Les tranches exposees correspondent aux seuils demandes."""
    assert FEDERAL_2026_BRACKETS[0]["max"] == Decimal("58523")
    assert FEDERAL_2026_BRACKETS[-1]["rate"] == Decimal("0.33")
    assert QUEBEC_2026_BRACKETS[0]["max"] == Decimal("54345")
    assert QUEBEC_2026_BRACKETS[-1]["rate"] == Decimal("0.2575")
    assert bracket_actif(Decimal("100000"), FEDERAL_2026_BRACKETS)["rate"] == Decimal("0.205")
    assert bracket_actif(Decimal("120000"), QUEBEC_2026_BRACKETS)["rate"] == Decimal("0.24")


def test_salary_scenario_uses_payroll_engine_and_opportunity_cost():
    """Le scenario retourne salaire brut, cout employeur et retention a 21 %."""
    ledger_path = PROJECT_ROOT / "ledger/main.beancount"
    params = ParametresScenario(
        "baseline",
        depenses_mensuelles=Decimal("3677.99"),
    )

    result = analyser_scenario(
        params,
        ledger_path,
        date_reference=dt.date(2026, 6, 29),
        taux_impot_corporatif=Decimal("0.21"),
    )

    assert result.net_annuel_requis == Decimal("44135.88")
    assert result.salaire_brut_annuel_estime > result.net_annuel_requis
    assert result.cout_corporatif_annuel > result.salaire_brut_annuel_estime
    assert result.retenu_apres_impot_corporatif == (
        result.cout_corporatif_annuel * Decimal("0.79")
    ).quantize(Decimal("0.01"))
