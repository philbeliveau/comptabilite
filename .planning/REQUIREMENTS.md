# Requirements: CompteQC

**Defined:** 2026-02-18
**Core Value:** Every dollar that flows through the corporation is correctly categorized, traceable to source documents, and ready for CPA review — without manual data entry.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [x] **FOUND-01**: System uses Beancount v3 as double-entry ledger engine with immutable append-only journal
- [x] **FOUND-02**: Chart of accounts is GIFI-mapped (accounts 1000-6999) for Quebec IT consultant CCPC
- [x] **FOUND-03**: All monetary amounts stored as Python Decimal (never float), GST and QST stored separately per transaction
- [x] **FOUND-04**: Ledger data is plain-text .beancount files, git-versioned with auto-commit on changes
- [x] **FOUND-05**: Project structure follows modular architecture (ledger/, src/ingestion/, src/quebec/, src/mcp/, src/fava_ext/, src/cli/)

### Data Ingestion

- [x] **INGEST-01**: User can import RBC business bank account transactions from CSV file
- [x] **INGEST-02**: User can import RBC business credit card transactions from CSV file
- [x] **INGEST-03**: User can import RBC transactions from OFX/QFX file
- [x] **INGEST-04**: Imported transactions are normalized (date, amount in CAD, payee, description, memo)
- [x] **INGEST-05**: Raw import files are archived in data/processed/ with import metadata

### Categorization

- [x] **CAT-01**: Rule-based engine categorizes transactions using configurable YAML/TOML rules (handles ~60-70%)
- [ ] **CAT-02**: smart_importer ML predicts account postings from historical data (handles ~20-25% of remainder)
- [ ] **CAT-03**: Claude LLM categorizes remaining edge cases, constrained to closed chart of accounts list
- [ ] **CAT-04**: Every categorization has a confidence score and source tag (rule/ml/llm/human)
- [ ] **CAT-05**: Transactions below 80% confidence are flagged for mandatory human review
- [ ] **CAT-06**: AI-categorized transactions go to pending.beancount staging file with #pending tag
- [ ] **CAT-07**: User can approve, reject, or recategorize pending transactions
- [ ] **CAT-08**: Approved transactions move from pending to monthly ledger files
- [ ] **CAT-09**: Transactions >$500 are auto-flagged as potential CAPEX with suggested CCA class
- [ ] **CAT-10**: User corrections feed back into rule engine (auto-generate rules after N identical corrections)
- [ ] **CAT-11**: LLM categorizations stored with prompt/response for drift detection

### Quebec Payroll

- [x] **PAY-01**: User can run payroll for a given gross salary amount and pay period
- [x] **PAY-02**: System calculates QPP base (5.3%), QPP additional 1 (1.0%), QPP additional 2 (4.0%) with correct maximums and exemptions
- [x] **PAY-03**: System calculates RQAP employer (0.602%) and employee (0.430%) contributions
- [x] **PAY-04**: System calculates EI at Quebec rate (employer 1.82%, employee 1.30%) with MIE cap
- [x] **PAY-05**: System calculates FSS (1.65% for payroll under $1M, service sector)
- [x] **PAY-06**: System calculates CNESST based on assigned classification rate
- [x] **PAY-07**: System calculates labour standards contribution (0.06%)
- [x] **PAY-08**: System calculates federal income tax withholding with Quebec 16.5% abatement
- [x] **PAY-09**: System calculates Quebec provincial income tax withholding using TP-1015.F-V formulas
- [x] **PAY-10**: System tracks year-to-date totals and stops contributions at annual maximums
- [x] **PAY-11**: Payroll generates complete journal entries (salary expense, deductions, employer contributions, net pay)
- [x] **PAY-12**: All payroll rates are config-driven in rates.py, updatable annually

### GST/QST

- [x] **TAX-01**: System tracks GST collected (5%) and QST collected (9.975%) on revenue separately
- [x] **TAX-02**: System tracks GST paid and QST paid on business expenses for ITC/ITR claims
- [x] **TAX-03**: GST and QST are calculated separately per line item, each rounded independently (never combined rate)
- [x] **TAX-04**: System generates net GST/QST remittance summary by filing period
- [x] **TAX-05**: System handles GST/QST-exempt items (financial services, etc.)
- [x] **TAX-06**: Automated reconciliation check ensures GST and QST returns derive from identical transaction sets

### CCA (Capital Cost Allowance)

- [x] **CCA-01**: System tracks capital assets by CCA class (8, 10, 12, 50, 54)
- [x] **CCA-02**: Half-year rule automatically applied for new acquisitions
- [x] **CCA-03**: Declining balance depreciation calculated per class with correct rates
- [x] **CCA-04**: UCC (undepreciated capital cost) schedule maintained per class
- [x] **CCA-05**: System handles disposals and recapture/terminal loss calculations
- [x] **CCA-06**: CCA entries generated as Beancount transactions for year-end

