# Feature Research

**Domain:** AI-assisted accounting system for a solo Quebec IT consultant (CCPC)
**Researched:** 2026-02-18
**Confidence:** HIGH (domain well-understood, user context is specific, features derived from real-world tools and community patterns)

## Feature Landscape

### Table Stakes (Users Expect These)

Features the system is useless without. If any of these are missing, the tool does not fulfil its core purpose of "every dollar correctly categorized, traceable, CPA-ready."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Transaction import (CSV/OFX)** | Without import, you are doing manual data entry — the thing the system exists to eliminate | LOW | RBC CSV/OFX only for v1. Parser is straightforward; format rarely changes. Normalize dates, amounts, descriptions. |
| **Quebec chart of accounts** | Double-entry requires a COA. IT-consultant-specific COA already designed (1000-6999). Without it, every categorization is meaningless. | LOW | Already researched. Load from config file. Must map to CRA/RQ categories for CPA export. |
| **Double-entry ledger with audit trail** | The accounting engine. Without proper debits/credits that balance, this is a spreadsheet not an accounting system. | HIGH | Core architectural decision (HLedger vs Beancount vs PyLedger vs custom). Every entry must reference source document. Immutable append-only log. |
| **Rule-based transaction categorization** | Handles 60-70% of transactions deterministically. Rules are transparent, auditable, and do not hallucinate. | MEDIUM | Pattern matching on payee/description/amount. e.g., "PROCOM" -> 4000 Consulting Revenue. Configurable rules file. Must run before LLM. |
| **LLM-assisted categorization (edge cases)** | Handles the 30-40% that rules miss. Community-proven hybrid approach achieves 95% accuracy vs 8% LLM-only. | MEDIUM | Claude API for ambiguous transactions. Must constrain to existing COA (no invented accounts). Confidence scoring mandatory. |
| **Confidence scoring + human review workflow** | Without human verification of AI decisions, you cannot trust the data. CPA will not accept unreviewed AI output. | MEDIUM | Flag anything below 80% confidence. Batch review interface. Approve/reject/recategorize. Corrections feed back into rules. |
| **GST (5%) / QST (9.975%) tracking** | Legal obligation. ~$230K revenue = mandatory registration. Every business expense needs ITC/ITR calculated. | MEDIUM | Separate GST/QST accounts for collected and paid. Net calculation per filing period. Must handle exempt items (e.g., financial services, basic groceries). |
| **CPA export package** | The entire point: "CPA reviews in <1 hour." Without clean exports, the system fails its core mission. | MEDIUM | Trial balance, P&L, balance sheet, GL detail, GST/QST summary, payroll summary, CCA schedule. CSV + PDF. Must match what CPAs expect. |
| **Payroll calculation engine** | Solo owner-employee must calculate correct source deductions every pay period. QPP, RQAP, EI, FSS, CNESST, labour standards, federal+Quebec income tax. | HIGH | All formulas already documented with 2026 rates. Must handle annual maximums, QPP exemption, Quebec-specific EI rate, FSS thresholds. Rates change annually — config-driven. |
| **CCA tracking (capital cost allowance)** | Assets over $500 must be capitalized, not expensed. Half-year rule, declining balance, class-specific rates. | MEDIUM | Classes 8, 10, 12, 50, 54 relevant for IT consultant. Track UCC per class. Half-year rule in acquisition year. Handle disposals. |
| **Shareholder loan account tracking** | CRA aggressively audits this. Personal expenses through corp = loan to shareholder. Must repay within deadline or it becomes taxable income. | LOW | Dedicated account (1800). Flag when balance > $0 approaching year-end. Simple but critical — missing this causes real tax pain. |
| **CLI interface** | Developer-friendly means CLI-first. Batch imports, quick queries, automation scripts. | LOW | Wraps core library. Commands: import, categorize, review, report, export. Scriptable for cron jobs. |

### Differentiators (Competitive Advantage)

