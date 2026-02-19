# CompteQC

**Automated accounting system for a solo incorporated IT consultant in Quebec.**

CompteQC (`cqc`) automates the full bookkeeping lifecycle for a Canadian-Controlled Private Corporation (CCPC) in Quebec: transaction ingestion, AI-powered categorization, payroll with exact provincial/federal formulas, GST/QST tracking, CCA schedules, shareholder loan monitoring, and year-end CPA package generation -- all backed by [Beancount](https://beancount.github.io/) double-entry accounting.

The goal is **not** to replace the accountant, but to reduce the bookkeeping and data-prep load so the CPA can review everything in under one hour and focus on validation and optimization.

## Architecture

```
Bank CSV/OFX ─┐
Receipts (PDF) ┤    ┌─────────────┐    ┌──────────────┐    ┌────────────────┐
Payment data ──┼──> │  Ingestion   │──> │ AI Pipeline  │──> │ Human Review   │
               │    └─────────────┘    │ Rules > ML > │    │ Approve/Reject │
               │                       │    LLM       │    └───────┬────────┘
               │                       └──────────────┘            │
               │                                                   v
               │    ┌─────────────┐    ┌──────────────┐    ┌──────────────┐
               └──> │  Beancount   │<── │  Ledger Mgmt │<── │  Auto-commit │
                    │  Ledger      │    │  (monthly)   │    │  (git)       │
                    └──────┬──────┘    └──────────────┘    └──────────────┘
                           │
              ┌────────────┼────────────┬──────────────┐
              v            v            v              v
        ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐
        │ Fava Web │ │ CLI      │ │ MCP      │ │ Reports   │
        │ (8 ext.) │ │ (cqc)   │ │ Server   │ │ & Export  │
        └──────────┘ └──────────┘ └──────────┘ └───────────┘
```

## Features

- **Transaction ingestion** -- RBC chequing/credit card CSV and OFX importers with auto-deduplication and payee normalization
- **3-tier AI categorization** -- Rules engine (confidence 1.0) -> sklearn ML (smart-importer) -> LLM via OpenRouter; with CAPEX detection and configurable auto-approval thresholds
- **Review workflow** -- Pending transactions staged in `pending.beancount`; approve, reject, or recategorize with learning feedback loop that auto-generates rules
- **Quebec payroll** -- Full calculation of QPP (base + supp1 + supp2), RQAP, EI (Quebec rate), FSS, CNESST, normes du travail, federal and Quebec income tax with bracket annualization (T4127 122nd edition)
- **GST/QST tracking** -- Per-transaction tax calculation, period summaries (annual/quarterly), input tax credits
- **CCA/DPA schedules** -- Asset registry, half-year rule, pool management across classes 8, 10, 12, 50, 54
- **Shareholder loan monitoring** -- Balance tracking, movement detection, ITA s.15(2) countdown alerts (graduated: 11mo, 9mo, 30d, exceeded)
- **Invoice management** -- Create, track (draft/sent/paid/overdue), generate PDF via WeasyPrint, write AR/payment journal entries
- **Receipt management** -- Upload, Claude Vision extraction (vendor, date, taxes, total), fuzzy match to ledger transactions, Beancount document linking
- **Filing deadline calendar** -- T2, CO-17, GST/QST, payroll remittances, corporate installments with urgency alerts
- **Financial reports** -- Trial balance, income statement, balance sheet, GIFI code export for TaxCycle
- **8 Fava web extensions** -- Approval queue, payroll dashboard, GST/QST, CCA, shareholder loan, deadlines, receipts, CPA export
- **MCP server** -- 12 tools for Claude Desktop/Code integration (ledger queries, categorization, approval, payroll)

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| Ledger engine | Beancount 3.2 + beangulp + beanquery |
| CLI | Typer + Rich |
| Web UI | Fava 1.30 (with 8 custom extensions) |
| AI / LLM | Anthropic SDK (Claude Vision), OpenAI SDK via OpenRouter |
| ML | smart-importer (sklearn) |
| MCP server | FastMCP (`mcp>=1.25`) |
| Data validation | Pydantic v2 |
| PDF generation | WeasyPrint + Jinja2 |
| Package manager | uv |

## Installation

```bash
# Requires Python 3.12+
git clone <repo-url> && cd comptabilite
uv sync
```

### Environment variables

Create a `.env` file:

```env
ANTHROPIC_API_KEY=sk-ant-...    # Receipt extraction (Claude Vision)
OPENROUTER_API_KEY=sk-or-...    # LLM transaction categorization
```

## Usage

### CLI (`cqc`)

```bash
# Import transactions
cqc importer fichier bank-export.csv
cqc importer fichier bank-export.ofx

# Review pending transactions
cqc reviser liste
cqc reviser approuver all
cqc reviser recategoriser 3 Depenses:TI:Logiciels

# Payroll
cqc paie lancer 5000 --dry-run          # Preview
cqc paie lancer 5000 --nb-periodes 24   # Run and write to ledger

# Reports
cqc rapport balance                      # Trial balance
cqc rapport resultats --debut 2026-01-01 # Income statement
cqc rapport bilan                        # Balance sheet

# Invoices
cqc facture creer --client "Acme" --description "Consultation" --prix 150 --heures 40
cqc facture pdf FAC-2026-001
cqc facture payer FAC-2026-001

# Receipts
cqc recu telecharger receipt.pdf

# Deadlines
cqc echeances calendrier
cqc echeances rappels
```

### Fava (web UI)

```bash
fava ledger/main.beancount
# Opens at http://localhost:5000
```

Custom extensions add tabs for: approval queue, payroll dashboard, GST/QST summaries, CCA schedules, shareholder loan tracking, filing deadlines, receipts, and CPA export.

### MCP Server (Claude Code / Claude Desktop)

The MCP server lets you talk to your accounting data directly through Claude. Claude reads your Beancount ledger into memory and exposes 13 tools for querying and modifying it.

#### Setup with Claude Code

From the project directory, run once:

```bash
claude mcp add compteqc -- uv run python -m compteqc.mcp
```

Then restart Claude Code (exit and relaunch). That's it -- Claude now has access to your ledger.

#### Setup with Claude Desktop

Add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "compteqc": {
      "command": "uv",
      "args": ["run", "python", "-m", "compteqc.mcp"],
      "cwd": "/path/to/comptabilite"
    }
  }
}
```

#### What you can ask Claude

Once the MCP server is connected, just ask in plain language:

```
"What are my account balances?"
"Show me the trial balance"
"What's my income statement for January?"
"What's my GST/QST situation?"
"Show me the CCA schedule"
"What's the shareholder loan status?"
"Categorize this: Bell Canada, internet, $85"
"Show me pending transactions"
"Approve all pending transactions"
"Run a payroll dry-run for $4,230.77 gross"
```

Claude reads the Beancount ledger at `ledger/main.beancount`, parses it into memory, and answers from the live data. After any mutation (approving transactions, running payroll), the ledger is re-read automatically.

#### Environment variables

- `COMPTEQC_LEDGER` -- path to `main.beancount` (default: `ledger/main.beancount`)
- `COMPTEQC_READONLY` -- set to `true` to block all mutations (query-only mode)

#### Available tools

| Tool | Type | Description |
|------|------|-------------|
| `soldes_comptes` | query | Account balances (optional filter) |
| `balance_verification` | query | Trial balance (debits = credits check) |
| `etat_resultats` | query | Income statement (optional date range) |
| `bilan` | query | Balance sheet |
| `sommaire_tps_tvq` | query | GST/QST summary by period |
| `etat_dpa` | query | CCA/depreciation schedule by class |
| `etat_pret_actionnaire` | query | Shareholder loan status + s.15(2) alerts |
| `proposer_categorie` | mutation | AI-categorize a transaction (rules > ML > LLM) |
| `lister_pending_tool` | query | List pending transactions awaiting review |
| `approuver_lot` | mutation | Batch-approve pending transactions ($2,000 guardrail) |
| `rejeter` | mutation | Reject a pending transaction (with optional correction) |
| `calculer_paie_tool` | query | Payroll dry-run (preview without writing) |
| `lancer_paie` | mutation | Run payroll and write to ledger |

## Project Structure

```
src/compteqc/
├── models/           # TransactionNormalisee (Pydantic, all Decimal)
├── ingestion/        # RBC CSV/OFX importers
├── categorisation/   # 3-tier AI pipeline (rules -> ML -> LLM)
├── ledger/           # File management, git auto-commit, validation
├── quebec/           # Quebec/federal domain logic
│   ├── paie/         #   Payroll engine (contributions, taxes, journals)
│   ├── taxes/        #   GST/QST calculation and summaries
│   ├── dpa/          #   CCA/DPA schedules and asset registry
│   └── pret_actionnaire/  # Shareholder loan tracking + s.15(2) alerts
├── factures/         # Invoice lifecycle and PDF generation
├── documents/        # Receipt upload, AI extraction, matching
├── echeances/        # Filing deadline calendar
├── rapports/         # Financial reports + GIFI export
├── cli/              # Typer CLI commands
├── fava_ext/         # 8 Fava web extensions
└── mcp/              # MCP server + tool modules

ledger/
├── main.beancount        # Main file (includes all others)
├── comptes.beancount     # Chart of accounts (GIFI-annotated, French)
├── pending.beancount     # Transactions awaiting review
└── 2026/                 # Monthly transaction files
    ├── 01.beancount
    └── 02.beancount

rules/
└── categorisation.yaml   # Transaction categorization rules
```

## Development

```bash
uv run pytest                      # Run tests
uv run pytest --cov=compteqc      # With coverage
uv run ruff check src/             # Lint
uv run mypy src/                   # Type check
```

The test suite covers all modules: importers, categorization pipeline, payroll calculations, tax formulas, CCA logic, shareholder loans, ledger management, CLI commands, MCP tools, and Fava extensions.

## What This System Does NOT Do

- Generate or file tax returns (T2, CO-17, T1/TP-1, T4/Releve 1, GST/QST returns)
- Provide tax advice or legal opinions
- Silently invent accounting categories or numbers

It prepares clean, auditable data so the CPA and filing software can handle the rest.

## License

Private project. All rights reserved.
