# Architecture Research

**Domain:** AI-assisted accounting system for a solo Quebec IT consultant (CCPC)
**Researched:** 2026-02-18
**Confidence:** MEDIUM-HIGH

## Recommendation: Beancount + Fava + Custom MCP + Quebec Plugins

Use **Beancount** as the ledger engine, **Fava** as the web dashboard foundation, a **custom Python MCP server** as the AI integration layer, and **custom Beancount plugins** for all Quebec-specific domain logic. This is Option C from the project context, enhanced with a purpose-built MCP server instead of relying on nascent third-party ones.

**Why Beancount over the alternatives:**

1. **Strict validation prevents silent errors** -- Beancount mandates explicit `open` directives for every account, catching typos that hledger/Ledger would silently accept as new accounts. For an accounting system where correctness matters more than convenience, this is non-negotiable.
2. **Python-native extensibility** -- Beancount's plugin system runs Python functions inside the core processing loop. You can inject CCA calculators, GST/QST validators, and payroll modules directly into the ledger's load pipeline. With hledger (Haskell) or Ledger (C++), extensibility is external -- you pipe data to/from the executable but cannot modify internal processing.
3. **Fava provides 80% of the web dashboard** -- Fava already has trial balance, income statement, balance sheet, journal views, BQL queries, document management, and a REST API. Building on Fava's extension system for Quebec-specific views is far less work than building a dashboard from scratch on top of hledger-web.
4. **smart_importer gives ML categorization out of the box** -- The `smart_importer` plugin predicts account postings from historical data, achieving ~95% accuracy per community reports. This handles the "rules-first" layer; the LLM (via MCP) handles edge cases.
5. **Plain-text, git-friendly** -- `.beancount` files version-control cleanly, satisfying the auditability requirement.

**Why NOT hledger:** hledger-mcp is more mature as an MCP server today, but hledger's Haskell codebase means Quebec-specific modules must be external scripts rather than integrated plugins. The MCP server advantage disappears once we build a custom one (which we need anyway for the approval workflow).

**Why NOT PyLedger:** Newest and least battle-tested. SQLite-backed rather than plain-text, which complicates git-based auditability. The built-in MCP is appealing but immature.

## System Overview