Features that make this system worth building instead of using Wave/QuickBooks. These align with the core value of developer-friendliness and Quebec-specific automation.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **MCP server for Claude interaction** | The killer feature. Claude can query balances, add transactions, generate reports, answer questions about your books — conversationally. No commercial tool offers this. | MEDIUM | Expose ledger operations as MCP tools. Read-only mode for safety. hledger-mcp proves this works. Must scope carefully — Claude should query and propose, not write directly without approval. |
| **Receipt/invoice parsing (PDF/image)** | Eliminates manual receipt data entry. AI extracts vendor, date, amount, tax breakdown from photos/PDFs. | MEDIUM | LLM-based extraction (Claude vision or dedicated OCR). TaxHacker proves the pattern. Must validate extracted amounts against bank transactions for reconciliation. |
| **Invoice generation** | Generate professional invoices for Procom and training clients. Auto-calculate GST/QST. Track payment status. | LOW | Simple template engine. Procom likely has their own format requirements. Training gigs need standard invoices. Link invoices to receivables. |
| **OPEX vs CAPEX auto-classification** | $500 threshold detection. Items above $500 flagged as potential capital assets, assigned CCA class. Saves time and prevents common errors. | LOW | Rule: amount > $500 + category match -> flag for CAPEX review. Suggest CCA class based on description (computer -> Class 50, furniture -> Class 8). |
| **Web dashboard** | Visual transaction review, report viewing, invoice management. Not everyone wants CLI all the time. | HIGH | Full web app (likely separate phase). Transaction list with filters, approval workflow, charts, report viewer. Could be simple — hledger-web or Fava prove a basic web UI adds huge value. |
| **Correction feedback loop** | When you fix an AI miscategorization, the correction improves future accuracy. Rules auto-generate from repeated corrections. | MEDIUM | Store corrections. After N identical corrections, propose a new rule. RAG index for LLM context. Community reports this is what pushes accuracy from 85% to 95%. |
| **Filing deadline alerts** | Calendar of obligations (T4/RL-1 by Feb 28, GST/QST by Mar 31, T2/CO-17 by Jun 30, etc.) with reminders. | LOW | Static calendar already documented. Generate alerts based on fiscal year-end. Low effort, high value — missing a deadline means penalties. |
| **Payroll remittance tracking** | Track what has been remitted to CRA/Revenu Quebec vs what is owed. Flag upcoming remittance deadlines. | LOW | Sum liability accounts (2200-2270) vs payments. Regular remitter = 15th of following month. Simple balance check. |
| **Year-end checklist automation** | Guided workflow: verify shareholder loan, confirm CCA schedule, reconcile GST/QST, generate all CPA deliverables. | LOW | Scripted checklist that queries the ledger and flags issues. "Shareholder loan balance: $X — must repay by [date]." Huge time saver at year-end. |
| **Self-hosted / local data** | Financial data never leaves your machine. No cloud dependency. No subscription. Full control. | LOW | Architecture decision, not a feature to build. But it is a differentiator vs QuickBooks/Xero/Wave. Impacts technology choices. |
| **Git-versioned data** | Every change to the ledger is a git commit. Full history, rollback, diff. Audit trail built into the tool developers already use. | LOW | Plain-text ledger formats (HLedger/Beancount) naturally support this. Just init a git repo and auto-commit on changes. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems. Deliberately excluded.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Tax return filing (T2, CO-17, T4, RL-1)** | "Automate everything end-to-end" | Tax filing has legal liability. CRA/RQ XML schemas change annually. T2/CO-17 complexity is enormous. One error = penalties + interest. CPA handles this for ~$1,500-2,000/year — worth every dollar. | Produce a clean CPA export package. Let CPA file. |
| **Tax advice / salary vs dividend optimization** | "Tell me the optimal split" | Legal and professional liability. Tax optimization depends on personal circumstances (RRSP room, spousal income, TFSA, future plans). AI recommending tax strategy is dangerous. | Surface the data (total salary, total dividends, corp tax rate, personal marginal rate). Let CPA advise. |
| **Real-time bank sync (Plaid/Flinks)** | "Auto-import like QuickBooks" | Plaid/Flinks require ongoing subscription, break frequently, create security surface area (OAuth tokens to bank). For 1 bank with ~20-30 transactions/month, CSV import weekly is sufficient. | CSV/OFX import on demand. Takes 2 minutes. |
| **Multi-currency support** | "What if I get USD clients?" | Adds FX tracking, unrealized gains/losses, and reporting complexity. Not needed when all clients pay CAD through Procom. | Defer entirely. If USD revenue appears, add as a future milestone. |
| **Mobile app** | "Review transactions on my phone" | Separate codebase, app store deployment, responsive web is sufficient for occasional mobile use. Solo consultant is at a desk 95% of the time. | Web dashboard with responsive design. |
| **AI-generated financial reports / commentary** | "Claude writes my financial summary" | LLMs hallucinate numbers. Financial reports must be mathematically exact. AI commentary on reports could mislead. | Let the ledger engine generate exact reports. Use MCP to let Claude explain them conversationally, but never generate the numbers themselves. |
| **Multi-user / role-based access** | "What about my CPA login?" | Solo system. Adding auth, permissions, and user management is pure overhead. CPA gets a PDF/CSV export, not a login. | Export package for CPA. Read-only MCP mode if CPA wants to query. |
| **Automated payment / bank transfer** | "Pay invoices automatically" | Initiating bank transactions programmatically requires bank API access, creates massive security risk, and is unnecessary for ~5 payments/month. | Track what is owed. Pay manually via RBC online banking. Mark as paid in system. |
| **Inventory / project costing** | "Track cost per project" | IT consulting is a service business with near-zero COGS. Project costing adds complexity for no value when you have 1-2 clients. | Tag transactions by client if needed. Simple. |
| **PSB risk assessment tool** | "Tell me if I'm at PSB risk" | Legal determination. False reassurance is dangerous. Factors are qualitative (degree of control, ownership of tools, chance of profit/loss). | Surface PSB-relevant indicators (single client %, own tools Y/N, number of clients) without making a determination. Flag for CPA discussion. |

