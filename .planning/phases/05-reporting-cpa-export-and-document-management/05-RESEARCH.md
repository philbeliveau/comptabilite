# Phase 5: Reporting, CPA Export, and Document Management - Research

**Researched:** 2026-02-19
**Domain:** PDF report generation, GIFI export, invoice templating, receipt OCR, filing deadline tracking
**Confidence:** HIGH

## Summary

Phase 5 is the output convergence layer that transforms all ledger data from prior phases into deliverables: a CPA year-end package, branded consulting invoices, receipt ingestion with AI extraction, and filing deadline alerts. The codebase already has the core data available -- trial balance, P&L, and balance sheet rendering in `rapports.py`, GST/QST summaries in `taxes/sommaire.py`, CCA pools in `dpa/calcul.py`, shareholder loan tracking in `pret_actionnaire/suivi.py`, and payroll results in `paie/moteur.py`. The primary work is (1) rendering these to CSV + PDF in dual-format, (2) GIFI code mapping for Schedule 100/125 export, (3) branded invoice generation, (4) Claude Vision receipt extraction, and (5) deadline calendar with dashboard alerts.

The standard stack is Jinja2 + WeasyPrint for HTML-to-PDF generation (already implicit via the project's Python stack), the existing Anthropic SDK for Claude Vision receipt extraction (already a dependency), and Beancount's `document` directive for linking receipts to transactions. No new heavyweight dependencies are needed -- the heaviest addition is WeasyPrint for PDF rendering.

**Primary recommendation:** Use Jinja2 HTML templates + WeasyPrint for all PDF generation (reports and invoices). Use the existing `messages.parse()` with Pydantic `output_format` for receipt extraction. Generate GIFI CSV in TaxCycle-compatible format (GIFI code + amount pairs). Surface deadlines through the Fava dashboard (Phase 4 dependency) and CLI output.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- CPA format preference unknown -- consult CPA before finalizing; system should generate both CSV (machine-readable) and PDF (human-readable) so whichever the CPA prefers is available
- GIFI-mapped Schedule 100 export should include pre-validation (accounting equation balance, no negative revenue, asset/liability sanity checks) before generation
- Dual-format strategy: PDF for all reports (human review), CSV for key data exports (trial balance, GIFI mapping, payroll schedule) that CPA tools can import
- Currently invoicing manually from Word/Google Docs -- this replaces that with a CLI/system-generated approach
- Low volume: 1-2 clients per month -- keep workflow simple
- Branded template required: company logo, colors, specific styling (not generic/plain)
- GST/QST numbers and correct tax breakdown on every invoice (legal requirement)
- Payment tracking is manual: user marks invoices as paid when deposit is seen in bank -- no auto-matching needed
- Invoice statuses: draft, sent, paid, overdue
- Invoices link to accounts receivable entries in the ledger
- Mix of physical receipts (photographed) and digital PDFs from email
- Upload via both CLI (`cqc receipt upload`) and web dashboard (drag-and-drop in Fava UI)
- AI extraction via Claude Vision: vendor, date, amount, GST/QST breakdown
- Extracted data feeds into transaction matching
- Alerts surface as dashboard banners in the Fava web UI (primary channel)
- Key deadlines tracked: GST/QST quarterly, T4/RL-1 (Feb 28), T2/CO-17 (6 months after fiscal year-end)
- s.15(2) shareholder loan deadlines should be unified into the same dashboard alert system (single view of all deadlines)

### Claude's Discretion
- Single ZIP folder vs individual files delivery format for CPA package
- Exact report layout and PDF styling
- Which reports get CSV in addition to PDF (beyond the key three: trial balance, GIFI, payroll)
- Receipt-to-transaction matching strategy (auto-propose with confirmation vs manual selection -- use confidence scoring from Phase 3 to decide)
- Storage approach: git-tracked `documents/` folder vs separate storage with reference IDs
- Handling of low-quality images or unreadable receipts
- Alert lead times per deadline type (standard urgency-based approach)
- Year-end checklist strictness: warn-but-allow vs block-on-failure for CPA package generation
- Whether to also show deadline reminders in CLI output

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CPA-01 | System generates trial balance (CSV + PDF) | Existing `rapports.py:balance()` provides the logic; add CSV writer + Jinja2/WeasyPrint PDF renderer |
| CPA-02 | System generates income statement / P&L (CSV + PDF) | Existing `rapports.py:resultats()` provides the logic; same dual-format approach |
| CPA-03 | System generates balance sheet (CSV + PDF) | Existing `rapports.py:bilan()` provides the logic; same dual-format approach |
| CPA-04 | System generates payroll summary schedule | Existing `paie/moteur.py:ResultatPaie` + `paie/ytd.py` provides all data; format into schedule |
| CPA-05 | System generates CCA schedule by class | Existing `dpa/calcul.py:PoolDPA` + `dpa/registre.py` provides all data; format into schedule |
| CPA-06 | System generates GST/QST reconciliation summary | Existing `taxes/sommaire.py:SommairePeriode` provides all data; format by period |
| CPA-07 | System generates shareholder loan continuity schedule | Existing `pret_actionnaire/suivi.py:EtatPret` provides all data; format movements + deadlines |
| CPA-08 | GIFI-mapped export validates Schedule 100 balances | Chart of accounts already has GIFI metadata; build validation layer + GIFI CSV exporter |
| CPA-09 | All reports available as CSV for CPA import | CSV generation for all report types using Python `csv` module |
| AUTO-01 | Filing deadline calendar with reminders | Deadline definitions + alert engine; surface via Fava dashboard (Phase 4 dep) and CLI |
| AUTO-02 | Year-end checklist | Orchestrate validation checks across all modules; generate pass/fail report |
| AUTO-03 | Payroll remittance tracking | Compare Passifs:Retenues + Passifs:Cotisations-Employeur against remittance transactions |
| INV-01 | Generate professional invoices with GST/QST | Jinja2 + WeasyPrint branded template; invoice data model with tax calculation |
| INV-02 | Invoice tracks payment status | Invoice YAML/JSON store with status field; CLI commands to update |
| INV-03 | Invoices link to AR entries in ledger | Generate Beancount transactions for Actifs:ComptesClients on invoice creation |
| DOC-01 | Upload receipt/invoice PDFs and images | CLI `cqc receipt upload` + file copy to `ledger/documents/` |
| DOC-02 | AI extracts data from documents (Claude Vision) | Anthropic SDK `messages.parse()` with Pydantic model for receipt fields |
| DOC-03 | Extracted data matches to bank transactions | Matching by amount + date proximity; confidence scoring |
| DOC-04 | Documents stored and linked via Beancount document directive | Store in `ledger/documents/{YYYY}/{account}/` with `document` directives |
| CLI-05 | Generate CPA export package via CLI | `cqc cpa export --annee 2025` command orchestrating all report generation |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| WeasyPrint | >=62 | HTML-to-PDF rendering | Standard Python PDF generator; supports CSS `@page`, grid, flexbox; no external binaries; used by Django/Flask ecosystems for invoices and reports |
| Jinja2 | >=3.1 (already via beancount) | HTML template engine | Already an indirect dependency; de facto Python template standard; template inheritance for base report layout |
| anthropic | >=0.82.0 (already installed) | Claude Vision for receipt extraction | Already a project dependency; `messages.parse()` with Pydantic `output_format` for structured receipt data |
| pydantic | >=2 (already installed) | Data models for invoices, receipts, deadlines | Already a project dependency; validation, serialization, type safety |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | >=10.0 | Image processing for receipt photos | Resize/rotate receipt images before sending to Claude Vision; WeasyPrint may also need it for image embedding |
| python-dateutil | >=2.9 (already installed) | Date arithmetic for deadline calculations | Already installed; relativedelta for "6 months after fiscal year-end" type calculations |
| zipfile (stdlib) | N/A | ZIP packaging for CPA export | Bundle all reports into single deliverable |
| csv (stdlib) | N/A | CSV export for GIFI/reports | Standard library; simple GIFI code + amount pairs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint | fpdf2 | fpdf2 is lighter/faster but requires programmatic layout (no HTML/CSS); WeasyPrint wins for branded templates where CSS styling matters |
| WeasyPrint | ReportLab | ReportLab is more powerful for complex layouts but heavier API; HTML/CSS approach is much faster to develop and maintain for report-style documents |
| Jinja2 + WeasyPrint | python-docx | Would produce Word instead of PDF; less portable, harder to style; PDF is universal |

**Installation:**
```bash
uv add weasyprint pillow
```

Note: WeasyPrint requires system libraries (Pango, Cairo, GDK-PixBuf). On macOS: `brew install pango`. On Ubuntu: `apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0`.

## Architecture Patterns

### Recommended Project Structure
```
src/compteqc/
├── rapports/                # NEW: Report generation engine
│   ├── __init__.py
│   ├── base.py              # Base report class, shared rendering logic
│   ├── trial_balance.py     # Trial balance report (CPA-01)
│   ├── income_statement.py  # P&L report (CPA-02)
│   ├── balance_sheet.py     # Balance sheet report (CPA-03)
│   ├── payroll_schedule.py  # Payroll summary (CPA-04)
│   ├── cca_schedule.py      # CCA schedule (CPA-05)
│   ├── gst_qst_summary.py   # GST/QST reconciliation (CPA-06)
│   ├── shareholder_loan.py  # Shareholder loan continuity (CPA-07)
│   ├── gifi_export.py       # GIFI validation + CSV export (CPA-08, CPA-09)
│   ├── cpa_package.py       # Orchestrator: runs all reports, zips (CLI-05)
│   └── templates/           # Jinja2 HTML templates for PDF rendering
│       ├── base_report.html  # Shared header/footer, company branding
│       ├── trial_balance.html
│       ├── income_statement.html
│       ├── balance_sheet.html
│       ├── payroll_schedule.html
│       ├── cca_schedule.html
│       ├── gst_qst_summary.html
│       ├── shareholder_loan.html
│       └── css/
│           └── report.css    # Shared print CSS (@page rules, branding)
├── factures/                # NEW: Invoice generation
│   ├── __init__.py
│   ├── modeles.py           # Invoice data model (Pydantic)
│   ├── registre.py          # Invoice store (YAML persistence)
│   ├── generateur.py        # Invoice PDF generation
│   ├── journal.py           # Beancount AR entry generation
│   └── templates/
│       ├── facture.html     # Branded invoice template
│       └── css/
│           └── facture.css  # Invoice-specific styling
├── documents/               # NEW: Receipt/document management
│   ├── __init__.py
│   ├── upload.py            # File handling, storage, naming
│   ├── extraction.py        # Claude Vision receipt extraction
│   ├── matching.py          # Receipt-to-transaction matching
│   └── beancount_link.py    # Generate document directives
├── echeances/               # NEW: Filing deadlines and alerts
│   ├── __init__.py
│   ├── calendrier.py        # Deadline definitions and calculations
│   ├── verification.py      # Year-end checklist logic
│   └── remises.py           # Payroll remittance tracking
└── cli/
    ├── cpa.py               # NEW: `cqc cpa` subcommands
    ├── facture.py           # NEW: `cqc facture` subcommands
    └── receipt.py           # NEW: `cqc receipt` subcommands
```

### Pattern 1: Report Generator with Dual Output
**What:** Each report module produces both CSV and PDF from the same data extraction logic.
**When to use:** All CPA reports (CPA-01 through CPA-09).
**Example:**
```python
# Source: Pattern derived from existing rapports.py structure
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import csv
from io import StringIO
from jinja2 import Environment, PackageLoader
from weasyprint import HTML

@dataclass
class ReportRow:
    """A single row in a report."""
    account: str
    gifi: str
    debit: Decimal
    credit: Decimal

class BaseReport:
    """Base class for all CPA reports."""

    report_name: str = ""
    template_name: str = ""

    def __init__(self, entries: list, annee: int):
        self.entries = entries
        self.annee = annee
        self._env = Environment(
            loader=PackageLoader("compteqc.rapports", "templates"),
        )

    def extract_data(self) -> dict:
        """Override in subclasses. Returns template context dict."""
        raise NotImplementedError

    def to_csv(self, output_path: Path) -> Path:
        """Write report data as CSV."""
        data = self.extract_data()
        # Subclasses define their own CSV row format
        # ...
        return output_path

    def to_pdf(self, output_path: Path) -> Path:
        """Render report as branded PDF via Jinja2 + WeasyPrint."""
        data = self.extract_data()
        template = self._env.get_template(self.template_name)
        html_string = template.render(**data, annee=self.annee)
        css_path = Path(__file__).parent / "templates" / "css" / "report.css"
        HTML(string=html_string).write_pdf(
            str(output_path),
            stylesheets=[str(css_path)],
        )
        return output_path

    def generate(self, output_dir: Path) -> dict[str, Path]:
        """Generate both CSV and PDF."""
        output_dir.mkdir(parents=True, exist_ok=True)
        return {
            "csv": self.to_csv(output_dir / f"{self.report_name}.csv"),
            "pdf": self.to_pdf(output_dir / f"{self.report_name}.pdf"),
        }
```

### Pattern 2: GIFI Validation Before Export
**What:** Pre-validate accounting equation and sanity checks before generating GIFI CSV.
**When to use:** CPA-08 (GIFI export).
**Example:**
```python
# Source: Derived from existing comptes.beancount GIFI metadata
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class GIFIValidationResult:
    balanced: bool
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    warnings: list[str]
    errors: list[str]

def validate_gifi(soldes: dict[str, Decimal], gifi_map: dict[str, str]) -> GIFIValidationResult:
    """Validate before GIFI export.

    Checks:
    1. Accounting equation: Assets = Liabilities + Equity
    2. No negative revenue accounts
    3. Asset totals are positive
    4. Liability totals are positive (credit balances)
    """
    assets = sum(v for k, v in soldes.items() if k.startswith("Actifs"))
    liabilities = sum(abs(v) for k, v in soldes.items() if k.startswith("Passifs"))
    equity = sum(abs(v) for k, v in soldes.items() if k.startswith("Capital"))
    # Include net income in equity for balance check
    revenue = sum(abs(v) for k, v in soldes.items() if k.startswith("Revenus"))
    expenses = sum(v for k, v in soldes.items() if k.startswith("Depenses"))
    net_income = revenue - expenses
    equity_with_net = equity + net_income

    errors = []
    warnings = []

    if assets != liabilities + equity_with_net:
        diff = assets - (liabilities + equity_with_net)
        errors.append(f"Accounting equation imbalance: {diff} CAD")

    # Check for negative revenue (possible data entry error)
    for acct, val in soldes.items():
        if acct.startswith("Revenus") and val > 0:
            warnings.append(f"Revenue account {acct} has debit balance: {val}")

    return GIFIValidationResult(
        balanced=len(errors) == 0,
        total_assets=assets,
        total_liabilities=liabilities,
        total_equity=equity_with_net,
        warnings=warnings,
        errors=errors,
    )
```

### Pattern 3: Receipt Extraction with Claude Vision + Pydantic
**What:** Use Claude Vision to extract structured data from receipt images/PDFs.
**When to use:** DOC-02 (receipt extraction).
**Example:**
```python
# Source: Anthropic SDK docs - messages.parse() with output_format
import base64
from decimal import Decimal
from pathlib import Path
from pydantic import BaseModel
import anthropic

class ReceiptData(BaseModel):
    """Structured receipt data extracted by Claude Vision."""
    vendor: str
    date: str  # YYYY-MM-DD format
    subtotal: Decimal
    gst_amount: Decimal | None = None  # 5% federal
    qst_amount: Decimal | None = None  # 9.975% Quebec
    total: Decimal
    description: str
    confidence: float  # 0.0-1.0

def extract_receipt(image_path: Path) -> ReceiptData:
    """Extract structured data from receipt image using Claude Vision."""
    client = anthropic.Anthropic()

    image_data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")
    media_type = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"

    parsed = client.messages.parse(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    "Extract the following from this receipt: vendor name, date, "
                    "subtotal before tax, GST amount (5%), QST amount (9.975%), "
                    "total. Use YYYY-MM-DD date format. If a tax amount is not "
                    "visible, calculate it from the subtotal. Rate your confidence "
                    "from 0.0 to 1.0."
                )},
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                }},
            ],
        }],
        output_format=ReceiptData,
    )
    return parsed.parsed_output
```

### Pattern 4: Invoice Data Model with Ledger Integration
**What:** Pydantic model for invoices that generates Beancount AR entries.
**When to use:** INV-01 through INV-03.
**Example:**
```python
# Source: Derived from existing project patterns (Pydantic models + Beancount generation)
import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"

class InvoiceLine(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    gst_applicable: bool = True
    qst_applicable: bool = True

    @property
    def subtotal(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))

class Invoice(BaseModel):
    number: str          # e.g. "INV-2026-001"
    client_name: str
    client_address: str
    date: datetime.date
    due_date: datetime.date
    lines: list[InvoiceLine]
    status: InvoiceStatus = InvoiceStatus.DRAFT
    payment_date: datetime.date | None = None
    notes: str = ""

    @property
    def subtotal(self) -> Decimal:
        return sum(line.subtotal for line in self.lines)

    @property
    def gst(self) -> Decimal:
        taxable = sum(l.subtotal for l in self.lines if l.gst_applicable)
        return (taxable * Decimal("0.05")).quantize(Decimal("0.01"))

    @property
    def qst(self) -> Decimal:
        taxable = sum(l.subtotal for l in self.lines if l.qst_applicable)
        return (taxable * Decimal("0.09975")).quantize(Decimal("0.01"))

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.gst + self.qst
```

### Pattern 5: Beancount Document Directive for Receipts
**What:** Store receipts in a directory structure and link them to accounts/transactions.
**When to use:** DOC-04 (document storage and linking).
**Example:**
```python
# Source: Beancount language syntax documentation
# Document directive format: YYYY-MM-DD document Account "path/to/file.pdf"
# File structure: ledger/documents/{YYYY}/{account-path}/YYYY-MM-DD.description.pdf

def generate_document_directive(
    date: datetime.date,
    account: str,
    file_path: str,
) -> str:
    """Generate a Beancount document directive.

    Example output:
    2026-01-15 document Depenses:Bureau:Abonnements-Logiciels "documents/2026/01/2026-01-15.github-subscription.pdf"
    """
    return f'{date.isoformat()} document {account} "{file_path}"'

# Storage path convention:
# ledger/documents/{YYYY}/{MM}/YYYY-MM-DD.vendor-description.{ext}
# e.g.: ledger/documents/2026/01/2026-01-15.github-subscription.pdf
```

### Anti-Patterns to Avoid
- **Generating PDFs programmatically without templates:** Do not build PDFs cell-by-cell with ReportLab or fpdf2. Use HTML/CSS templates -- they are faster to develop, easier to maintain, and produce professional output with minimal code.
- **Storing receipts outside git:** For a solo consultant with low volume (~30 transactions/month), git-tracked documents in `ledger/documents/` are simpler and provide version history. Do not over-engineer with S3 or database blob storage.
- **Hardcoding deadlines:** Filing deadlines depend on fiscal year-end and filing frequency. Make them configurable, not hardcoded to December 31 year-end.
- **Auto-matching receipts without confirmation:** Always propose matches and require user confirmation. False matches are worse than unmatched receipts.
- **Generating GIFI without validation:** Never output GIFI CSV if the accounting equation does not balance. This would cause the CPA to reject the entire package.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF rendering | Custom PDF byte manipulation | WeasyPrint + Jinja2 | CSS paged media handles headers, footers, page breaks, margins -- hundreds of edge cases |
| Receipt OCR | Custom OpenCV pipeline | Claude Vision via Anthropic SDK | Claude handles handwriting, varying formats, poor lighting; custom OCR would take months |
| GIFI code database | Manual GIFI code table | Parse from `comptes.beancount` metadata | GIFI codes already exist as metadata on every account in the chart of accounts |
| Date/deadline arithmetic | Manual month/year math | python-dateutil relativedelta | Leap years, month-end edge cases (Feb 28/29), business day adjustments |
| ZIP archive creation | Shell `zip` commands | Python stdlib `zipfile` | Cross-platform, no external dependency, proper UTF-8 filename handling |

**Key insight:** The existing codebase already has all the data extraction logic needed (balances, payroll, CCA, GST/QST, shareholder loan). Phase 5 is primarily a presentation/formatting layer, not a computation layer. Do not re-implement business logic -- call existing functions and format their output.

## Common Pitfalls

### Pitfall 1: WeasyPrint System Dependencies
**What goes wrong:** WeasyPrint requires Pango, Cairo, and GDK-PixBuf system libraries. Installation fails silently or produces garbled PDFs if these are missing or outdated.
**Why it happens:** `pip install weasyprint` installs the Python package but not system dependencies.
**How to avoid:** Document system dependency installation in development setup. Test PDF generation early in development. On macOS: `brew install pango`. On Ubuntu: `apt install libpango-1.0-0 libpangocairo-1.0-0`.
**Warning signs:** Import errors mentioning `cffi`, `cairo`, or `pango`; PDFs with missing fonts or broken layout.

### Pitfall 2: Decimal Precision in CSV Export
**What goes wrong:** Decimal values get exported with floating-point artifacts (e.g., `1234.5600000001`) or inconsistent decimal places in CSV.
**Why it happens:** Implicit `str()` conversion of Decimal may not produce consistent formatting; mixing Decimal with float operations.
**How to avoid:** Always use `quantize(Decimal("0.01"))` before CSV export. Define a standard format function for all monetary CSV output.
**Warning signs:** CSV files where amounts have more than 2 decimal places; CPA tools rejecting import.

### Pitfall 3: GIFI Aggregation Mismatch
**What goes wrong:** Multiple Beancount accounts map to the same GIFI code (e.g., both `Actifs:TPS-Payee` and `Actifs:TVQ-Payee` map to GIFI 1300). The GIFI export needs aggregated amounts per GIFI code, not per Beancount account.
**Why it happens:** Beancount has finer granularity than GIFI requires.
**How to avoid:** Build an explicit GIFI aggregation step that sums balances by GIFI code. Add a test that verifies the sum of all GIFI-mapped accounts equals the trial balance total.
**Warning signs:** GIFI export has different totals than trial balance; CPA finds discrepancies.

### Pitfall 4: Invoice Number Collisions
**What goes wrong:** Restarting the system or manual edits cause duplicate invoice numbers, which is a legal compliance issue.
**Why it happens:** Sequential numbering without checking existing invoices.
**How to avoid:** Load the invoice registry on startup and derive the next number from the maximum existing number. Use format `INV-{YYYY}-{NNN}` with zero-padding.
**Warning signs:** Duplicate invoice numbers in the registry; tax authority audit risk.

### Pitfall 5: Receipt Image Size for Claude Vision
**What goes wrong:** Large receipt photos (10+ MB from phone cameras) cause slow API calls and high token usage.
**Why it happens:** Phone cameras take 12MP+ images; Claude Vision processes the full resolution.
**How to avoid:** Resize images to max 1568px on longest edge before sending to Claude (Anthropic recommends this). Use Pillow for resizing.
**Warning signs:** Receipt extraction taking >10 seconds; unexpectedly high API costs.

### Pitfall 6: Filing Deadline Timezone Issues
**What goes wrong:** Deadline alerts fire on the wrong day because the system uses UTC instead of Eastern time.
**Why it happens:** Python `datetime.date.today()` uses system timezone; servers may be UTC.
**How to avoid:** Always use `datetime.date.today()` for a local CLI tool (this is fine for a solo desktop app). If ever deployed to a server, explicitly use `America/Toronto` timezone.
**Warning signs:** Alerts appearing a day early or late.

## Code Examples

### Jinja2 + WeasyPrint Report Template
```html
{# templates/base_report.html #}
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>{{ titre }}</title>
  <style>
    @page {
      size: letter;
      margin: 2cm;
      @top-center { content: "{{ entreprise }}"; font-size: 9pt; color: #666; }
      @bottom-right { content: "Page " counter(page) " de " counter(pages); font-size: 8pt; }
    }
    body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 10pt; color: #333; }
    h1 { color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 0.5em; }
    table { width: 100%; border-collapse: collapse; margin-top: 1em; }
    th { background: #f0f4f8; text-align: left; padding: 6px 8px; border-bottom: 2px solid #1a365d; }
    td { padding: 4px 8px; border-bottom: 1px solid #e2e8f0; }
    td.amount { text-align: right; font-variant-numeric: tabular-nums; }
    tr.total { font-weight: bold; border-top: 2px solid #1a365d; }
    .generated { font-size: 8pt; color: #999; margin-top: 2em; }
  </style>
</head>
<body>
  <h1>{{ titre }}</h1>
  <p>Exercice: {{ annee }} | Genere: {{ date_generation }}</p>
  {% block content %}{% endblock %}
  <p class="generated">Genere par CompteQC v{{ version }}</p>
</body>
</html>
```

### GIFI CSV Export Format
```python
# Source: TaxCycle documentation - GIFI import format
# Format: Two columns - GIFI code and amount
# TaxCycle accepts .CSV, .GFI, or .TXT extensions

import csv
from decimal import Decimal
from pathlib import Path

def export_gifi_csv(
    gifi_balances: dict[str, Decimal],
    output_path: Path,
    schedule: str = "S100",  # S100 (balance sheet) or S125 (income statement)
) -> Path:
    """Export GIFI-mapped balances to TaxCycle-compatible CSV.

    Format: GIFI_CODE,AMOUNT
    Example:
        1001,45230.50
        1060,12500.00
        1300,1875.25
    """
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # TaxCycle expects: GIFI code, Amount
        for gifi_code, amount in sorted(gifi_balances.items()):
            if amount != Decimal("0"):
                writer.writerow([
                    gifi_code,
                    str(amount.quantize(Decimal("0.01"))),
                ])
    return output_path
```

### Filing Deadline Calendar
```python
# Source: CRA and Revenu Quebec official deadline documentation
import datetime
from dataclasses import dataclass
from enum import Enum
from dateutil.relativedelta import relativedelta

class DeadlineType(str, Enum):
    T4_RL1 = "T4/RL-1"          # Employee slips
    GST_QST = "GST/QST"          # Sales tax return
    T2 = "T2"                     # Federal corporate return
    CO17 = "CO-17"                # Quebec corporate return
    SHAREHOLDER_LOAN = "s.15(2)"  # Shareholder loan repayment
    PAYROLL_REMIT = "Payroll"     # Source deduction remittances

@dataclass
class Deadline:
    type: DeadlineType
    due_date: datetime.date
    description: str
    alert_days: list[int]  # Days before due date to alert

def calculate_deadlines(fiscal_year_end: datetime.date) -> list[Deadline]:
    """Calculate all filing deadlines for a fiscal year.

    Args:
        fiscal_year_end: Last day of fiscal year (e.g., 2025-12-31)
    """
    year = fiscal_year_end.year
    deadlines = []

    # T4/RL-1: Last day of February following calendar year
    # (if falls on weekend, next business day)
    t4_date = datetime.date(year + 1, 2, 28)
    if t4_date.weekday() >= 5:  # Weekend
        t4_date += datetime.timedelta(days=(7 - t4_date.weekday()))
    deadlines.append(Deadline(
        type=DeadlineType.T4_RL1,
        due_date=t4_date,
        description=f"T4 and RL-1 slips for {year}",
        alert_days=[90, 60, 30, 14, 7],
    ))

    # T2: 6 months after fiscal year-end
    t2_date = fiscal_year_end + relativedelta(months=6)
    deadlines.append(Deadline(
        type=DeadlineType.T2,
        due_date=t2_date,
        description=f"T2 corporate return for FY ending {fiscal_year_end}",
        alert_days=[90, 60, 30, 14, 7],
    ))

    # CO-17: Same as T2 (6 months after fiscal year-end)
    deadlines.append(Deadline(
        type=DeadlineType.CO17,
        due_date=t2_date,
        description=f"CO-17 Quebec corporate return for FY ending {fiscal_year_end}",
        alert_days=[90, 60, 30, 14, 7],
    ))

    # GST/QST quarterly: 1 month after each quarter end
    for q_end_month in [3, 6, 9, 12]:
        q_end = datetime.date(year, q_end_month, 1) + relativedelta(months=1) - datetime.timedelta(days=1)
        gst_due = q_end + relativedelta(months=1)
        deadlines.append(Deadline(
            type=DeadlineType.GST_QST,
            due_date=gst_due,
            description=f"GST/QST return for Q ending {q_end}",
            alert_days=[30, 14, 7],
        ))

    return deadlines
```

### CPA Package Orchestrator
```python
# Source: Derived from project architecture
from pathlib import Path
import zipfile
import datetime

def generate_cpa_package(
    entries: list,
    annee: int,
    output_dir: Path,
) -> Path:
    """Generate complete CPA package as ZIP.

    Steps:
    1. Run year-end checklist validation
    2. Generate all reports (CSV + PDF)
    3. Generate GIFI export with pre-validation
    4. Bundle into ZIP
    """
    pkg_dir = output_dir / f"cpa-package-{annee}"
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # Each report module generates its files into pkg_dir
    # ... (call each report generator)

    # ZIP everything
    zip_path = output_dir / f"cpa-package-{annee}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in pkg_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(pkg_dir))

    return zip_path
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ReportLab for Python PDFs | WeasyPrint (HTML/CSS to PDF) | ~2020 onwards | Much faster development; CSS expertise transfers directly; no programmatic layout code |
| Custom OCR pipelines | Vision LLMs (Claude, GPT-4V) | 2023-2024 | 90%+ accuracy on receipts without any training; handles varied formats natively |
| Tool-use for structured output | `messages.parse()` with Pydantic `output_format` | Nov 2025 | Native constrained generation; no tool-use workaround needed; guaranteed schema compliance |
| Separate tax filing apps | CPA receives pre-formatted data package | Ongoing | CPA can import GIFI CSV directly into TaxCycle; reduces manual data entry |

**Deprecated/outdated:**
- `instructor` library for Anthropic structured output: Anthropic's native `output_format` parameter (Nov 2025) makes instructor unnecessary for Claude. The project already uses `messages.parse()`.
- wkhtmltopdf: Deprecated upstream; WeasyPrint is the successor for HTML-to-PDF in Python.

## Discretion Recommendations

Based on research, here are recommendations for areas marked as Claude's Discretion:

### CPA Package Delivery: Single ZIP
**Recommendation:** Generate a single ZIP file containing organized subdirectories (`reports/`, `schedules/`, `gifi/`). CPAs are accustomed to receiving bundled packages, and a ZIP ensures nothing gets lost. Individual files are also available in the output directory before zipping.

### Additional CSV Reports
**Recommendation:** Generate CSV for: trial balance, GIFI (S100 + S125), payroll schedule, and GST/QST summary. These are the ones CPAs most likely need to import. CCA and shareholder loan schedules are PDF-only (rarely imported into tax software).

### Receipt-to-Transaction Matching
**Recommendation:** Auto-propose matches when confidence >= 0.8 (amount matches within $0.05 AND date within 3 days). Display proposed match for user confirmation. Below 0.8, show unmatched receipt for manual selection. This aligns with the Phase 3 confidence scoring approach.

### Receipt Storage
**Recommendation:** Git-tracked `ledger/documents/{YYYY}/{MM}/` folder. For a solo consultant with ~30 transactions/month, this is simple, version-controlled, and backed up with the rest of the ledger. Average receipt image is ~200KB after resize, so ~6MB/year of storage -- trivial for git.

### Low-Quality Receipt Handling
**Recommendation:** If Claude Vision confidence < 0.5, flag as "unreadable" and prompt user to re-photograph or manually enter data. Store the image anyway for audit trail.

### Alert Lead Times
**Recommendation:** Tiered by severity:
- T2/CO-17: 90, 60, 30, 14, 7 days before (high stakes, long lead time)
- T4/RL-1: 90, 60, 30, 14, 7 days before (same -- annual critical deadline)
- GST/QST quarterly: 30, 14, 7 days before (recurring, shorter window)
- Shareholder loan s.15(2): 90, 60, 30, 14, 7 days before (high stakes)
- Payroll remittances: 14, 7, 3 days before (monthly/quarterly routine)

### Year-End Checklist Strictness
**Recommendation:** Warn-but-allow. The system should display a clear report of all checks (pass/fail/warning) but still allow CPA package generation even with warnings. The CPA may have valid reasons to proceed despite warnings (e.g., shareholder loan will be repaid before deadline). Block only on fatal errors (accounting equation imbalance).

### CLI Deadline Reminders
**Recommendation:** Yes, show active deadline reminders in CLI output. When any deadline is within 30 days, display a one-line reminder at the bottom of any `cqc` command output (e.g., "Reminder: GST/QST Q4 due in 14 days"). Non-intrusive but effective for a CLI-first user.

## Open Questions

1. **TaxCycle GIFI CSV exact column format**
   - What we know: TaxCycle accepts `.CSV`, `.GFI`, or `.TXT` files with GIFI code + amount pairs. A sample file exists in TaxCycle's install directory.
   - What's unclear: Exact column headers (if any), whether amounts should be positive/negative or absolute with a sign column, whether a schedule identifier column is needed.
   - Recommendation: Start with simple `GIFI_CODE,AMOUNT` format (no headers). The user should validate with their CPA's copy of TaxCycle. Make the CSV format configurable.

2. **CPA's preferred format (CSV vs PDF)**
   - What we know: User hasn't consulted CPA yet on format preference.
   - What's unclear: Whether CPA uses TaxCycle, CaseWare, or another tool; what their import workflow looks like.
   - Recommendation: Build both formats now. After first CPA review, adjust based on feedback. The dual-format approach ensures no wasted work.

3. **Invoice branding specifics**
   - What we know: Branded template required with company logo, colors, specific styling. Not generic.
   - What's unclear: Exact logo file, brand colors, preferred layout.
   - Recommendation: Create a configurable template with brand variables (`logo_path`, `primary_color`, `secondary_color`, `company_info`) in a YAML config file. User provides these once during setup.

4. **Fava extension API stability**
   - What we know: Fava extension docs state "the whole extension system should be considered unstable and it might change drastically."
   - What's unclear: Whether Phase 4's Fava extensions will be stable enough for Phase 5's dashboard alerts by the time Phase 5 is implemented.
   - Recommendation: Design the alert/deadline system as a standalone module that can be surfaced through CLI first, with Fava dashboard integration as a separate task that depends on Phase 4 completion.

## Sources

### Primary (HIGH confidence)
- Anthropic SDK Python docs (Context7 `/anthropics/anthropic-sdk-python`) - Vision, structured output with `messages.parse()`
- WeasyPrint docs (Context7 `/kozea/weasyprint`) - HTML-to-PDF API, CSS support, write_pdf()
- Jinja2 docs (Context7 `/pallets/jinja`) - Template rendering, inheritance, PackageLoader
- Beancount language syntax (https://beancount.github.io/docs/beancount_language_syntax.html) - Document directive format
- CRA GIFI documentation (https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/rc4088/general-index-financial-information-gifi.html) - GIFI code ranges, Schedule 100/125 structure
- Existing codebase: `rapports.py`, `taxes/sommaire.py`, `dpa/calcul.py`, `pret_actionnaire/suivi.py`, `paie/moteur.py`, `comptes.beancount` - All source data already available

### Secondary (MEDIUM confidence)
- TaxCycle GIFI import docs (https://www.taxcycle.com/resources/help-topics/data-import/import-gifi/import-gifi-from-a-file/) - GIFI CSV format (column structure not fully documented)
- CRA filing deadlines (https://www.canada.ca/en/revenue-agency/news/newsroom/tax-tips/tax-tips-2025/businesses-have-different-filing-payment-deadlines-quick-reference.html) - T2, T4 deadlines
- Revenu Quebec RL-1 deadlines (https://www.revenuquebec.ca/en/businesses/rl-slips-and-summaries/sending-rl-slips-and-summaries/filing-deadline/) - RL-1 filing deadline
- Fava extension documentation (https://fava.pythonanywhere.com/example-beancount-file/help/extensions) - Extension class structure, report_title, templates

### Tertiary (LOW confidence)
- TaxCycle GIFI CSV exact column format - Only sample file reference available, not detailed specification; needs validation with actual TaxCycle installation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - WeasyPrint, Jinja2, Anthropic SDK are well-documented with Context7 verification; all fit the existing Python stack
- Architecture: HIGH - Existing codebase provides all data extraction; Phase 5 is primarily a formatting/presentation layer
- GIFI export format: MEDIUM - CRA GIFI codes are well-documented; TaxCycle import format specifics need validation
- Pitfalls: HIGH - WeasyPrint system deps, Decimal precision, and receipt image sizing are well-documented issues

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable domain; filing deadlines are annual)
