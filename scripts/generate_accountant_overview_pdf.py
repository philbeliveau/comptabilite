#!/usr/bin/env python3
"""Generate the 2026 YTD accountant overview PDF.

This report is intentionally CPA-facing and conservative: it presents ledger
facts, source files, unresolved classifications, and planning questions without
turning them into tax advice.
"""

from __future__ import annotations

import csv
import datetime as dt
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/pdf/accountant-overview-2026-ytd.pdf"
LEDGER_DIR = ROOT / "ledger/2026"
PENDING = ROOT / "ledger/pending.beancount"
COMPANY_INFO = ROOT / "docs/company-information.md"
PERSONAL_SPENDING_DIR = ROOT / "data/personal-spending"
PERSONAL_MONTHLY = PERSONAL_SPENDING_DIR / "personal-spending-monthly-2026.csv"
PERSONAL_CATEGORIES = PERSONAL_SPENDING_DIR / "personal-spending-categories-2026.csv"
PERSONAL_TRANSACTIONS = PERSONAL_SPENDING_DIR / "personal-spending-transactions-2026.csv"

MONEY = Decimal("0.01")
POSTING_RE = re.compile(
    r"^\s{2,}([A-Z][A-Za-z0-9:À-ÿ-]+)\s+(-?[0-9]+(?:\.[0-9]{1,2})?)\s+CAD\b"
)
TXN_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+[*!]\s+\"([^\"]*)\"\s+\"([^\"]*)\"")


@dataclass
class Posting:
    date: dt.date
    payee: str
    narration: str
    account: str
    amount: Decimal
    source: str


def money(value: Decimal) -> str:
    return f"${value.quantize(MONEY, rounding=ROUND_HALF_UP):,.2f}"


def signed_money(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value).quantize(MONEY, rounding=ROUND_HALF_UP):,.2f}"


def read_postings() -> list[Posting]:
    postings: list[Posting] = []
    for path in sorted(LEDGER_DIR.glob("*.beancount")):
        current: tuple[dt.date, str, str] | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            match_txn = TXN_RE.match(line)
            if match_txn:
                current = (
                    dt.date.fromisoformat(match_txn.group(1)),
                    match_txn.group(2),
                    match_txn.group(3),
                )
                continue
            match_posting = POSTING_RE.match(line)
            if current and match_posting:
                postings.append(
                    Posting(
                        date=current[0],
                        payee=current[1],
                        narration=current[2],
                        account=match_posting.group(1),
                        amount=Decimal(match_posting.group(2)),
                        source=str(path.relative_to(ROOT)),
                    )
                )
    return postings


def pending_total() -> Decimal:
    total = Decimal("0")
    if not PENDING.exists():
        return total
    for line in PENDING.read_text(encoding="utf-8").splitlines():
        match = POSTING_RE.match(line)
        if match and match.group(1) == "Depenses:Non-Classe":
            total += Decimal(match.group(2))
    return total


def account_balances(postings: list[Posting]) -> dict[str, Decimal]:
    balances: dict[str, Decimal] = {}
    for posting in postings:
        balances[posting.account] = balances.get(posting.account, Decimal("0")) + posting.amount
    return balances


def month_flows(postings: list[Posting]) -> list[list[str]]:
    by_month: dict[str, dict[str, Decimal]] = {}
    for posting in postings:
        if posting.account != "Actifs:Banque:RBC:Cheques":
            continue
        key = posting.date.strftime("%Y-%m")
        bucket = by_month.setdefault(key, {"in": Decimal("0"), "out": Decimal("0"), "net": Decimal("0")})
        if posting.amount > 0:
            bucket["in"] += posting.amount
        else:
            bucket["out"] += -posting.amount
        bucket["net"] += posting.amount
    rows = [["Month", "Receipts", "Disbursements", "Net cash flow"]]
    for month, values in sorted(by_month.items()):
        rows.append([month, money(values["in"]), money(values["out"]), signed_money(values["net"])])
    return rows


