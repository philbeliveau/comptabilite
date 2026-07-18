"""Personal cash-flow analysis for owner compensation planning.

This module intentionally stays outside the corporate Beancount ledger. Its
purpose is to summarize personal spending so salary/dividend/shareholder-loan
planning can be grounded in recurring personal cash needs.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from compteqc.ingestion.normalisation import detecter_encodage


CAD = Decimal("0.01")
SPOUSE_RENT_CONTRIBUTION = Decimal("900.00")
SPOUSE_RENT_CONTRIBUTOR_TERMS = (
    "ANASTASIIA SUBBOTINA",
)

CARD_PAYMENT_TERMS = (
    "PAIEMENT",
    "PAYMENT",
    "VIREMENT PAR BANQUE EN DIRECT",
    "CARTE DE CREDIT",
    "CARTE DE CRÉDIT",
)

TRANSFER_TERMS = (
    "VIREMENT ENVOY",
    "VIREMENT RECU",
    "VIREMENT REÇU",
    "TRANSFERT",
    "INTERAC E-TRANSFER",
)

NON_RECURRING_TERMS = (
    "AIRBNB",
    "EXPEDIA",
    "BORDEAUX",
    "ARCACHON",
    "SAINT-EMILION",
    "SAINT EMILION",
    "ST EMILION",
    "MARGAUX",
    "SAINT-ESTEPHE",
    "SAINT ESTEPHE",
    "ST ESTEPHE",
    "BELLESPERDRIX",
    "LADOS",
    "KUBA-MODALIS",
    "FRANCE",
    "PARIS",
    "CHARLES DE GAULLE",
    "AEROPORT",
    "AÉROPORT",
    "AIR/ VOL",
    "AVION",
    "HOTEL",
    "HÔTEL",
    "DIAMOND",
    "DIAMANT",
    "RING",
    "BAGUE",
    "HANNAH",
)

SAVINGS_ARTIFACT_TERMS = (
    "PLACEMENT IG",
    "INVEST",
    "EPARGNE",
    "ÉPARGNE",
    "NSF",
)

BUSINESS_CAPEX_TERMS = (
    "MACBOOK",
    "APPLE STORE",
    "ERIC VUONG",
)

RETURNED_PAYMENT_TERMS = (
    "EFFET REFUSÉ SANS PROVISION",
    "EFFET REFUSE SANS PROVISION",
    "NSF",
    "NON-SUFFICIENT FUNDS",
)


@dataclass(frozen=True)
class PersonalTransaction:
    source_file: str
    line: int
    account_type: str
    date: date
    description: str
    amount: Decimal
    direction: str
    category: str
    recurring: bool
    excluded_reason: str


@dataclass(frozen=True)
class PersonalSpendingSummary:
    transactions: list[PersonalTransaction]
    monthly_recurring: dict[str, Decimal]
    monthly_offsets: dict[str, Decimal]
    monthly_net_recurring: dict[str, Decimal]
    category_recurring: dict[str, Decimal]
    category_offsets: dict[str, Decimal]
    category_net: dict[str, Decimal]
    excluded_totals: dict[str, Decimal]

    @property
    def recurring_total(self) -> Decimal:
        return sum(self.monthly_recurring.values(), Decimal("0")).quantize(CAD)

    @property
    def recurring_months(self) -> int:
        return len(self.monthly_recurring)

    @property
    def recurring_monthly_average(self) -> Decimal:
        if not self.monthly_recurring:
            return Decimal("0.00")
        return (self.recurring_total / Decimal(len(self.monthly_recurring))).quantize(
            CAD, rounding=ROUND_HALF_UP
        )

    @property
    def net_recurring_total(self) -> Decimal:
        return sum(self.monthly_net_recurring.values(), Decimal("0")).quantize(CAD)

    @property
    def net_recurring_monthly_average(self) -> Decimal:
        if not self.monthly_net_recurring:
            return Decimal("0.00")
        return (self.net_recurring_total / Decimal(len(self.monthly_net_recurring))).quantize(
            CAD, rounding=ROUND_HALF_UP
        )


def analyser_depenses_personnelles(paths: list[Path]) -> PersonalSpendingSummary:
    transactions: list[PersonalTransaction] = []
    for path in paths:
        transactions.extend(_lire_csv_personnel(path))

    monthly: dict[str, Decimal] = {}
    offsets: dict[str, Decimal] = {}
    categories: dict[str, Decimal] = {}
    category_offsets: dict[str, Decimal] = {}
    excluded: dict[str, Decimal] = {}
    spouse_inflows_by_month: dict[str, Decimal] = {}
    for txn in transactions:
        amount = abs(txn.amount)
        if txn.recurring:
            month = txn.date.strftime("%Y-%m")
            monthly[month] = monthly.get(month, Decimal("0")) + amount
            categories[txn.category] = categories.get(txn.category, Decimal("0")) + amount
        elif txn.excluded_reason == "spouse_rent_contribution_candidate":
            month = txn.date.strftime("%Y-%m")
            spouse_inflows_by_month[month] = spouse_inflows_by_month.get(month, Decimal("0")) + amount
        elif txn.excluded_reason:
            excluded[txn.excluded_reason] = excluded.get(txn.excluded_reason, Decimal("0")) + amount

    for month, amount in spouse_inflows_by_month.items():
        if monthly.get(month, Decimal("0")) <= Decimal("0"):
            continue
        offset = min(amount, SPOUSE_RENT_CONTRIBUTION)
        offsets[month] = offset
        category_offsets["Housing"] = category_offsets.get("Housing", Decimal("0")) + offset

    net_monthly = {
        month: (amount - offsets.get(month, Decimal("0"))).quantize(CAD)
        for month, amount in sorted(monthly.items())
    }
    category_net = {
        category: (amount - category_offsets.get(category, Decimal("0"))).quantize(CAD)
        for category, amount in sorted(categories.items())
    }

    return PersonalSpendingSummary(
        transactions=transactions,
        monthly_recurring={k: v.quantize(CAD) for k, v in sorted(monthly.items())},
        monthly_offsets={k: v.quantize(CAD) for k, v in sorted(offsets.items())},
        monthly_net_recurring=net_monthly,
        category_recurring={k: v.quantize(CAD) for k, v in sorted(categories.items())},
        category_offsets={k: v.quantize(CAD) for k, v in sorted(category_offsets.items())},
        category_net=category_net,
        excluded_totals={k: v.quantize(CAD) for k, v in sorted(excluded.items())},
    )


def ecrire_rapport_depenses_personnelles(
    summary: PersonalSpendingSummary,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    transactions_csv = output_dir / "personal-spending-transactions-2026.csv"
    monthly_csv = output_dir / "personal-spending-monthly-2026.csv"
    category_csv = output_dir / "personal-spending-categories-2026.csv"
    markdown = output_dir / "personal-spending-summary-2026.md"

    with transactions_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "date",
                "source_file",
                "line",
                "account_type",
                "description",
                "amount",
                "direction",
                "category",
                "recurring",
                "excluded_reason",
            ]
        )
        for txn in sorted(summary.transactions, key=lambda t: (t.date, t.source_file, t.line)):
            writer.writerow(
                [
                    txn.date.isoformat(),
                    txn.source_file,
                    txn.line,
                    txn.account_type,
                    txn.description,
                    f"{txn.amount.quantize(CAD)}",
                    txn.direction,
                    txn.category,
                    "yes" if txn.recurring else "no",
                    txn.excluded_reason,
                ]
            )

    with monthly_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "gross_recurring_spend", "shared_housing_offset", "net_recurring_spend"])
        for month, amount in summary.monthly_recurring.items():
            writer.writerow(
                [
                    month,
                    f"{amount.quantize(CAD)}",
                    f"{summary.monthly_offsets.get(month, Decimal('0')).quantize(CAD)}",
                    f"{summary.monthly_net_recurring.get(month, amount).quantize(CAD)}",
                ]
            )

    with category_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "gross_recurring_spend", "offset", "net_recurring_spend"])
        for category, amount in summary.category_recurring.items():
            writer.writerow(
                [
                    category,
                    f"{amount.quantize(CAD)}",
                    f"{summary.category_offsets.get(category, Decimal('0')).quantize(CAD)}",
                    f"{summary.category_net.get(category, amount).quantize(CAD)}",
                ]
            )

    markdown.write_text(_markdown(summary), encoding="utf-8")

    return {
        "transactions": transactions_csv,
        "monthly": monthly_csv,
        "categories": category_csv,
        "summary": markdown,
    }


def _lire_csv_personnel(path: Path) -> list[PersonalTransaction]:
    encodage = detecter_encodage(path)
    rows: list[PersonalTransaction] = []
    with path.open(encoding=encodage, newline="") as f:
        reader = csv.DictReader(f)
        for lineno, row in enumerate(reader, start=2):
            amount_text = (row.get("CAD$") or row.get("CAD") or "").strip()
            if not amount_text:
                continue
            amount = Decimal(amount_text)
            txn_date = datetime.strptime(row["Date de l'opération"].strip(), "%m/%d/%Y").date()
            desc1 = (row.get("Description 1") or "").strip()
            desc2 = (row.get("Description 2") or "").strip()
            description = f"{desc1} {desc2}".strip()
            account_type = (row.get("Type de compte") or "").strip()
            direction = "inflow" if amount > 0 else "outflow"
            category, recurring, reason = _classer(description, amount, account_type)
            rows.append(
                PersonalTransaction(
                    source_file=path.name,
                    line=lineno,
                    account_type=account_type,
                    date=txn_date,
                    description=description,
                    amount=amount,
                    direction=direction,
                    category=category,
                    recurring=recurring,
                    excluded_reason=reason,
                )
            )
    return rows


def _classer(description: str, amount: Decimal, account_type: str) -> tuple[str, bool, str]:
    desc = description.upper()

    if amount > 0:
        if account_type.upper() == "VISA" or _contains(desc, CARD_PAYMENT_TERMS):
            return "Transfers / card payments", False, "card_payment_or_credit"
        if _contains(desc, RETURNED_PAYMENT_TERMS):
            return "Returned or failed payment", False, "returned_or_failed_payment"
        if _contains(desc, SPOUSE_RENT_CONTRIBUTOR_TERMS):
            return "Shared housing contribution", False, "spouse_rent_contribution_candidate"
        return "Income / transfers in", False, "inflow"

    if _contains(desc, SAVINGS_ARTIFACT_TERMS):
        return "Savings / investment artifacts", False, "savings_or_artifact"
    if _contains(desc, BUSINESS_CAPEX_TERMS):
        return "Business or capital items", False, "business_or_capex_review"
    if _contains(desc, NON_RECURRING_TERMS):
        return "Non-recurring travel/ring", False, "non_recurring_travel_ring"
    if _contains(desc, CARD_PAYMENT_TERMS):
        return "Transfers / card payments", False, "card_payment_or_credit"
    if _contains(desc, TRANSFER_TERMS) and "COLLEEN MARIE" not in desc:
        return "Transfers / review", False, "transfer_review"

    return _categorie_recurrente(desc), True, ""


def _categorie_recurrente(desc: str) -> str:
    if "COLLEEN MARIE" in desc or "LOYER" in desc:
        return "Housing"
    if "ASSURANCE" in desc or "INSURANCE" in desc or "BELAIR" in desc:
        return "Insurance"
    if any(term in desc for term in ("IGA", "COSTCO", "METRO", "PHARMAPRIX", "DOLLARAMA", "MAXI")):
        return "Groceries and household"
    if any(term in desc for term in ("BOUCHERIE", "CHARCUTERIE", "FAMILIPRIX", "IHERB")):
        return "Groceries, pharmacy, and health"
    if any(term in desc for term in ("SAQ", "MICRODISTILLERIE", "VAPE", "COUCHE-TARD")):
        return "Alcohol, convenience, and discretionary"
    if any(term in desc for term in ("CAFE", "CAFÉ", "MOLLO", "RESTO", "UBER EATS", "DOORDASH", "RESTAURANT")):
        return "Restaurants and coffee"
    if any(term in desc for term in ("HIATUS", "ODESSA", "TEATRO")):
        return "Restaurants and coffee"
    if any(term in desc for term in ("STM", "BIXI", "UBER", "TAXI", "ESSO", "ALLO VELO", "PARKING", "PETRO-CANADA", "SHELL", "CLICKTIRE")):
        return "Transport"
    if any(term in desc for term in ("FIZZ", "GOOGLE", "MICROSOFT", "APPLE", "SPOTIFY", "NETFLIX", "SUBSCRIPTION")):
        return "Telecom, software, subscriptions"
    if any(term in desc for term in ("HYDRO-QUEBEC", "HYDRO QUÉBEC", "ELECTR", "ÉLECTR")):
        return "Utilities"
    if any(term in desc for term in ("ECCO", "ARCTERYX", "WINNERS", "MOUNTAIN EQUIPMENT", "OAKLEY")):
        return "Clothing and gear"
    if any(term in desc for term in ("FRAIS", "FEE", "BANCAIRE")):
        return "Bank fees"
    return "Other recurring personal"


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _format_money(value: Decimal) -> str:
    return f"${value.quantize(CAD):,.2f}"


def _markdown(summary: PersonalSpendingSummary) -> str:
    lines = [
        "# Personal Spending Summary - 2026",
        "",
        "Purpose: track personal spending for salary and compensation planning. This is not part of the corporate ledger.",
        "",
        "## Salary Planning Signal",
        "",
        f"- Gross recurring monthly average before shared-housing offsets: `{_format_money(summary.recurring_monthly_average)}`",
        f"- Net recurring monthly average after shared-housing offsets: `{_format_money(summary.net_recurring_monthly_average)}`",
        f"- Shared housing offset assumption: `{_format_money(SPOUSE_RENT_CONTRIBUTION)}/month` from spouse contributions when present in the CSV.",
        f"- Months covered: `{summary.recurring_months}`",
        "- Practical net salary target remains a CPA planning question; use recurring spend plus savings, RRSP/FHSA, mortgage, and tax objectives.",
        "- Bordeaux/France travel and ring-related spending are treated as non-recurring and excluded from recurring salary planning.",
        "",
        "## Recurring Spending By Month",
        "",
        "| Month | Gross recurring spend | Shared housing offset | Net recurring spend |",
        "| --- | ---: | ---: | ---: |",
    ]
    for month, amount in summary.monthly_recurring.items():
        offset = summary.monthly_offsets.get(month, Decimal("0"))
        net = summary.monthly_net_recurring.get(month, amount)
        lines.append(f"| `{month}` | `{_format_money(amount)}` | `{_format_money(offset)}` | `{_format_money(net)}` |")

    lines.extend(["", "## Recurring Spending By Category", "", "| Category | Gross | Offset | Net |", "| --- | ---: | ---: | ---: |"])
    for category, amount in sorted(summary.category_recurring.items(), key=lambda i: i[1], reverse=True):
        offset = summary.category_offsets.get(category, Decimal("0"))
        net = summary.category_net.get(category, amount)
        lines.append(f"| {category} | `{_format_money(amount)}` | `{_format_money(offset)}` | `{_format_money(net)}` |")

    lines.extend(["", "## Excluded From Recurring Salary Planning", "", "| Reason | Amount |", "| --- | ---: |"])
    for reason, amount in sorted(summary.excluded_totals.items(), key=lambda i: i[1], reverse=True):
        lines.append(f"| `{reason}` | `{_format_money(amount)}` |")

    if "savings_or_artifact" in summary.excluded_totals or "returned_or_failed_payment" in summary.excluded_totals:
        lines.extend(
            [
                "",
                "## Savings And CELIAPP/FHSA Planning",
                "",
                "- Savings/investment transfers are excluded from recurring living costs.",
                "- A returned or failed payment is not treated as completed savings.",
                "- If the CELIAPP/FHSA contribution later clears, track it as a one-time savings goal or completed contribution, not recurring spending.",
            ]
        )

    lines.extend(
        [
            "",
            "## Generated Files",
            "",
            "- `personal-spending-transactions-2026.csv`: transaction-level classified personal activity.",
            "- `personal-spending-monthly-2026.csv`: recurring spend by month.",
            "- `personal-spending-categories-2026.csv`: recurring spend by category.",
            "",
            "## Caveats",
            "",
            "- Categorization is deterministic and reviewable; it is not tax advice.",
            "- Personal CSVs include transfers, card payments, credits, and savings artifacts that must not be treated as living expenses.",
            "- Personal spending informs compensation planning only; it should not be mixed into the corporate books.",
        ]
    )
    return "\n".join(lines) + "\n"