```
                         +-----------------------+
                         |   Claude (via MCP)    |
                         |  - Categorization     |
                         |  - Natural language    |
                         |    queries & reports   |
                         +----------+------------+
                                    |
                              MCP Protocol
                                    |
                         +----------v------------+
                         |   MCP Server          |
                         |   (Python, custom)    |
                         |  - Tool definitions   |
                         |  - Approval workflow  |
                         |  - Confidence scoring |
                         +--+------+----------+--+
                            |      |          |
              +-------------+      |          +-------------+
              |                    |                        |
   +----------v-------+  +--------v---------+  +-----------v---------+
   | Ingestion Layer   |  | Beancount Core   |  | Quebec Modules      |
   | - RBC CSV/OFX     |  | - Ledger files   |  | - Payroll engine    |
   | - PDF/receipt OCR  |  | - bean-check     |  | - GST/QST tracker  |
   | - beangulp import  |  | - BQL queries    |  | - CCA calculator   |
   | - smart_importer   |  | - Plugins        |  | - Shareholder loan  |
   +----------+--------+  +--------+---------+  +-----------+---------+
              |                    |                        |
              +------>  .beancount files (git)  <-----------+
                                   |
                         +---------v----------+
                         |   Fava (Web UI)     |
                         |  - Dashboard views  |
                         |  - Review/approval  |
                         |  - CPA export       |
                         |  - Custom extensions |
                         +---------------------+
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Ingestion Layer** | Parse bank CSVs/OFX, extract data from PDFs/receipts, normalize into Beancount transactions, apply rule-based + ML categorization | Beancount files (writes), MCP Server (receives edge cases) |
| **Beancount Core** | Source of truth for all financial data. Validates double-entry integrity, runs plugins, executes BQL queries | .beancount files (reads/validates), Fava (serves data), Quebec Modules (via plugin pipeline) |
| **Quebec Modules** | Domain-specific calculations: payroll deductions, GST/QST ITC/ITR, CCA depreciation schedules, shareholder loan tracking | Beancount Core (as plugins), MCP Server (exposes tools) |
| **MCP Server** | Bridge between Claude and the accounting system. Exposes tools for categorization, querying, reporting, and approval workflow | Claude (MCP protocol), Beancount Core (reads/writes), Ingestion Layer (triggers imports), Quebec Modules (triggers calculations) |
| **Fava (Web UI)** | Visual dashboard for transaction review, report viewing, document management, CPA export generation | Beancount Core (reads ledger), MCP Server (shares approval state) |
| **CLI** | Batch imports, automation scripts, power-user operations | Ingestion Layer (triggers), Beancount Core (reads), Quebec Modules (triggers) |

## Recommended Project Structure

```
compteqc/
+-- ledger/                     # Beancount data (git-tracked)
|   +-- main.beancount          # Master file with includes
|   +-- accounts.beancount      # Chart of accounts (open directives)
|   +-- 2026/
|   |   +-- 01-jan.beancount    # Monthly transaction files
|   |   +-- 02-feb.beancount
|   |   +-- payroll.beancount   # Payroll journal entries
|   |   +-- cca.beancount       # CCA depreciation entries
|   |   +-- adjustments.beancount
|   +-- prices.beancount        # Currency/commodity prices
|   +-- documents/              # Linked receipts/invoices (PDFs)
|
+-- src/
|   +-- ingestion/              # Data import pipeline
|   |   +-- rbc_csv.py          # RBC CSV importer (beangulp)
|   |   +-- rbc_ofx.py          # RBC OFX importer
|   |   +-- pdf_extractor.py    # Receipt/invoice OCR + extraction
|   |   +-- rules.py            # Rule-based categorization engine
|   |   +-- config.py           # Importer configuration
|   |
|   +-- quebec/                 # Quebec domain modules
|   |   +-- payroll.py          # Payroll calculation engine
|   |   +-- gst_qst.py         # GST/QST tracking + ITC/ITR
|   |   +-- cca.py              # CCA calculator (half-year rule)
|   |   +-- shareholder_loan.py # Shareholder loan tracker
|   |   +-- rates.py            # Annual rates (QPP, RQAP, EI, FSS, etc.)
|   |
|   +-- plugins/                # Beancount plugins
|   |   +-- cca_plugin.py       # Auto-generate CCA entries
|   |   +-- gst_qst_plugin.py   # Validate GST/QST on transactions
|   |   +-- loan_plugin.py      # Shareholder loan alerts
|   |
|   +-- mcp/                    # MCP server
|   |   +-- server.py           # MCP server entry point
|   |   +-- tools/              # Tool definitions
|   |   |   +-- categorize.py   # AI categorization tool
|   |   |   +-- query.py        # Ledger query tools
|   |   |   +-- report.py       # Report generation tools
|   |   |   +-- approve.py      # Approval workflow tools
|   |   |   +-- import_tool.py  # Import trigger tools
|   |   +-- prompts.py          # System prompts for Claude
|   |
|   +-- fava_ext/               # Fava extensions
|   |   +-- approval/           # Transaction approval UI
|   |   +-- cpa_export/         # CPA export package generator
|   |   +-- quebec_reports/     # Quebec-specific report views
|   |
|   +-- cli/                    # CLI commands
|   |   +-- import_cmd.py       # Batch import command
|   |   +-- payroll_cmd.py      # Run payroll command
|   |   +-- export_cmd.py       # CPA export command
|
+-- data/                       # Import staging (not git-tracked)
|   +-- inbox/                  # Incoming bank CSVs, receipts
|   +-- processed/              # Archived after import
|
+-- tests/
|   +-- test_payroll.py
|   +-- test_cca.py
|   +-- test_gst_qst.py
|   +-- test_importers.py
|
+-- pyproject.toml
```

### Structure Rationale

- **ledger/:** Beancount data separated from code. Monthly files keep individual files small and git diffs readable. The `main.beancount` includes everything via Beancount's `include` directive.
- **src/ingestion/:** Isolated import pipeline. Importers follow beangulp's protocol so they work with both CLI and Fava's import UI.
- **src/quebec/:** Pure Python modules with no Beancount dependency. Testable in isolation. Contain the formulas for payroll, CCA, GST/QST. Updated annually when rates change.
- **src/plugins/:** Thin wrappers that call into `src/quebec/` modules within Beancount's plugin pipeline. Keeps domain logic separate from Beancount integration.
- **src/mcp/:** Custom MCP server. Each tool is a separate module for maintainability. The server orchestrates reads/writes to the ledger.
- **src/fava_ext/:** Fava extensions for the approval workflow and CPA export. Uses Fava's extension API (subclass `FavaExtensionBase`, register endpoints and JS modules).
- **data/:** Ephemeral staging area for imports. Not version-controlled (financial CSVs should not be in git; the resulting beancount entries are).

## Architectural Patterns

### Pattern 1: Rules-First, LLM-for-Edge-Cases Categorization

**What:** A tiered categorization pipeline where deterministic rules handle the majority of transactions, smart_importer handles pattern-matched predictions, and the LLM (via MCP) handles only what the first two tiers cannot.

**When to use:** Every transaction import.

**Trade-offs:** More initial setup (writing rules) but dramatically lower error rates and API costs ($2-3/month vs unlimited). The 8.33% accuracy of pure-LLM approaches is unacceptable for accounting.

**Example:**
```python
def categorize_transaction(txn: Transaction) -> CategorizedTransaction:
    # Tier 1: Exact rules (handles ~60-70%)
    result = rules_engine.match(txn)
    if result and result.confidence >= 0.95:
        return result

    # Tier 2: ML prediction from smart_importer (handles ~20-25%)
    result = ml_predictor.predict(txn)
    if result and result.confidence >= 0.80:
        return result

    # Tier 3: LLM via MCP (handles ~5-10%)
    result = llm_categorize(txn, chart_of_accounts)
    if result and result.confidence >= 0.70:
        result.needs_review = True  # Always flag LLM results
        return result

    # Tier 4: Human review required
    return CategorizedTransaction(txn, account=None, needs_review=True)