### Shareholder Loan

- [x] **LOAN-01**: Dedicated shareholder loan account (1800) tracks all personal-vs-business transactions
- [x] **LOAN-02**: System computes repayment deadline (fiscal year-end + 1 year) per s.15(2)
- [x] **LOAN-03**: Alerts at 9 months, 11 months, and 30 days before inclusion date
- [x] **LOAN-04**: System flags circular loan-repayment-reborrow patterns

### Invoice Generation

- [ ] **INV-01**: User can generate professional invoices for consulting clients with GST/QST
- [ ] **INV-02**: Invoice tracks payment status (sent, paid, overdue)
- [ ] **INV-03**: Invoices link to accounts receivable entries in the ledger

### Receipt/Document Management

- [ ] **DOC-01**: User can upload receipt/invoice PDFs and images
- [ ] **DOC-02**: AI extracts vendor, date, amount, tax breakdown from uploaded documents (Claude Vision)
- [ ] **DOC-03**: Extracted data can be matched to bank transactions for reconciliation
- [ ] **DOC-04**: Documents stored in ledger/documents/ and linked via Beancount document directive

### MCP Server

- [ ] **MCP-01**: Custom MCP server exposes ledger query tools (balances, reports, account details)
- [ ] **MCP-02**: MCP server exposes categorization tools (propose category for transaction)
- [ ] **MCP-03**: MCP server exposes payroll tools (run payroll, get payroll summary)
- [ ] **MCP-04**: MCP server exposes approval workflow tools (list pending, approve, reject)
- [ ] **MCP-05**: MCP server supports read-only mode for safe exploration
- [ ] **MCP-06**: MCP server built with official Python MCP SDK (mcp>=1.25,<2)

### Web Dashboard

- [ ] **WEB-01**: Fava serves as base web UI for ledger browsing, trial balance, P&L, balance sheet
- [ ] **WEB-02**: Custom Fava extension for transaction approval workflow (pending queue, approve/reject)
- [ ] **WEB-03**: Custom Fava extension for Quebec-specific report views (payroll, CCA, GST/QST)
- [ ] **WEB-04**: Custom Fava extension for CPA export package generation
- [ ] **WEB-05**: Dashboard shows confidence indicators for AI-categorized transactions

### CPA Export

- [ ] **CPA-01**: System generates trial balance (CSV + PDF)
- [ ] **CPA-02**: System generates income statement / P&L (CSV + PDF)
- [ ] **CPA-03**: System generates balance sheet (CSV + PDF)
- [ ] **CPA-04**: System generates payroll summary schedule (gross, deductions, employer contributions)
- [ ] **CPA-05**: System generates CCA schedule by class (cost, half-year, CCA claimed, UCC)
- [ ] **CPA-06**: System generates GST/QST reconciliation summary by period
- [ ] **CPA-07**: System generates shareholder loan continuity schedule
- [ ] **CPA-08**: GIFI-mapped export validates Schedule 100 balances before generation
- [ ] **CPA-09**: All reports available as CSV for CPA import into TaxCycle or similar

### CLI

- [x] **CLI-01**: User can import bank files via CLI command
- [ ] **CLI-02**: User can run categorization pipeline via CLI command
- [ ] **CLI-03**: User can review and approve pending transactions via CLI
- [x] **CLI-04**: User can run payroll via CLI command
- [ ] **CLI-05**: User can generate CPA export package via CLI command
- [x] **CLI-06**: User can query ledger balances and run reports via CLI

### Automation & Alerts

- [ ] **AUTO-01**: Filing deadline calendar with reminders (T4/RL-1 Feb 28, GST/QST Mar 31, T2/CO-17 Jun 30, etc.)
- [ ] **AUTO-02**: Year-end checklist: verify shareholder loan balance, confirm CCA schedule, reconcile GST/QST, generate CPA package
- [ ] **AUTO-03**: Payroll remittance tracking (amounts owed vs remitted, upcoming deadlines)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Multi-Entity

- **MULTI-01**: Support for Enact product entity alongside consulting corp
- **MULTI-02**: Consolidated reporting across entities

### Additional Integrations

- **INTEG-01**: Stripe payment processor import (when Enact generates revenue)
- **INTEG-02**: Wise/PayPal import (when international payments begin)
- **INTEG-03**: Additional bank imports (Desjardins, National Bank)

### Advanced Features

