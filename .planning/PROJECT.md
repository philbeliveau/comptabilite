# CompteQC — AI-Assisted Accounting for a Solo IT Consultant in Quebec

## What This Is

A self-hosted, AI-assisted accounting system for a Quebec IT consulting CCPC (~$230K revenue). Built on Beancount v3 with a 61-account French chart of accounts (GIFI-mapped), it automates transaction import, 3-tier AI categorization, Quebec payroll, GST/QST tracking, CCA schedules, and produces a complete year-end CPA export package. The Fava web dashboard provides beginner-friendly navigation with pedagogical French tooltips. Claude interacts via MCP server for categorization, queries, and approvals.

## Core Value

Every dollar that flows through the corporation is correctly categorized, traceable to source documents, and ready for CPA review — without manual data entry.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- Import and normalize RBC bank/credit card transactions (CSV/OFX) — v1.0
- AI-assisted transaction categorization with confidence scoring — v1.0
- Human review/approval workflow for proposed entries — v1.0
- Quebec-appropriate chart of accounts (IT consultant, CCPC) — v1.0
- Double-entry ledger with full audit trail — v1.0
- Payroll calculation engine (QPP, RQAP, EI, FSS, CNESST, labour standards) — v1.0
- GST (5%) / QST (9.975%) tracking with ITC/ITR calculations — v1.0
- CCA tracking by asset class with half-year rule — v1.0
- Shareholder loan account tracking with year-end alerts — v1.0
- Invoice generation for consulting clients (Procom, training gigs) — v1.0
- Receipt/invoice ingestion (PDF, images) with AI extraction — v1.0
- Web dashboard for transaction review, invoice management, report viewing — v1.0
- MCP server for Claude interaction (categorize, query, report) — v1.0
- CPA export package: trial balance, P&L, balance sheet, payroll/CCA/GST schedules — v1.0
- CLI for batch imports, automation, and power use — v1.0

### Active

<!-- Current scope. Building toward these. -->

(None yet — define in next milestone)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Tax return filing (T2, CO-17, T1/TP-1, T4/RL-1, GST/QST returns) — CPA handles these
- Tax advice or legal opinions — system prepares data, never recommends
- Enact product revenue tracking — pre-revenue, defer to future milestone
- Multi-entity support — single corp for now, architecture should allow later
- Stripe/Wise/PayPal integrations — not in use yet, add when needed
- Mobile app — web-first
- Real-time bank syncing (Plaid, etc.) — CSV/OFX import is sufficient
- AI-generated financial reports/commentary — LLMs hallucinate numbers; reports must be mathematically exact

## Context

**Current state (v1.0 shipped 2026-02-25):**
- 21,044 lines Python + 1,769 lines JS + 1,180 lines HTML + 2,101 lines Beancount
- Tech stack: Python 3.12, Beancount v3, Fava, FastMCP, sklearn, Anthropic API, WeasyPrint
- 85 requirements delivered across 6 phases (23 plans + 10 quick tasks) in 8 days
- System is functional end-to-end: import -> categorize -> review -> payroll -> export

**Business profile:**
- Solo incorporated IT consultant (CCPC) in Quebec, Canada
- Fresh incorporation (2025-2026), December 31 fiscal year-end
- ~$230K annual revenue from consulting
- Main client engagement through Procom (intermediary agency), plus occasional training gigs
- One bank: RBC (business account + eventually business credit card)
- Enact (software product) exists but is pre-revenue

**CPA relationship:**
- CPA retained for: T2/CO-17 corporate returns, T1/TP-1 personal returns, salary vs dividends strategy, tax planning
- Goal is to eliminate CPA bookkeeping/cleanup time, not replace the CPA
- CPA export must be clean enough for <1 hour review

**PSB risk awareness:**
- Single-client through intermediary (Procom) creates Personal Services Business risk
- System should surface PSB-relevant indicators (not advise, but flag)
- Additional clients (trainings, future gigs) help mitigate

**Quebec-specific considerations:**
- Does NOT qualify for Quebec SBD (5,500-hour rule) — combined corp tax rate is 20.5%, not 12.2%
- Must handle both federal and Quebec payroll deduction formulas
- GST + QST are separate taxes with separate ITC/ITR tracking
- Federal tax abatement of 16.5% for Quebec employees

## Constraints

- **Tech stack**: Python 3.12, Beancount v3, Fava, FastMCP. Self-hosted.
- **Data sovereignty**: All financial data stays local (no cloud accounting SaaS).
- **Auditability**: Every entry traces back to source document. AI reasoning visible in JSONL logs.
- **Correctness over speed**: Wrong entries that look right are worse than slow entries that are transparent.
- **Solo operator**: No team workflow needed. Single user with CPA as read-only consumer.

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep CPA for tax filing | T2/CO-17 complexity, legal risk, PSB awareness | Good |
| December 31 fiscal year-end | Standard calendar year | Good |
| RBC-only for v1 | Only bank in use, simplifies import development | Good |
| Defer Enact revenue tracking | Pre-revenue, avoid premature complexity | Good |
| Self-hosted, local data | Financial data sensitivity, privacy | Good |
| Beancount v3 as ledger engine | Python-native plugins, Decimal math, 10-year track record, Fava UI | Good |
| Rules-first + LLM for edge cases | Community-proven approach, 95% accuracy vs 8% pure-LLM | Good |
| FastMCP for Claude integration | Official Python MCP SDK, stdio transport, clean tool registration | Good |
| Fava as web UI | Existing ledger browser, extensible, no custom frontend needed | Good |
| sklearn SVC for ML tier | Probability-based confidence via Platt scaling, simple to train | Good |
| WeasyPrint for PDF generation | HTML/CSS to PDF, Jinja2 templates, no external services | Good |
| Per-deduction-type sub-accounts | Trivial YTD queries from ledger, no separate state tracking | Good |
| CCA '!' flag for discretionary review | CPA decides on CCA claims, not auto-posted | Good |
| FIFO repayment for s.15(2) | Per-advance deadline tracking, matches CRA interpretation | Good |

---
*Last updated: 2026-02-25 after v1.0 milestone*