def shareholder_movements(postings: list[Posting]) -> tuple[Decimal, Decimal, Decimal, list[list[str]]]:
    shareholder = [p for p in postings if p.account == "Passifs:Pret-Actionnaire"]
    balance = sum((p.amount for p in shareholder), Decimal("0"))
    positive = sum((p.amount for p in shareholder if p.amount > 0), Decimal("0"))
    regular = sum(
        (
            p.amount
            for p in shareholder
            if p.amount > 0 and p.narration == "Virement vers compte personnel RBC"
        ),
        Decimal("0"),
    )
    rows = [["Date", "Description", "Amount"]]
    for posting in sorted([p for p in shareholder if p.amount > 0], key=lambda p: p.date):
        rows.append([posting.date.isoformat(), posting.narration or posting.payee, money(posting.amount)])
    return balance, regular, positive, rows


def read_personal_spending() -> dict[str, object]:
    monthly_rows: list[dict[str, str]] = []
    category_rows: list[dict[str, str]] = []
    excluded_totals: dict[str, Decimal] = {}

    if PERSONAL_MONTHLY.exists():
        with PERSONAL_MONTHLY.open(encoding="utf-8", newline="") as f:
            monthly_rows = list(csv.DictReader(f))
    if PERSONAL_CATEGORIES.exists():
        with PERSONAL_CATEGORIES.open(encoding="utf-8", newline="") as f:
            category_rows = list(csv.DictReader(f))
    if PERSONAL_TRANSACTIONS.exists():
        with PERSONAL_TRANSACTIONS.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                reason = row.get("excluded_reason") or ""
                if not reason:
                    continue
                amount = abs(Decimal(row["amount"]))
                excluded_totals[reason] = excluded_totals.get(reason, Decimal("0")) + amount

    gross_total = sum(
        (Decimal(row.get("gross_recurring_spend") or "0") for row in monthly_rows),
        Decimal("0"),
    )
    offset_total = sum(
        (Decimal(row.get("shared_housing_offset") or "0") for row in monthly_rows),
        Decimal("0"),
    )
    net_total = sum(
        (Decimal(row.get("net_recurring_spend") or "0") for row in monthly_rows),
        Decimal("0"),
    )
    months = Decimal(len(monthly_rows) or 1)
    non_recurring = excluded_totals.get("non_recurring_travel_ring", Decimal("0"))
    transfer_review = excluded_totals.get("transfer_review", Decimal("0"))
    savings_attempt = excluded_totals.get("savings_or_artifact", Decimal("0"))
    returned_failed = excluded_totals.get("returned_or_failed_payment", Decimal("0"))
    actual_spent = net_total + non_recurring

    return {
        "monthly_rows": monthly_rows,
        "category_rows": category_rows,
        "excluded_totals": excluded_totals,
        "gross_monthly_average": money(gross_total / months),
        "net_monthly_average": money(net_total / months),
        "gross_total": money(gross_total),
        "shared_housing_offset": money(offset_total),
        "net_total": money(net_total),
        "non_recurring": money(non_recurring),
        "transfer_review": money(transfer_review),
        "savings_attempt": money(savings_attempt),
        "returned_failed": money(returned_failed),
        "actual_spent": money(actual_spent),
        "actual_spent_monthly": money(actual_spent / months),
        "recurring_estimate": f"{money(net_total / months)}/month after shared-housing offset",
        "planning_target": "$4,500-$5,000/month net",
        "excluded_items": (
            "Bordeaux/France travel, travel restaurants and wine, ring purchase, "
            "pending/failed CELIAPP/FHSA transfer, large review transfers, and business capex."
        ),
    }


def personal_monthly_table(personal: dict[str, object]) -> list[list[str]]:
    rows = [["Month", "Gross recurring", "Housing offset", "Net recurring"]]
    for row in personal["monthly_rows"]:  # type: ignore[index]
        rows.append(
            [
                row["month"],
                money(Decimal(row["gross_recurring_spend"])),
                money(Decimal(row["shared_housing_offset"])),
                money(Decimal(row["net_recurring_spend"])),
            ]
        )
    return rows


def personal_category_table(personal: dict[str, object]) -> list[list[str]]:
    rows = [["Category", "Gross", "Offset", "Net"]]
    category_rows = list(personal["category_rows"])  # type: ignore[arg-type]
    category_rows.sort(key=lambda row: Decimal(row["net_recurring_spend"]), reverse=True)
    for row in category_rows:
        rows.append(
            [
                row["category"],
                money(Decimal(row["gross_recurring_spend"])),
                money(Decimal(row["offset"])),
                money(Decimal(row["net_recurring_spend"])),
            ]
        )
    return rows