## Feature Dependencies

```
[Transaction Import (CSV/OFX)]
    +--requires--> [Chart of Accounts]
    +--requires--> [Double-Entry Ledger]

[Rule-Based Categorization]
    +--requires--> [Transaction Import]
    +--requires--> [Chart of Accounts]

[LLM Categorization]
    +--requires--> [Rule-Based Categorization] (runs after rules, on uncategorized remainder)
    +--requires--> [Chart of Accounts] (constrains LLM output)

[Confidence Scoring + Human Review]
    +--requires--> [LLM Categorization]

[Correction Feedback Loop]
    +--requires--> [Confidence Scoring + Human Review]
    +--enhances--> [Rule-Based Categorization] (auto-generates new rules)
    +--enhances--> [LLM Categorization] (RAG context)

[GST/QST Tracking]
    +--requires--> [Double-Entry Ledger]
    +--requires--> [Chart of Accounts] (tax accounts)

[CCA Tracking]
    +--requires--> [Double-Entry Ledger]
    +--requires--> [OPEX vs CAPEX Classification]

[OPEX vs CAPEX Classification]
    +--requires--> [Rule-Based Categorization]

[Payroll Engine]
    +--requires--> [Double-Entry Ledger]
    +--independent-- (can be built in parallel with import pipeline)

[Invoice Generation]
    +--requires--> [Double-Entry Ledger] (records receivable)
    +--requires--> [GST/QST Tracking] (calculates taxes on invoice)

[Receipt Parsing]
    +--requires--> [Double-Entry Ledger] (stores extracted data)
    +--enhances--> [Transaction Import] (reconciles parsed receipts against bank transactions)

[CPA Export]
    +--requires--> [Double-Entry Ledger]
    +--requires--> [GST/QST Tracking]
    +--requires--> [CCA Tracking]
    +--requires--> [Payroll Engine]
    +--requires--> [Shareholder Loan Tracking]

[MCP Server]
    +--requires--> [Double-Entry Ledger]
    +--enhances--> [all query/report features]

[Web Dashboard]
    +--requires--> [Double-Entry Ledger]
    +--requires--> [Confidence Scoring + Human Review]
    +--enhances--> [all features via visual interface]

[CLI]
    +--requires--> [Double-Entry Ledger]
    +--wraps--> [all core operations]
```

### Dependency Notes