```

### Pattern 2: Staging-then-Commit Approval Workflow

**What:** New transactions are written to a staging file (e.g., `pending.beancount`) with a `#pending` tag. The review UI shows these. On approval, entries move to the appropriate monthly file and the tag is removed.

**When to use:** All AI-categorized transactions before they become part of the official ledger.

**Trade-offs:** Adds a step before data is "real," but prevents unchecked AI errors from polluting the ledger. The CPA never sees pending entries.

**Example:**
```beancount
; In pending.beancount (staging)
2026-02-15 * "AMZN Mktp CA" "Amazon purchase" #pending
  confidence: "0.85"
  ai-source: "smart_importer"
  Expenses:Office:Supplies    45.99 CAD
  Liabilities:CreditCard:RBC

; After approval, moved to 2026/02-feb.beancount without #pending tag
2026-02-15 * "AMZN Mktp CA" "Amazon - Office supplies"
  Expenses:Office:Supplies    45.99 CAD
  Liabilities:CreditCard:RBC
```

### Pattern 3: Quebec Domain Modules as Pure Functions

**What:** All Quebec-specific calculations (payroll, CCA, GST/QST) are implemented as pure Python functions that take inputs and return results, with no side effects or Beancount dependencies. Thin Beancount plugin wrappers call these functions and generate entries.

**When to use:** All domain logic.

**Trade-offs:** More files (module + plugin wrapper) but testable without Beancount, reusable from CLI/MCP/API, and rates can be updated in a single `rates.py` file.

**Example:**
```python
# src/quebec/payroll.py -- pure function, no Beancount dependency
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class PayrollResult:
    gross_salary: Decimal
    federal_tax: Decimal
    quebec_tax: Decimal
    qpp_employee: Decimal
    qpp_employer: Decimal
    rqap_employee: Decimal
    rqap_employer: Decimal
    ei_employee: Decimal
    ei_employer: Decimal
    fss: Decimal
    cnesst: Decimal
    net_pay: Decimal

def calculate_payroll(
    gross_salary: Decimal,
    year: int = 2026,
    pay_period: str = "monthly",
    ytd_gross: Decimal = Decimal("0"),
) -> PayrollResult:
    rates = get_rates(year)
    # ... pure calculation logic ...
    return PayrollResult(...)

# src/plugins/payroll_plugin.py -- thin Beancount wrapper
def generate_payroll_entries(date, gross_salary, year):
    result = calculate_payroll(gross_salary, year)
    # Generate Beancount Transaction objects from PayrollResult
    return entries
```

## Data Flow

### Transaction Import Flow

```
[RBC CSV/OFX file]
      |
      v
[Ingestion Layer: rbc_csv.py]
      | parse, normalize
      v
[Rule Engine: rules.py]
      | Tier 1: exact match rules
      v
[smart_importer]
      | Tier 2: ML prediction
      v
[MCP -> Claude LLM]
      | Tier 3: edge cases only
      v
[pending.beancount]  <-- staged with #pending tag + confidence metadata
      |
      v
[Fava UI / MCP approval tool]
      | human review
      v
[2026/MM-month.beancount]  <-- committed to ledger
      |
      v
[Beancount plugin pipeline]
      | validation, GST/QST checks, CCA checks
      v
[bean-check passes] = source of truth
```

### Reporting / CPA Export Flow