def personal_excluded_table(personal: dict[str, object]) -> list[list[str]]:
    labels = {
        "inflow": "Other personal inflows excluded from spend",
        "card_payment_or_credit": "Card-payment credits / duplicate transfers",
        "returned_or_failed_payment": "Returned/failed payment",
        "savings_or_artifact": "Savings / investment attempt",
        "transfer_review": "Personal e-transfers requiring review",
        "non_recurring_travel_ring": "Bordeaux/France/Ring spending",
        "business_or_capex_review": "Business/capital items paid personally",
        "spouse_rent_contribution_candidate": "Spouse/shared-housing inflows",
    }
    rows = [["Reason", "Amount", "Planning treatment"]]
    excluded = personal["excluded_totals"]  # type: ignore[assignment]
    for reason, amount in sorted(excluded.items(), key=lambda item: item[1], reverse=True):
        treatment = "Exclude from recurring salary baseline"
        if reason == "non_recurring_travel_ring":
            treatment = "Show separately; do not annualize"
        elif reason == "transfer_review":
            treatment = "Review before treating as personal spend"
        elif reason == "savings_or_artifact":
            treatment = "Track as savings goal if it clears"
        elif reason == "returned_or_failed_payment":
            treatment = "Not completed; do not count as contribution"
        elif reason == "spouse_rent_contribution_candidate":
            treatment = "Apply capped $900/month housing offset"
        rows.append([labels.get(reason, reason), money(amount), treatment])
    return rows


def salary_equivalent_table() -> list[list[str]]:
    return [
        ["Scenario", "Net cash need", "Gross salary estimate", "Company cost estimate"],
        ["Recurring lifestyle only", "$33,335.88/year", "$41,562.17/year", "$46,045.09/year"],
        ["Recurring + pending $8k CELIAPP/FHSA", "$41,335.88/year", "$53,336.27/year", "$59,141.55/year"],
        ["Actual YTD spend annualized", "$45,208.80/year", "$59,366.19/year", "$65,848.77/year"],
        ["Actual YTD + review transfers annualized", "$60,158.28/year", "$84,877.91/year", "$93,698.67/year"],
        ["Recurring + wedding savings", "$50,853.84/year", "$69,175.73/year", "$76,755.25/year"],
        ["$4,500/month planning target", "$54,000.00/year", "$74,538.75/year", "$82,622.93/year"],
        ["$5,000/month planning target", "$60,000.00/year", "$84,612.45/year", "$93,413.97/year"],
    ]


def loan_salary_offset_table(shareholder_balance: Decimal, regular_withdrawals: Decimal, positive_loan_moves: Decimal) -> list[list[str]]:
    return [
        ["Loan/draw base", "Net salary offset", "Gross salary estimate", "Employer costs", "Company cost"],
        ["Current shareholder-loan balance", money(shareholder_balance), "$14,478.75", "$1,440.92", "$15,919.67"],
        ["Regular owner withdrawals", money(regular_withdrawals), "$15,020.59", "$1,501.50", "$16,522.09"],
        ["All positive shareholder-loan movements", money(positive_loan_moves), "$20,643.87", "$2,133.30", "$22,777.17"],
    ]


def tax_remittance_table(balances: dict[str, Decimal]) -> list[list[str]]:
    tps_remaining = -balances.get("Passifs:TPS-Percue", Decimal("0")) - balances.get("Actifs:TPS-Payee", Decimal("0"))
    tvq_remaining = -balances.get("Passifs:TVQ-Percue", Decimal("0")) - balances.get("Actifs:TVQ-Payee", Decimal("0"))
    return [
        ["Item", "Amount / date", "Notes"],
        ["First quarterly period", "2026-03-03 to 2026-03-31", "Deadline: 2026-04-30."],
        ["Main March tax driver", "$11,129.58 on 2026-04-10", "Procom PQI160679; sales tax was $1,449.58."],
        ["TPS/GST remitted", "$592.87", "RBC withdrawal evidence: 2026-04-20."],
        ["TVQ/QST remitted", "$1,182.77", "RBC withdrawal evidence: 2026-04-20."],
        ["Combined first-period remittance", "$1,775.64", "Cleared the documented March package."],
        ["Remaining TPS/GST estimate", money(tps_remaining), "Ledger estimate after first remittance."],
        ["Remaining TVQ/QST estimate", money(tvq_remaining), "Ledger estimate after first remittance."],
        ["Remaining combined estimate", money(tps_remaining + tvq_remaining), "CPA to reconcile before next filing."],
    ]