- **Everything requires the Double-Entry Ledger:** This is the foundation. Pick the ledger engine first (HLedger/Beancount/PyLedger), then build everything on top.
- **Categorization is a pipeline:** Import -> Rules -> LLM -> Confidence Score -> Human Review -> Feedback. Each stage depends on the previous one.
- **CPA Export requires all financial features:** It is the capstone. Cannot produce a complete package without GST/QST, CCA, payroll, and shareholder loan data all flowing into the ledger.
- **MCP Server and Web Dashboard are presentation layers:** They expose the same underlying data through different interfaces. Build the core first, then add interfaces.
- **Payroll is independent of the import pipeline:** It can be built in parallel. Owner inputs salary amount, system calculates deductions and generates journal entries.
- **Receipt Parsing enhances but does not block:** The system works without it (manual receipt tracking). It makes life easier by auto-extracting data from documents.

## MVP Definition

### Launch With (v1)

Minimum viable product: import bank transactions, categorize them, produce a trial balance for the CPA.

- [ ] **Double-entry ledger engine** — the accounting foundation; all other features build on this
- [ ] **Chart of accounts (Quebec IT consultant)** — load the already-designed 1000-6999 COA
- [ ] **RBC CSV/OFX import** — get bank transactions into the system
- [ ] **Rule-based categorization** — deterministic rules handle the predictable 60-70%
- [ ] **LLM categorization with confidence scoring** — Claude API handles ambiguous transactions
- [ ] **Human review workflow (CLI)** — approve/reject/recategorize flagged items
- [ ] **GST/QST tracking** — separate ITC/ITR calculation on all categorized expenses
- [ ] **Basic reporting** — trial balance, P&L, balance sheet in CSV format
- [ ] **CLI interface** — import, categorize, review, report commands
- [ ] **Shareholder loan tracking** — dedicated account with year-end balance alert

### Add After Validation (v1.x)

Features to add once the core import-categorize-report pipeline is working and trusted.

- [ ] **Payroll calculation engine** — triggered when you start paying yourself salary (may be needed for first payroll run, could be v1 if timing demands it)
- [ ] **CCA tracking** — needed before first year-end if capital assets were acquired
- [ ] **OPEX vs CAPEX auto-classification** — enhances categorization pipeline
- [ ] **CPA export package** — full structured export (trial balance + all schedules)
- [ ] **Correction feedback loop** — auto-generate rules from repeated corrections
- [ ] **MCP server** — let Claude query and interact with the ledger conversationally
- [ ] **Invoice generation** — generate invoices for training clients (Procom may not need invoices from you)
- [ ] **Filing deadline alerts** — static calendar with reminders

### Future Consideration (v2+)

Features to defer until the core system is proven and stable.

- [ ] **Web dashboard** — full web UI for visual transaction review and reporting (HIGH complexity, defer until CLI workflow is solid)
- [ ] **Receipt/invoice parsing** — PDF/image AI extraction (valuable but not blocking; keep physical receipts organized meanwhile)
- [ ] **Payroll remittance tracking** — track amounts owed vs remitted to CRA/RQ
- [ ] **Year-end checklist automation** — guided workflow for annual close
- [ ] **Git-versioned data** — auto-commit ledger changes (trivial if using plain-text format, but formalize later)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Double-entry ledger engine | HIGH | HIGH | P1 |
| Chart of accounts | HIGH | LOW | P1 |
| Transaction import (CSV/OFX) | HIGH | LOW | P1 |
| Rule-based categorization | HIGH | MEDIUM | P1 |
| LLM categorization + confidence | HIGH | MEDIUM | P1 |
| Human review workflow | HIGH | MEDIUM | P1 |
| GST/QST tracking | HIGH | MEDIUM | P1 |
| Shareholder loan tracking | HIGH | LOW | P1 |
| CLI interface | HIGH | LOW | P1 |
| Basic reporting | HIGH | MEDIUM | P1 |
| Payroll calculation engine | HIGH | HIGH | P1/P2 (timing-dependent) |
| CCA tracking | HIGH | MEDIUM | P2 |
| CPA export package | HIGH | MEDIUM | P2 |
| OPEX vs CAPEX classification | MEDIUM | LOW | P2 |
| Correction feedback loop | MEDIUM | MEDIUM | P2 |
| MCP server | HIGH | MEDIUM | P2 |
| Invoice generation | MEDIUM | LOW | P2 |
| Filing deadline alerts | MEDIUM | LOW | P2 |
| Web dashboard | MEDIUM | HIGH | P3 |
| Receipt/invoice parsing | MEDIUM | MEDIUM | P3 |
| Payroll remittance tracking | LOW | LOW | P3 |
| Year-end checklist | MEDIUM | LOW | P3 |

