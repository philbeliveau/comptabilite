# Roadmap: CompteQC

## Overview

CompteQC delivers a self-hosted, AI-assisted accounting system for a solo Quebec IT consultant's CCPC. The roadmap progresses from a working double-entry ledger with import capabilities, through Quebec-specific domain logic (payroll, GST/QST, CCA), into AI-powered categorization, then interactive tooling (MCP server, web dashboard), and finally reporting, CPA export, and document management. Each phase delivers a coherent, testable capability that builds on the previous.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Ledger Foundation and Import Pipeline** - Working Beancount ledger with Quebec COA, RBC import, rule-based categorization, and basic CLI
- [ ] **Phase 2: Quebec Domain Logic** - Payroll engine, GST/QST tracking, CCA schedules, and shareholder loan management
- [ ] **Phase 3: AI Categorization and Review Workflow** - ML and LLM categorization tiers, confidence scoring, staging/approval pipeline
- [ ] **Phase 4: MCP Server and Web Dashboard** - Claude integration via MCP tools and Fava-based web UI with custom extensions
- [ ] **Phase 5: Reporting, CPA Export, and Document Management** - Complete CPA package, invoicing, receipt ingestion, and automation alerts

## Phase Details

### Phase 1: Ledger Foundation and Import Pipeline
**Goal**: User can import RBC transactions into a working double-entry Beancount ledger with a Quebec-appropriate chart of accounts, rule-based categorization handles the majority of transactions, and basic CLI provides import and query capabilities
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, CAT-01, CLI-01, CLI-06
**Success Criteria** (what must be TRUE):
  1. User can run a CLI command to import an RBC CSV or OFX file and see normalized transactions appear in the Beancount ledger
  2. Imported transactions are automatically categorized by the rule engine with source tag "rule" and the ledger balances correctly (bean-check passes)
  3. User can query account balances and run basic reports (trial balance, P&L) via CLI and get correct results
  4. All ledger data is plain-text .beancount files under git version control with auto-commit on changes
  5. Chart of accounts is GIFI-mapped (1000-6999) and all monetary amounts use Decimal (never float)
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Fondation projet Python, ledger Beancount, plan comptable Quebec GIFI-mappe
- [ ] 01-02-PLAN.md — Importateurs RBC (CSV cheques, CSV carte, OFX) et moteur de categorisation par regles
- [ ] 01-03-PLAN.md — CLI `cqc` : commandes d'import et de rapports en francais

### Phase 2: Quebec Domain Logic
**Goal**: User can run payroll with all Quebec deductions calculated correctly, GST/QST is tracked separately on all transactions with ITC/ITR, capital assets are tracked with CCA schedules, and shareholder loan balances are monitored with deadline alerts
**Depends on**: Phase 1
**Requirements**: PAY-01, PAY-02, PAY-03, PAY-04, PAY-05, PAY-06, PAY-07, PAY-08, PAY-09, PAY-10, PAY-11, PAY-12, TAX-01, TAX-02, TAX-03, TAX-04, TAX-05, TAX-06, CCA-01, CCA-02, CCA-03, CCA-04, CCA-05, CCA-06, LOAN-01, LOAN-02, LOAN-03, LOAN-04, CLI-04
**Success Criteria** (what must be TRUE):
  1. User can run payroll for a gross salary amount via CLI and the system produces correct journal entries with QPP (base + additional), RQAP, EI (Quebec rate), FSS, CNESST, labour standards, and both federal (with 16.5% abatement) and Quebec income tax withholdings
  2. Every business expense transaction in the ledger has GST and QST tracked separately (never combined rate), and the system produces a net remittance summary by filing period
  3. Capital assets over $500 are tracked by CCA class with half-year rule applied, declining balance depreciation calculated, and year-end CCA entries generated as Beancount transactions
  4. Shareholder loan account (1800) tracks all personal-vs-business transactions and the system alerts at 9 months, 11 months, and 30 days before the s.15(2) inclusion date
  5. All payroll and tax rates are config-driven in rates.py and year-to-date totals stop contributions at annual maximums
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD
- [ ] 02-03: TBD
- [ ] 02-04: TBD

