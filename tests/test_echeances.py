"""Tests pour le module echeances (calendrier de production et remises)."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from freezegun import freeze_time

from compteqc.echeances.calendrier import (
    AlerteEcheance,
    Echeance,
    TypeEcheance,
    _ajuster_jour_ouvrable,
    calculer_echeances,
    formater_rappels_cli,
    integrer_echeances_pret,
    obtenir_alertes,
)
from compteqc.echeances.remises import (
    RemisePaie,
    prochaine_remise,
    suivi_remises,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_echeance(echeances: list[Echeance], type_: TypeEcheance) -> Echeance:
    """Trouve la premiere echeance d'un type donne."""
    for e in echeances:
        if e.type == type_:
            return e
    raise ValueError(f"Aucune echeance de type {type_}")


def _find_all(echeances: list[Echeance], type_: TypeEcheance) -> list[Echeance]:
    """Trouve toutes les echeances d'un type donne."""
    return [e for e in echeances if e.type == type_]


# ---------------------------------------------------------------------------
# Tests: calculer_echeances
# ---------------------------------------------------------------------------


class TestCalculerEcheances:
    """Tests pour calculer_echeances()."""

    def test_calculer_echeances_dec31(self) -> None:
        """Dec 31 year-end: T2 due Jun 30, T4 due Feb 28."""
        echeances = calculer_echeances(datetime.date(2025, 12, 31))

        t2 = _find_echeance(echeances, TypeEcheance.T2)
        assert t2.date_limite == datetime.date(2026, 6, 30)

        t4 = _find_echeance(echeances, TypeEcheance.T4_RL1)
        # Feb 28, 2026 is Saturday -> adjusted to Monday Mar 2
        assert t4.date_limite == datetime.date(2026, 3, 2)

    def test_calculer_echeances_mar31(self) -> None:
        """Mar 31 year-end: T2 due Sep 30."""
        echeances = calculer_echeances(datetime.date(2025, 3, 31))

        t2 = _find_echeance(echeances, TypeEcheance.T2)
        assert t2.date_limite == datetime.date(2025, 9, 30)

    def test_gst_qst_quarterly_deadlines(self) -> None:
        """4 quarterly TPS/TVQ deadlines with correct due dates."""
        echeances = calculer_echeances(datetime.date(2025, 12, 31))
        tps = _find_all(echeances, TypeEcheance.TPS_TVQ)

        assert len(tps) == 4

        # Q1: Mar 31 + 1 month = Apr 30
        assert tps[0].date_limite == datetime.date(2025, 4, 30)
        # Q2: Jun 30 + 1 month = Jul 30 (2025-07-30 is Wednesday)
        assert tps[1].date_limite == datetime.date(2025, 7, 30)
        # Q3: Sep 30 + 1 month = Oct 30
        assert tps[2].date_limite == datetime.date(2025, 10, 30)
        # Q4: Dec 31 + 1 month = Jan 31
        # Jan 31, 2026 is Saturday -> Monday Feb 2
        assert tps[3].date_limite == datetime.date(2026, 2, 2)

    def test_payroll_remittance_deadlines(self) -> None:
        """12 monthly payroll remittance deadlines."""
        echeances = calculer_echeances(datetime.date(2025, 12, 31))
        remises = _find_all(echeances, TypeEcheance.REMISE_PAIE)

        assert len(remises) == 12

    def test_total_echeance_count(self) -> None:
        """Total: T4 + T2 + CO17 + 4*TPS + 12*REMISE = 19."""
        echeances = calculer_echeances(datetime.date(2025, 12, 31))
        assert len(echeances) == 19


# ---------------------------------------------------------------------------
# Tests: weekend adjustment
# ---------------------------------------------------------------------------


class TestWeekendAdjustment:
    """Tests pour _ajuster_jour_ouvrable()."""

    def test_saturday_to_monday(self) -> None:
        """Saturday -> Monday."""
        # 2026-02-28 is Saturday
        result = _ajuster_jour_ouvrable(datetime.date(2026, 2, 28))
        assert result == datetime.date(2026, 3, 2)
        assert result.weekday() == 0  # Monday

    def test_sunday_to_monday(self) -> None:
        """Sunday -> Monday."""
        # 2026-03-01 is Sunday
        result = _ajuster_jour_ouvrable(datetime.date(2026, 3, 1))
        assert result == datetime.date(2026, 3, 2)
        assert result.weekday() == 0  # Monday

    def test_weekday_unchanged(self) -> None:
        """Weekday stays the same."""
        # 2025-06-30 is Monday
        result = _ajuster_jour_ouvrable(datetime.date(2025, 6, 30))
        assert result == datetime.date(2025, 6, 30)


