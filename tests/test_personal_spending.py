from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from compteqc.personal_spending import analyser_depenses_personnelles


def _write_csv(path: Path, rows: list[str]) -> Path:
    path.write_text(
        "Type de compte,Numéro du compte,Date de l'opération,Numéro du chèque,Description 1,Description 2,CAD$,USD$\n"
        + "\n".join(rows)
        + "\n",
        encoding="utf-8",
    )
    return path


def test_personal_spending_excludes_card_payments_transfers_and_travel(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path / "personal.csv",
        [
            "Visa,111,3/1/2026,,IGA #8639 MONTREAL,,-18.72,",
            "Visa,111,3/2/2026,,MOLLO CAFE MONTREAL,,-5.13,",
            "Visa,111,3/3/2026,,AIRBNB BORDEAUX,,-600.00,",
            "Visa,111,3/4/2026,,PAIEMENT - MERCI,,500.00,",
            "Chèques,222,3/5/2026,,VIREMENT ENVOYÉ COMPTE PERSONNEL RBC,,-2000.00,",
            "Chèques,222,3/6/2026,,VIREMENT ENVOYÉ COLLEEN MARIE YFGGZS,,-1775.00,",
            "Chèques,222,3/6/2026,,VIREMENT REÇU ANASTASIIA SUBBOTINA CAES6X4K,,900.00,",
            "Chèques,222,3/7/2026,,PLACEMENT IG,,-1000.00,",
            "Chèques,222,3/7/2026,,EFFET REFUSÉ SANS PROVISION,,1000.00,",
            "Chèques,222,3/8/2026,,ASSURANCE CIE BELAIR,,-89.09,",
        ],
    )

    summary = analyser_depenses_personnelles([csv_path])

    assert summary.recurring_monthly_average == Decimal("1887.94")
    assert summary.net_recurring_monthly_average == Decimal("987.94")
    assert summary.monthly_offsets["2026-03"] == Decimal("900.00")
    assert summary.category_recurring["Housing"] == Decimal("1775.00")
    assert summary.category_net["Housing"] == Decimal("875.00")
    assert summary.category_recurring["Groceries and household"] == Decimal("18.72")
    assert summary.category_recurring["Restaurants and coffee"] == Decimal("5.13")
    assert summary.category_recurring["Insurance"] == Decimal("89.09")
    assert summary.excluded_totals["non_recurring_travel_ring"] == Decimal("600.00")
    assert summary.excluded_totals["card_payment_or_credit"] == Decimal("500.00")
    assert summary.excluded_totals["transfer_review"] == Decimal("2000.00")
    assert summary.excluded_totals["savings_or_artifact"] == Decimal("1000.00")
    assert summary.excluded_totals["returned_or_failed_payment"] == Decimal("1000.00")