```
[.beancount files]
      |
      v
[Beancount loader + plugins]
      | loads all entries, runs plugin pipeline
      v
[BQL queries / Fava API]
      | trial_balance, income_statement, balance_sheet
      v
[Quebec Modules]
      | payroll summary, CCA schedule, GST/QST summary
      v
[CPA Export Extension]
      | generates CSV + PDF package
      v
[CPA receives: trial balance, P&L, balance sheet,
 payroll schedule, CCA schedule, GST/QST schedule,
 shareholder loan summary, linked source documents]
```

### MCP Interaction Flow

```
[Claude Desktop / Claude Code]
      |
      | MCP protocol (stdio or streamable HTTP)
      v
[MCP Server: server.py]
      |
      +-- tool: categorize_transaction
      |     reads pending.beancount
      |     returns proposed categorization
      |
      +-- tool: query_ledger
      |     runs BQL against Beancount
      |     returns structured results
      |
      +-- tool: generate_report
      |     calls Fava API or bean-query
      |     returns formatted report
      |
      +-- tool: approve_transaction
      |     moves entry from pending to committed
      |
      +-- tool: run_payroll
      |     calls quebec/payroll.py
      |     writes entries to payroll.beancount
      |
      +-- tool: calculate_gst_qst
            calls quebec/gst_qst.py
            returns ITC/ITR summary
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Year 1 (single corp, ~500 txns/year) | Monolith is perfect. Single .beancount file set, single Fava instance, single MCP server. |
| Year 2-3 (add Enact revenue, credit card, ~1500 txns/year) | Split ledger includes by source (rbc-checking, rbc-cc, stripe). Add Stripe importer. Still single Beancount instance. |
| Multi-entity (consulting + product corp) | Separate ledger directories per entity. MCP server handles routing to correct entity. Fava supports multiple ledgers via separate instances or Fava's multi-file support. |

### Scaling Priorities

1. **First bottleneck: Import volume** -- As transaction count grows, batch import performance matters. Beancount handles 100K+ transactions in ~2 seconds, so this is a non-issue for years.
2. **Second bottleneck: Rule maintenance** -- As more vendors and transaction types appear, the rule engine needs to stay manageable. Use a YAML/TOML rule file rather than hardcoded Python so rules can be edited without code changes.

## Anti-Patterns

### Anti-Pattern 1: LLM as Calculator

**What people do:** Ask Claude to compute payroll deductions, CCA amounts, or GST/QST owing.
**Why it's wrong:** LLMs hallucinate numbers. Even small errors in tax calculations have legal consequences. The hledger-mcp community explicitly notes: "The LLM doesn't perform calculations directly. It utilizes hledger to manage all mathematical functions."
**Do this instead:** Quebec modules compute all numbers deterministically. The LLM triggers calculations and formats results but never invents a number.

### Anti-Pattern 2: Direct Ledger Writes from AI

**What people do:** Let the AI write directly to the production ledger without review.
**Why it's wrong:** Even at 95% categorization accuracy, 5% errors compound over a fiscal year (~25 wrong entries out of 500). These are hard to find retroactively.
**Do this instead:** All AI-generated entries go through the staging/approval workflow. The #pending tag makes unapproved entries visible but excluded from reports.

### Anti-Pattern 3: Monolithic Quebec Logic

**What people do:** Embed payroll formulas, CCA rules, and GST/QST logic directly in Beancount plugins or importers.
**Why it's wrong:** Annual rate changes (QPP ceiling changes every year, EI rates change, etc.) become a hunt through multiple files. Testing requires loading Beancount.
**Do this instead:** Pure Python modules in `src/quebec/` with a centralized `rates.py`. Beancount plugins are thin wrappers. CLI, MCP, and tests all call the same functions.

### Anti-Pattern 4: Building a Custom Web Dashboard from Scratch

**What people do:** Ignore Fava and build a React/Vue dashboard from scratch to display accounting data.
**Why it's wrong:** Fava already provides trial balance, income statement, balance sheet, journal, BQL query interface, document management, and import UI. Rebuilding this is months of wasted effort.
**Do this instead:** Extend Fava via its extension API (`FavaExtensionBase`). Add custom views for the approval workflow and CPA export. Use Fava's existing REST API for the MCP server to query data.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| RBC Bank (CSV/OFX) | File-based import via beangulp importer | Manual download for v1. No Plaid. OFX preferred over CSV for richer data. |
| Claude API (LLM) | MCP protocol (stdio for Claude Desktop, streamable HTTP for programmatic) | Only used for Tier 3 categorization edge cases + natural language queries. ~200-300 calls/month. |
| Receipt/invoice PDFs | Local OCR/extraction (pdf-extract, tesseract, or Claude vision via MCP) | Store originals in `ledger/documents/`, link via Beancount `document` directive. |
| CPA tools | CSV/Excel export from Fava extension | CPA imports into their tax software. Format TBD based on CPA preference. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Ingestion -> Ledger | File write (`.beancount`) | Importers write to `pending.beancount`. Never modify committed files. |
| MCP Server -> Beancount | Python API (`beancount.loader.load_file`) + file write | Reads via loader, writes by appending to `.beancount` files. |
| MCP Server -> Fava | HTTP API (`/api/query`, `/api/ledger_data`, etc.) | Fava runs as a separate process. MCP server calls its REST API for reports. |
| Quebec Modules -> Beancount Plugins | Python function calls | Plugins import from `src/quebec/` and call pure functions. No reverse dependency. |
| Fava Extensions -> Quebec Modules | Python imports | Extensions can call Quebec modules directly for rendering report data. |
| CLI -> Everything | Python imports | CLI commands import from ingestion, quebec, and mcp modules as needed. |

## Build Order (Dependencies)

The components have clear dependency chains that dictate build order:

```
Phase 1: Foundation (no dependencies)
  +-- Beancount ledger setup (chart of accounts, main.beancount)
  +-- Quebec rates module (rates.py -- pure data, no dependencies)
  +-- RBC CSV importer (beangulp protocol)