- **ADV-01**: Salary vs dividend optimization modeling (present data for CPA decision)
- **ADV-02**: Cash flow forecasting based on historical patterns
- **ADV-03**: PSB risk indicator dashboard (number of clients, control factors)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Tax return filing (T2, CO-17, T1/TP-1, T4/RL-1, GST/QST returns) | CPA handles filing; legal liability; CRA XML schemas change annually |
| Tax advice or legal opinions | Professional liability; depends on personal circumstances |
| Real-time bank sync (Plaid/Flinks) | Subscription cost, security surface, unnecessary for ~30 txns/month |
| Multi-currency support | All clients pay CAD through Procom; no USD revenue currently |
| Mobile app | Web dashboard with responsive design is sufficient |
| AI-generated financial reports/commentary | LLMs hallucinate numbers; reports must be mathematically exact |
| Multi-user / role-based access | Solo system; CPA gets export package, not a login |
| Automated payment / bank transfer | Security risk; unnecessary for ~5 payments/month |
| Inventory / project costing | Service business with near-zero COGS |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Complete |
| FOUND-05 | Phase 1 | Complete |
| INGEST-01 | Phase 1 | Complete |
| INGEST-02 | Phase 1 | Complete |
| INGEST-03 | Phase 1 | Complete |
| INGEST-04 | Phase 1 | Complete |
| INGEST-05 | Phase 1 | Complete |
| CAT-01 | Phase 1 | Complete |
| CAT-02 | Phase 3 | Pending |
| CAT-03 | Phase 3 | Pending |
| CAT-04 | Phase 3 | Pending |
| CAT-05 | Phase 3 | Pending |
| CAT-06 | Phase 3 | Pending |
| CAT-07 | Phase 3 | Pending |
| CAT-08 | Phase 3 | Pending |
| CAT-09 | Phase 3 | Pending |
| CAT-10 | Phase 3 | Pending |
| CAT-11 | Phase 3 | Pending |
| PAY-01 | Phase 2 | Complete |
| PAY-02 | Phase 2 | Complete |
| PAY-03 | Phase 2 | Complete |
| PAY-04 | Phase 2 | Complete |
| PAY-05 | Phase 2 | Complete |
| PAY-06 | Phase 2 | Complete |
| PAY-07 | Phase 2 | Complete |
| PAY-08 | Phase 2 | Complete |
| PAY-09 | Phase 2 | Complete |
| PAY-10 | Phase 2 | Complete |
| PAY-11 | Phase 2 | Complete |
| PAY-12 | Phase 2 | Complete |
| TAX-01 | Phase 2 | Complete |
| TAX-02 | Phase 2 | Complete |
| TAX-03 | Phase 2 | Complete |
| TAX-04 | Phase 2 | Complete |
| TAX-05 | Phase 2 | Complete |
| TAX-06 | Phase 2 | Complete |
| CCA-01 | Phase 2 | Complete |
| CCA-02 | Phase 2 | Complete |
| CCA-03 | Phase 2 | Complete |
| CCA-04 | Phase 2 | Complete |
| CCA-05 | Phase 2 | Complete |
| CCA-06 | Phase 2 | Complete |
| LOAN-01 | Phase 2 | Complete |
| LOAN-02 | Phase 2 | Complete |
| LOAN-03 | Phase 2 | Complete |
| LOAN-04 | Phase 2 | Complete |
| INV-01 | Phase 5 | Pending |
| INV-02 | Phase 5 | Pending |
| INV-03 | Phase 5 | Pending |
| DOC-01 | Phase 5 | Pending |
| DOC-02 | Phase 5 | Pending |
| DOC-03 | Phase 5 | Pending |
| DOC-04 | Phase 5 | Pending |
| MCP-01 | Phase 4 | Pending |
| MCP-02 | Phase 4 | Pending |
| MCP-03 | Phase 4 | Pending |
| MCP-04 | Phase 4 | Pending |
| MCP-05 | Phase 4 | Pending |
| MCP-06 | Phase 4 | Pending |
| WEB-01 | Phase 4 | Pending |
| WEB-02 | Phase 4 | Pending |
| WEB-03 | Phase 4 | Pending |
| WEB-04 | Phase 4 | Pending |
| WEB-05 | Phase 4 | Pending |
| CPA-01 | Phase 5 | Pending |
| CPA-02 | Phase 5 | Pending |
| CPA-03 | Phase 5 | Pending |
| CPA-04 | Phase 5 | Pending |
| CPA-05 | Phase 5 | Pending |
| CPA-06 | Phase 5 | Pending |
| CPA-07 | Phase 5 | Pending |
| CPA-08 | Phase 5 | Pending |
| CPA-09 | Phase 5 | Pending |
| CLI-01 | Phase 1 | Complete |
| CLI-02 | Phase 3 | Pending |
| CLI-03 | Phase 3 | Pending |
| CLI-04 | Phase 2 | Complete |
| CLI-05 | Phase 5 | Pending |
| CLI-06 | Phase 1 | Complete |
| AUTO-01 | Phase 5 | Pending |
| AUTO-02 | Phase 5 | Pending |
| AUTO-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 85 total
- Mapped to phases: 85
- Unmapped: 0

---
*Requirements defined: 2026-02-18*
*Last updated: 2026-02-18 after roadmap creation*