**Priority key:**
- P1: Must have for launch — system is broken without it
- P2: Should have — add as soon as core is stable, before first year-end
- P3: Nice to have — defer to v2+

## Competitor Feature Analysis

| Feature | QuickBooks Online | Wave | Akaunting (self-hosted) | HLedger + MCP | Our Approach |
|---------|-------------------|------|------------------------|---------------|--------------|
| Transaction import | Auto-sync (Plaid) | Auto-sync | CSV import | CSV import | CSV/OFX import (RBC) |
| Categorization | Rule-based + ML | Rule-based | Manual | Manual + MCP/AI | Rules-first + LLM + human review |
| GST/QST | Yes (Canadian ed.) | Yes (basic) | Plugin | Manual journal entries | Automated ITC/ITR calculation |
| Payroll (Quebec) | Add-on ($) | No | No | No | Built-in with all QC formulas |
| CCA tracking | No (manual) | No | No | No | Automated by class with half-year rule |
| Receipt parsing | Yes (mobile app) | Yes (basic) | Plugin | No | LLM-based extraction |
| Invoice generation | Yes | Yes | Yes | No | Template-based with GST/QST |
| MCP / AI assistant | No | No | No | Yes (hledger-mcp) | Native MCP server |
| Self-hosted | No (cloud only) | No (cloud only) | Yes | Yes | Yes (local data) |
| CPA export | Yes (accountant access) | Yes (accountant access) | Export | CLI reports | Structured package |
| Quebec-specific | Partial | Minimal | No | No | Full (payroll, taxes, CCA, SBD awareness) |
| Developer-friendly | No | No | Somewhat | Yes (CLI, plain text) | Yes (CLI, MCP, scriptable, git-versioned) |

**Key insight:** No existing tool combines Quebec-specific payroll/tax automation with MCP/AI integration and self-hosted local data. QuickBooks comes closest on features but fails on self-hosting, developer UX, and deep Quebec payroll automation. HLedger + MCP is the closest in spirit but requires building all Quebec specifics from scratch.

## Sources

- Beancount community: 95% automated categorization with hybrid rules + LLM approach ([beancount.io forum](https://beancount.io/forum/t/finally-got-95-automated-expense-categorization-working-with-beancount-llms/93))
- FinNLP 2025 research: LLMs produce 8.33% fully correct entries without careful prompting ([beancount.io docs](https://beancount.io/docs/Solutions/using-llms-to-automate-and-enhance-bookkeeping-with-beancount))
- hledger-mcp: production MCP server for accounting ([GitHub - iiAtlas/hledger-mcp](https://github.com/iiAtlas/hledger-mcp))
- TaxHacker: self-hosted AI receipt parsing ([GitHub - vas3k/TaxHacker](https://github.com/vas3k/TaxHacker))
- PyLedger: Python accounting with built-in MCP ([GitHub - dickhfchan/pyledger](https://github.com/dickhfchan/pyledger))
- hledger features: ([hledger.org/features](https://hledger.org/features.html))
- Plain text accounting overview: ([plaintextaccounting.org](https://plaintextaccounting.org/))
- AI in Accounting 2026: ([DualEntry guide](https://www.dualentry.com/blog/ai-in-accounting))
- Existing project research: `/Users/philippebeliveau/Desktop/Notebook/comptabilite/research/AI Accounting Automation Research.md`
- Quebec tax reference: `/Users/philippebeliveau/Desktop/Notebook/comptabilite/research/quebec_incorporation_reference.md`

---
*Feature research for: AI-assisted accounting, solo Quebec IT consultant (CCPC)*
*Researched: 2026-02-18*