# ---------------------------------------------------------------------------
# Tests: obtenir_alertes
# ---------------------------------------------------------------------------


class TestObtenirAlertes:
    """Tests pour obtenir_alertes()."""

    @freeze_time("2025-06-16")
    def test_obtenir_alertes_within_window(self) -> None:
        """Alert returned when within alert days."""
        echeances = [
            Echeance(
                type=TypeEcheance.T2,
                date_limite=datetime.date(2025, 6, 30),
                description="T2",
                jours_alerte=[90, 60, 30, 14, 7],
            )
        ]
        alertes = obtenir_alertes(echeances)
        assert len(alertes) == 1
        assert alertes[0].jours_restants == 14
        assert alertes[0].urgence == "urgent"

    @freeze_time("2025-01-01")
    def test_obtenir_alertes_outside_window(self) -> None:
        """No alert when deadline > 90 days away."""
        echeances = [
            Echeance(
                type=TypeEcheance.T2,
                date_limite=datetime.date(2025, 6, 30),
                description="T2",
                jours_alerte=[90, 60, 30, 14, 7],
            )
        ]
        alertes = obtenir_alertes(echeances)
        assert len(alertes) == 0

    @freeze_time("2025-06-27")
    def test_urgence_critique(self) -> None:
        """<= 7 days = critique."""
        echeances = [
            Echeance(
                type=TypeEcheance.T2,
                date_limite=datetime.date(2025, 6, 30),
                description="T2",
                jours_alerte=[90, 60, 30, 14, 7],
            )
        ]
        alertes = obtenir_alertes(echeances)
        assert len(alertes) == 1
        assert alertes[0].urgence == "critique"
        assert alertes[0].jours_restants == 3

    @freeze_time("2025-06-20")
    def test_urgence_urgent(self) -> None:
        """8-14 days = urgent."""
        echeances = [
            Echeance(
                type=TypeEcheance.T2,
                date_limite=datetime.date(2025, 6, 30),
                description="T2",
                jours_alerte=[90, 60, 30, 14, 7],
            )
        ]
        alertes = obtenir_alertes(echeances)
        assert len(alertes) == 1
        assert alertes[0].urgence == "urgent"
        assert alertes[0].jours_restants == 10

    @freeze_time("2025-06-10")
    def test_urgence_normal(self) -> None:
        """15-30 days = normal."""
        echeances = [
            Echeance(
                type=TypeEcheance.T2,
                date_limite=datetime.date(2025, 6, 30),
                description="T2",
                jours_alerte=[90, 60, 30, 14, 7],
            )
        ]
        alertes = obtenir_alertes(echeances)
        assert len(alertes) == 1
        assert alertes[0].urgence == "normal"
        assert alertes[0].jours_restants == 20

    def test_completed_echeance_skipped(self) -> None:
        """Completed echeances are not alerted."""
        echeances = [
            Echeance(
                type=TypeEcheance.T2,
                date_limite=datetime.date(2025, 6, 30),
                description="T2",
                jours_alerte=[90, 60, 30, 14, 7],
                completed=True,
            )
        ]
        alertes = obtenir_alertes(echeances, aujourd_hui=datetime.date(2025, 6, 25))
        assert len(alertes) == 0


# ---------------------------------------------------------------------------
# Tests: integrer_echeances_pret
# ---------------------------------------------------------------------------


class TestIntegrerEcheancesPret:
    """Tests pour integrer_echeances_pret()."""

    def test_integrer_echeances_pret(self) -> None:
        """Shareholder loan deadline appears in calendar."""
        from dataclasses import dataclass, field

        @dataclass
        class FakeEtatPret:
            avances_ouvertes: list = field(default_factory=list)

        etat = FakeEtatPret(avances_ouvertes=[
            {
                "date": datetime.date(2025, 6, 15),
                "montant_initial": Decimal("10000"),
                "solde_restant": Decimal("5000"),
            }
        ])

        echeances_base = calculer_echeances(datetime.date(2025, 12, 31))
        merged = integrer_echeances_pret(echeances_base, etat)

        pret = _find_all(merged, TypeEcheance.PRET_ACTIONNAIRE)
        assert len(pret) == 1
        assert pret[0].date_limite == datetime.date(2026, 12, 31)
        assert "s.15(2)" in pret[0].description
        assert "5000" in pret[0].description