Phase 2: Core Engine (depends on Phase 1)
  +-- Rule-based categorization engine
  +-- GST/QST module (depends on rates.py)
  +-- Payroll calculation engine (depends on rates.py)
  +-- CCA calculator (depends on rates.py)

Phase 3: AI Layer (depends on Phase 1-2)
  +-- MCP server skeleton (tool definitions)
  +-- Categorization tool (uses rules from Phase 2)
  +-- smart_importer integration
  +-- LLM fallback for edge cases
  +-- Staging/approval workflow (pending.beancount)

Phase 4: Web Dashboard (depends on Phase 1-3)
  +-- Fava setup + configuration
  +-- Approval extension (review pending transactions)
  +-- Quebec report extensions (payroll, CCA, GST/QST views)
  +-- CPA export extension

Phase 5: Polish + Automation (depends on Phase 1-4)
  +-- CLI commands (batch import, payroll run, export)
  +-- PDF/receipt ingestion
  +-- Shareholder loan tracking
  +-- Invoice generation
```

**Rationale:**
- Phase 1 must come first because everything reads/writes `.beancount` files and uses Quebec rates.
- Phase 2 builds the domain logic that the AI layer and dashboard will expose.
- Phase 3 adds the AI categorization, which requires the rule engine and chart of accounts to exist.
- Phase 4 builds the UI on top of working data and calculations.
- Phase 5 adds convenience features that depend on all prior layers.

Each phase produces a usable vertical slice:
- After Phase 1: You can manually import and categorize RBC transactions.
- After Phase 2: Payroll and GST/QST calculations work via Python scripts.
- After Phase 3: Claude can categorize transactions and query the ledger.
- After Phase 4: Full review workflow in a browser.
- After Phase 5: Mostly hands-off operation.

## Sources

- [Beancount documentation -- plugin architecture, importer protocol](https://beancount.github.io/docs/) -- HIGH confidence (Context7 + official docs)
- [Fava REST API and extension system](https://github.com/beancount/fava) -- HIGH confidence (Context7 verified)
- [hledger-mcp server](https://github.com/iiAtlas/hledger-mcp) -- HIGH confidence (npm published, community-validated)
- [Beancount smart_importer](https://github.com/beancount/smart_importer) -- MEDIUM confidence (community reports of 95% accuracy, but depends on training data quality)
- [Beancount vs hledger vs Ledger comparison](https://beancount.io/forum/t/plain-text-accounting-showdown-2025-beancount-v3-hledger-or-ledger/42) -- MEDIUM confidence (community forum, multiple perspectives)
- [LLM accuracy for accounting (8.33% without prompting)](https://beancount.io/docs/Solutions/using-llms-to-automate-and-enhance-bookkeeping-with-beancount) -- MEDIUM confidence (FinNLP 2025 research cited)
- [Hybrid rules+LLM achieving 95% accuracy](https://beancount.io/forum/t/finally-got-95-automated-expense-categorization-working-with-beancount-llms/93) -- MEDIUM confidence (single user report, methodology documented)
- [MCP protocol -- streamable HTTP transport (March 2025)](https://www.anthropic.com/news/model-context-protocol) -- HIGH confidence (official Anthropic)
- [beangulp importer framework](https://github.com/beancount/beangulp) -- HIGH confidence (Context7 verified, official Beancount project)

---
*Architecture research for: AI-assisted accounting system (Quebec CCPC IT consultant)*
*Researched: 2026-02-18*