def source_files() -> list[str]:
    files = [
        "ledger/main.beancount",
        "ledger/pending.beancount",
        "docs/company-information.md",
        "docs/salary-roadmap-2026.md",
        "docs/personal-salary-scenarios-2026.md",
        "docs/tps-tvq-2026-03-filing-note.md",
        "Releves/2026/personal/2026/download-transactions-10.csv",
        "Releves/2026/personal/2026/download-transactions-11.csv",
        "Releves/2026/corporate/2026/download-transactions-13.csv",
        "Releves/2026/corporate/2026/download-transactions-14.csv",
        "Releves/2026/corporate/2026/procom/Payment-PQI160679.csv",
        "Releves/2026/corporate/2026/procom/Payment-PQI162526.csv",
        "Releves/2026/corporate/2026/procom/Payment-PQI164635.csv",
        "data/personal-spending/personal-spending-summary-2026.md",
        "data/personal-spending/personal-spending-monthly-2026.csv",
        "data/personal-spending/personal-spending-categories-2026.csv",
        "data/personal-spending/personal-spending-transactions-2026.csv",
    ]
    return files


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "CoverTitle",
            parent=styles["Title"],
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1f2933"),
            spaceAfter=20,
        )
    )
    styles.add(
        ParagraphStyle(
            "Section",
            parent=styles["Heading1"],
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#1f2933"),
            spaceBefore=12,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            "Subsection",
            parent=styles["Heading2"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#334e68"),
            spaceBefore=8,
            spaceAfter=5,
        )
    )
    styles.add(ParagraphStyle("Right", parent=styles["BodyText"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, leading=10))
    return styles


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#66788a"))
    canvas.drawString(0.72 * inch, 0.45 * inch, "CPA review required - generated from local accounting records")
    canvas.drawRightString(7.78 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def table(data: list[list[str]], widths: list[float] | None = None, small: bool = False) -> Table:
    if widths:
        tbl = Table(data, colWidths=widths, repeatRows=1)
    else:
        tbl = Table(data, repeatRows=1)
    font_size = 7 if small else 8
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7eef5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2933")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("LEADING", (0, 0), (-1, -1), font_size + 2),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bcccdc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fb")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tbl


def paragraph_list(items: list[str], styles) -> list[Paragraph]:
    return [Paragraph(f"- {item}", styles["BodyText"]) for item in items]


def generate() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    postings = read_postings()
    balances = account_balances(postings)
    shareholder_balance, regular_withdrawals, positive_loan_moves, loan_rows = shareholder_movements(postings)
    pending = pending_total()
    personal = read_personal_spending()
    generated = dt.date.today().isoformat()

    styles = build_styles()
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Accountant overview 2026 YTD",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=footer)])

    story = []
    story.append(Paragraph("Accountant Overview - 2026 YTD", styles["CoverTitle"]))
    story.append(Paragraph("CONSEIL ET SOLUTION ENACT INC.", styles["Title"]))
    story.append(Spacer(1, 0.18 * inch))
    story.append(
        Paragraph(
            f"Generated {generated}. Scope: corporate ledger through the current local records. "
            "This package is for CPA review and planning; it is not a tax filing, legal opinion, or payroll advice.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.25 * inch))
    story.append(
        table(
            [
                ["Identifier", "Value"],
                ["NEQ", "1181862674"],
                ["GST/HST / TPS-TVH", "79848 4770 RT0001"],
                ["QST / TVQ", "1233599588 TQ0001"],
                ["Corporate income tax file", "1233599588 IC0001"],
                ["Payroll status", "No confirmed payroll account found in reviewed files"],
            ],
            [2.3 * inch, 4.7 * inch],
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("Executive brief", styles["Section"]))
    story.extend(
        paragraph_list(
            [
                "Quebec incorporated solo IT consulting company with Procom as the main 2026 revenue stream.",
                "Main planning ask: determine sustainable monthly compensation and whether payments should be salary, dividends, shareholder-loan repayment/draw, reimbursements, or a mix.",
                "Current owner decision recorded on 2026-07-18: target 70,000 CAD gross salary for 2026; do not maximize RRSP/REER this year; treat the 8,000 CAD CELIAPP/FHSA transfer as a one-time savings event.",
                f"Net recurring personal baseline after spouse rent contribution: {personal['net_monthly_average']}/month; gross before shared-housing offsets: {personal['gross_monthly_average']}/month.",
                f"Base planning target remains {personal['planning_target']} if adding breathing room, CELIAPP/FHSA, wedding savings, house down payment, RRSP, and emergency reserve.",
                "Personal-account data is used only as a compensation-planning summary; it is not mixed into the corporate ledger except specific business-paid-personally or owner-loan items.",
                "May/June personal spending includes non-recurring Bordeaux/France travel and Ring purchase spending; show separately, but do not annualize for recurring salary planning.",
                "The current $8,000 CELIAPP/FHSA attempt is shown as failed/returned in the CSV and should be treated as pending until a cleared contribution appears.",
                "Sales taxes are treated as quarterly. The first March TPS/TVQ package was due 2026-04-30, driven mainly by the Procom receipt deposited 2026-04-10, and payment proofs are archived.",
            ],
            styles,
        )
    )

    story.append(Paragraph("Current key ledger totals", styles["Section"]))
    key_rows = [
        ["Metric", "Amount"],
        ["Corporate RBC chequing balance", money(balances.get("Actifs:Banque:RBC:Cheques", Decimal("0")))],
        ["Revenue - Consultation", money(-balances.get("Revenus:Consultation", Decimal("0")))],
        ["Expenses posted", money(sum(v for k, v in balances.items() if k.startswith("Depenses:")))],
        ["GST/HST collected liability", signed_money(balances.get("Passifs:TPS-Percue", Decimal("0")))],
        ["QST collected liability", signed_money(balances.get("Passifs:TVQ-Percue", Decimal("0")))],
        ["GST/HST ITCs receivable", money(balances.get("Actifs:TPS-Payee", Decimal("0")))],
        ["QST ITRs receivable", money(balances.get("Actifs:TVQ-Payee", Decimal("0")))],
        ["Remaining GST/QST payable estimate", money(-balances.get("Passifs:TPS-Percue", Decimal("0")) - balances.get("Passifs:TVQ-Percue", Decimal("0")) - balances.get("Actifs:TPS-Payee", Decimal("0")) - balances.get("Actifs:TVQ-Payee", Decimal("0")))],
        ["Current shareholder-loan balance", money(shareholder_balance)],
        ["Regular owner withdrawals", money(regular_withdrawals)],
        ["All positive shareholder-loan movements", money(positive_loan_moves)],
        ["Pending unclassified transfers", money(pending)],
        ["Net recurring personal baseline", personal["recurring_estimate"]],
        ["Actual personal cash consumed to date", personal["actual_spent"]],
    ]
    story.append(table(key_rows, [3.8 * inch, 2.1 * inch]))

    story.append(PageBreak())
    story.append(Paragraph("Financial statements", styles["Section"]))
    statement_rows = [["Account", "Balance"]]
    for account in sorted(balances):
        if account.startswith(("Actifs:", "Passifs:", "Revenus:", "Depenses:")):
            statement_rows.append([account, signed_money(balances[account])])
    story.append(table(statement_rows, [4.6 * inch, 1.6 * inch], small=True))

    story.append(PageBreak())
    story.append(Paragraph("GST/QST filing and remittance", styles["Section"]))
    story.extend(
        paragraph_list(
            [
                "The corporation files/remits sales taxes quarterly based on the current working records.",
                "For the first period ending 2026-03-31, the due/payment deadline was 2026-04-30.",
                "The tax amount to pay for that first period was mainly from the Procom payment received on 2026-04-10 for March services.",
                "The ledger preserves the bank evidence date currently shown in the RBC CSV: 2026-04-20 for both remittance withdrawals.",
                "Remaining GST/QST amounts below are ledger estimates for CPA review, not a submitted return.",
            ],
            styles,
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(table(tax_remittance_table(balances), [1.85 * inch, 1.75 * inch, 3.1 * inch], small=True))

    story.append(PageBreak())
    story.append(Paragraph("Corporate cash flow by month", styles["Section"]))
    story.append(table(month_flows(postings), [1.5 * inch, 1.55 * inch, 1.7 * inch, 1.55 * inch]))

    story.append(Paragraph("Shareholder loan", styles["Section"]))
    story.append(
        Paragraph(
            f"The current shareholder-loan balance in the ledger is <b>{money(shareholder_balance)}</b>. "
            f"Regular owner withdrawals total <b>{money(regular_withdrawals)}</b>. "
            "The difference exists because the shareholder-loan account also includes reimbursements, business expenses paid personally, personal deposits/returns, and personal items paid by the corporation.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(table(loan_rows, [1.05 * inch, 4.35 * inch, 1.1 * inch], small=True))

    story.append(PageBreak())
    story.append(Paragraph("Pending classification", styles["Section"]))
    story.append(
        Paragraph(
            f"Pending/unresolved items total <b>{money(pending)}</b>, currently staged in "
            "<code>ledger/pending.beancount</code> as non-classified until CPA/owner confirmation.",
            styles["BodyText"],
        )
    )
    story.extend(
        paragraph_list(
            [
                "2026-04-22 transfer to Hannah Diamong: $2,000 - classification not confirmed.",
                "2026-04-29 transfer to Hannah Diamong: $2,000 - classification not confirmed.",
                "Do not classify these as expense, salary, dividend, shareholder loan, or reimbursement without support.",
            ],
            styles,
        )
    )

    story.append(Paragraph("Personal cash-flow planning", styles["Section"]))
    story.extend(
        paragraph_list(
            [
                f"Gross recurring personal spending before shared-housing offsets: {personal['gross_monthly_average']}/month.",
                f"Shared housing contribution from spouse currently modeled as {personal['shared_housing_offset']} total across the four months reviewed, capped at $900/month.",
                f"Net recurring personal baseline after the shared-housing offset: {personal['net_monthly_average']}/month.",
                f"Actual personal cash consumed to date after offset and including non-recurring Bordeaux/France/ring spending: {personal['actual_spent']} ({personal['actual_spent_monthly']}/month over the reviewed period).",
                f"Excluded from recurring planning: {personal['excluded_items']}",
                "The personal CSVs are a planning input only; they are not corporate books.",
            ],
            styles,
        )
    )
    story.append(Paragraph("Monthly personal spending structure", styles["Subsection"]))
    story.append(table(personal_monthly_table(personal), [1.2 * inch, 1.75 * inch, 1.75 * inch, 1.75 * inch]))
    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph("Recurring personal spending by category", styles["Subsection"]))
    story.append(table(personal_category_table(personal), [3.15 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch], small=True))

    story.append(PageBreak())
    story.append(Paragraph("Personal one-time items and exclusions", styles["Section"]))
    story.append(
        Paragraph(
            "These items are excluded from the recurring salary baseline. Some still matter for cash planning, especially the pending CELIAPP/FHSA contribution, wedding savings, and reviewed transfers.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(table(personal_excluded_table(personal), [2.75 * inch, 1.1 * inch, 2.95 * inch], small=True))
    story.append(Paragraph("CELIAPP/FHSA status", styles["Subsection"]))
    story.extend(
        paragraph_list(
            [
                "The personal CSV currently shows an $8,000 PLACEMENT IG transfer followed by an $8,000 returned/failed payment.",
                "Treat the $8,000 as pending until the transfer clears. If it clears, model it as a one-time savings/contribution requirement, not recurring living expense.",
                "Recurring lifestyle plus an $8,000 CELIAPP/FHSA contribution implies about $53,336/year gross salary using the repo payroll estimate.",
            ],
            styles,
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Compensation scenarios for CPA review", styles["Section"]))
    scenarios = [
        [
            "Scenario",
            "CPA questions",
        ],
        [
            "Base living-cost scenario",
            "Gross up the mix for $4,500-$5,000/month net; respect payroll, tax, and cash.",
        ],
        [
            "House purchase next year",
            "Assess higher T4 salary for mortgage docs, down payment, FHSA/RRSP/HBP.",
        ],
        [
            "RRSP maximization",
            "Salary creates RRSP room; dividends generally do not. Quantify tradeoff.",
        ],
        [
            "Pay myself as little as possible",
            "Find minimum withdrawals for living costs and shareholder-loan compliance.",
        ],
        [
            "Balanced retained-cash scenario",
            "Cover personal needs while reserving GST/QST, income tax, CPA, equipment.",
        ],
        [
            "Wedding plan",
            "August 20, 2027 wedding; $20,000 target is about $1,460/month from 2026-06-29.",
        ],
    ]
    story.append(table(scenarios, [2.1 * inch, 4.6 * inch], small=True))

    story.append(Paragraph("Salary-equivalent planning estimates", styles["Section"]))
    story.append(
        Paragraph(
            "These are planning estimates from the repo payroll model and must be confirmed by the CPA using official payroll setup, TD1/TP-1015 assumptions, remittance frequency, and year-to-date treatment.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(table(salary_equivalent_table(), [2.45 * inch, 1.35 * inch, 1.45 * inch, 1.45 * inch], small=True))

    story.append(Paragraph("Recorded 70,000 CAD salary roadmap", styles["Section"]))
    story.extend(
        paragraph_list(
            [
                "Owner working decision recorded 2026-07-18: target 70,000 CAD gross salary for 2026.",
                "Repo payroll estimate: 70,000 CAD gross salary, 18,662.55 CAD employee deductions, 51,337.45 CAD net pay, 7,656.88 CAD employer payroll costs, and 77,656.88 CAD total company cost.",
                "If no 2026 salary has been formally posted yet and the target is caught up from July to December, use about 11,666.67 CAD gross salary per month. Estimated net pay is about 8,556.24 CAD/month and employer costs about 1,276.15 CAD/month.",
                "Actual monthly bank transfers should be confirmed by the CPA. If salary is used to clear existing shareholder-loan draws, apply net pay against Passifs:Pret-Actionnaire first and transfer only the excess cash to the personal account.",
                "RRSP/REER maximization is not a 2026 objective. The 8,000 CAD CELIAPP/FHSA transfer is a one-time savings event, not recurring monthly spending.",
            ],
            styles,
        )
    )

    story.append(Paragraph("Using salary to clear shareholder-loan draws", styles["Section"]))
    story.append(
        Paragraph(
            "If salary is used to clear amounts already drawn, the CPA should gross up salary, record payroll deductions and employer contributions, and apply the net pay against Passifs:Pret-Actionnaire instead of sending additional cash.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(table(loan_salary_offset_table(shareholder_balance, regular_withdrawals, positive_loan_moves), [2.35 * inch, 1.1 * inch, 1.2 * inch, 1.05 * inch, 1.1 * inch], small=True))

    story.append(PageBreak())
    story.append(Paragraph("Accountant action checklist", styles["Section"]))
    story.extend(
        paragraph_list(
            [
                "Classify prior corporation-to-owner transfers and determine salary/dividend/shareholder-loan/reimbursement treatment.",
                "Confirm whether CRA payroll and Quebec source-deduction accounts must be opened before salary starts.",
                "Confirm whether existing shareholder-loan draws can be cleared by salary net pay offset and what gross-up/remittance dates apply.",
                "Confirm home-office rent and internet assumptions.",
                "Gross up the target monthly net pay using Quebec payroll deductions if salary is selected.",
                "Review the personal-spending tracker: spouse rent contribution, pending $8,000 CELIAPP/FHSA transfer, wedding savings target, and reviewed e-transfers.",
                "Review GST/QST treatment, remittances, and remaining balances.",
                "Resolve pending Hannah transfers and any missing supporting documents.",
                "Advise which scenario best matches mortgage, RRSP, tax, and retained-cash objectives.",
            ],
            styles,
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Appendix - source files and validation", styles["Section"]))
    story.append(Paragraph("Primary sources used or referenced:", styles["BodyText"]))
    story.extend(paragraph_list(source_files(), styles))
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        Paragraph(
            "Ledger validation status: regenerate this PDF only after <code>uv run bean-check ledger/main.beancount</code> passes.",
            styles["BodyText"],
        )
    )
    story.append(
        Paragraph(
            "Sensitive note: the clicSEQUR access-code letter exists in corporate source files but the code is intentionally excluded from this report.",
            styles["BodyText"],
        )
    )

    doc.build(story)


if __name__ == "__main__":
    generate()