# ---------------------------------------------------------------------------
# Tests: suivi_remises
# ---------------------------------------------------------------------------


class TestSuiviRemises:
    """Tests pour suivi_remises()."""

    def test_suivi_remises_no_entries(self) -> None:
        """Empty ledger returns 12 months with zero balances."""
        remises = suivi_remises([], 2025)
        assert len(remises) == 12
        for r in remises:
            assert r.retenues_dues == Decimal("0.00")
            assert r.cotisations_dues == Decimal("0.00")
            assert r.solde == Decimal("0.00")

    def test_suivi_remises_with_payroll(self) -> None:
        """Month with payroll shows non-zero retenues_dues."""
        from beancount.core import amount, data
        from beancount.core.number import D

        # Create a payroll transaction: credit Passifs:Retenues:RRQ (deduction owed)
        meta = data.new_metadata("<test>", 0)
        txn = data.Transaction(
            meta=meta,
            date=datetime.date(2025, 3, 15),
            flag="*",
            payee="Paie",
            narration="Paie mars",
            tags=frozenset(),
            links=frozenset(),
            postings=[
                data.Posting(
                    "Depenses:Salaires:Brut",
                    amount.Amount(D("5000"), "CAD"),
                    None, None, None, None,
                ),
                data.Posting(
                    "Passifs:Retenues:RRQ",
                    amount.Amount(D("-300"), "CAD"),
                    None, None, None, None,
                ),
                data.Posting(
                    "Passifs:Cotisations-Employeur:RRQ",
                    amount.Amount(D("-300"), "CAD"),
                    None, None, None, None,
                ),
                data.Posting(
                    "Actifs:Banque:Desjardins",
                    amount.Amount(D("-4400"), "CAD"),
                    None, None, None, None,
                ),
            ],
        )

        remises = suivi_remises([txn], 2025)
        mars = remises[2]  # Index 2 = mois 3
        assert mars.mois == 3
        assert mars.retenues_dues == Decimal("300")
        assert mars.cotisations_dues == Decimal("300")
        assert mars.total_du == Decimal("600")
        assert mars.total_remis == Decimal("0.00")
        assert mars.solde == Decimal("600")


# ---------------------------------------------------------------------------
# Tests: formater_rappels_cli
# ---------------------------------------------------------------------------


class TestFormaterRappelsCli:
    """Tests pour formater_rappels_cli()."""

    def test_formater_rappels_cli_none_outside_30(self) -> None:
        """Returns None when no alerts within 30 days."""
        alertes = [
            AlerteEcheance(
                echeance=Echeance(
                    type=TypeEcheance.T2,
                    date_limite=datetime.date(2025, 6, 30),
                    description="T2",
                ),
                jours_restants=60,
                urgence="info",
            )
        ]
        result = formater_rappels_cli(alertes)
        assert result is None

    def test_formater_rappels_cli_shows_urgent(self) -> None:
        """Returns formatted string when alert within 14 days."""
        alertes = [
            AlerteEcheance(
                echeance=Echeance(
                    type=TypeEcheance.T2,
                    date_limite=datetime.date(2025, 6, 30),
                    description="T2 deadline",
                ),
                jours_restants=10,
                urgence="urgent",
            )
        ]
        result = formater_rappels_cli(alertes)
        assert result is not None
        assert "T2 deadline" in result
        assert "10 jours" in result
        assert "[yellow]" in result

    def test_formater_rappels_cli_critique(self) -> None:
        """Critique alerts use red color."""
        alertes = [
            AlerteEcheance(
                echeance=Echeance(
                    type=TypeEcheance.CO17,
                    date_limite=datetime.date(2025, 6, 30),
                    description="CO-17",
                ),
                jours_restants=3,
                urgence="critique",
            )
        ]
        result = formater_rappels_cli(alertes)
        assert result is not None
        assert "[red]" in result