### Phase 3: AI Categorization and Review Workflow
**Goal**: Transactions that the rule engine cannot categorize are handled by ML prediction and LLM classification with confidence scoring, and all AI-categorized transactions go through a human review workflow before reaching the official ledger
**Depends on**: Phase 1, Phase 2
**Requirements**: CAT-02, CAT-03, CAT-04, CAT-05, CAT-06, CAT-07, CAT-08, CAT-09, CAT-10, CAT-11, CLI-02, CLI-03
**Success Criteria** (what must be TRUE):
  1. User can run the categorization pipeline via CLI and transactions flow through rules, then smart_importer ML, then Claude LLM -- each tier only processes what the previous tier could not handle
  2. Every categorized transaction carries a confidence score and source tag (rule/ml/llm/human), and transactions below 80% confidence are flagged for mandatory review
  3. AI-categorized transactions land in pending.beancount with #pending tag, and user can approve, reject, or recategorize them via CLI before they move to monthly ledger files
  4. Transactions over $500 are auto-flagged as potential CAPEX with a suggested CCA class
  5. User corrections feed back into the rule engine (auto-generate rules after repeated identical corrections) and LLM categorizations are stored with prompt/response for drift detection
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD
- [ ] 03-03: TBD

### Phase 4: MCP Server and Web Dashboard
**Goal**: Claude can interact with the accounting system through MCP tools for querying, categorizing, and approving transactions, and the user has a web-based dashboard for ledger exploration, transaction approval, and Quebec-specific report views
**Depends on**: Phase 3
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06, WEB-01, WEB-02, WEB-03, WEB-04, WEB-05
**Success Criteria** (what must be TRUE):
  1. Claude can query ledger balances, propose categories for transactions, run payroll summaries, and approve/reject pending transactions through MCP tools
  2. MCP server supports a read-only mode for safe exploration and is built with the official Python MCP SDK (mcp>=1.25,<2)
  3. Fava serves as the web UI showing trial balance, P&L, and balance sheet with correct Quebec chart of accounts
  4. Custom Fava extensions provide a pending transaction approval queue and Quebec-specific report views (payroll, CCA, GST/QST) in the browser
  5. AI-categorized transactions in the dashboard show their confidence score and source tag visually
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD

### Phase 5: Reporting, CPA Export, and Document Management
**Goal**: User can generate a complete year-end CPA package that the accountant can review in under one hour, invoices can be created for consulting clients, receipts can be ingested and matched to transactions, and the system tracks filing deadlines with alerts
**Depends on**: Phase 2, Phase 4
**Requirements**: CPA-01, CPA-02, CPA-03, CPA-04, CPA-05, CPA-06, CPA-07, CPA-08, CPA-09, AUTO-01, AUTO-02, AUTO-03, INV-01, INV-02, INV-03, DOC-01, DOC-02, DOC-03, DOC-04, CLI-05
**Success Criteria** (what must be TRUE):
  1. User can generate the full CPA export package via CLI (trial balance, P&L, balance sheet, payroll schedule, CCA schedule, GST/QST reconciliation, shareholder loan continuity) in both CSV and PDF formats
  2. GIFI-mapped export validates Schedule 100 balances before generation and all reports are importable into TaxCycle or similar CPA software
  3. User can generate professional invoices for consulting clients with correct GST/QST, track payment status (sent/paid/overdue), and invoices link to accounts receivable entries in the ledger
  4. User can upload receipt/invoice PDFs and images, AI extracts vendor/date/amount/tax breakdown via Claude Vision, and extracted data matches to bank transactions for reconciliation
  5. Filing deadline calendar sends reminders (T4/RL-1, GST/QST, T2/CO-17 deadlines) and a year-end checklist verifies shareholder loan balance, CCA schedule, GST/QST reconciliation before generating the CPA package
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD
- [ ] 05-03: TBD
- [ ] 05-04: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Ledger Foundation and Import Pipeline | 0/3 | Not started | - |
| 2. Quebec Domain Logic | 0/4 | Not started | - |
| 3. AI Categorization and Review Workflow | 0/3 | Not started | - |
| 4. MCP Server and Web Dashboard | 0/3 | Not started | - |
| 5. Reporting, CPA Export, and Document Management | 0/4 | Not started | - |
