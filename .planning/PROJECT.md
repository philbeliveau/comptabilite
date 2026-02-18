# CompteQC — AI-Assisted Accounting for a Solo IT Consultant in Quebec

## What This Is

A developer-friendly accounting system for a freshly incorporated Quebec IT consulting corporation (~$230K revenue). It automates bookkeeping — transaction import, AI-assisted categorization, payroll calculations, GST/QST tracking, CCA schedules — and produces a clean, comprehensive year-end package so the CPA can review everything in under one hour. The system is built for a solo operator who values correctness and auditability over magic.

## Core Value

Every dollar that flows through the corporation is correctly categorized, traceable to source documents, and ready for CPA review — without manual data entry.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] Import and normalize RBC bank/credit card transactions (CSV/OFX)
- [ ] AI-assisted transaction categorization with confidence scoring
- [ ] Human review/approval workflow for proposed entries
- [ ] Quebec-appropriate chart of accounts (IT consultant, CCPC)
- [ ] Double-entry ledger with full audit trail
- [ ] Payroll calculation engine (QPP, RQAP, EI, FSS, CNESST, labour standards)
- [ ] GST (5%) / QST (9.975%) tracking with ITC/ITR calculations
- [ ] CCA tracking by asset class with half-year rule
- [ ] Shareholder loan account tracking with year-end alerts
- [ ] Invoice generation for consulting clients (Procom, training gigs)
- [ ] Receipt/invoice ingestion (PDF, images) with AI extraction
- [ ] Web dashboard for transaction review, invoice management, report viewing
- [ ] MCP server for Claude interaction (categorize, query, report)
- [ ] CPA export package: trial balance, P&L, balance sheet, payroll/CCA/GST schedules
- [ ] CLI for batch imports, automation, and power use

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Tax return filing (T2, CO-17, T1/TP-1, T4/RL-1, GST/QST returns) — CPA handles these
- Tax advice or legal opinions — system prepares data, never recommends
- Enact product revenue tracking — pre-revenue, defer to future milestone
- Multi-entity support — single corp for now, architecture should allow later
- Stripe/Wise/PayPal integrations — not in use yet, add when needed
- Mobile app — web-first
- Real-time bank syncing (Plaid, etc.) — CSV/OFX import is sufficient for v1

## Context

**Business profile:**
- Solo incorporated IT consultant (CCPC) in Quebec, Canada
- Fresh incorporation (2025–2026), December 31 fiscal year-end
- ~$230K annual revenue from consulting
- Main client engagement through Procom (intermediary agency), plus occasional training gigs
- One bank: RBC (business account + eventually business credit card)
- Enact (software product) exists but is pre-revenue

**CPA relationship:**
- CPA retained for: T2/CO-17 corporate returns, T1/TP-1 personal returns, salary vs dividends strategy, tax planning
- Goal is to eliminate CPA bookkeeping/cleanup time, not replace the CPA
- CPA export must be clean enough for <1 hour review

**Existing research:**
- Detailed Quebec payroll formulas documented (QPP base+additional, RQAP, EI Quebec rate, FSS, CNESST, labour standards) with 2026 rates
- Complete chart of accounts template for Quebec IT consultant already designed (accounts 1000–6999)
- Tax brackets (Quebec + federal), CCA classes, GST/QST rules, shareholder loan rules all documented
- Filing deadlines calendar mapped out
- AI accounting automation landscape researched (Beancount+LLM, HLedger+MCP, PyLedger, TaxHacker)
- Community consensus: rules-first + LLM for edge cases + human review achieves 95% accuracy

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

- **Tech stack**: Developer-friendly, open-source core. Python or TypeScript preferred. Must support MCP protocol for Claude integration.
- **Data sovereignty**: All financial data stays local (no cloud accounting SaaS). Self-hosted.
- **Auditability**: Every entry must trace back to source document. AI reasoning must be visible.
- **Correctness over speed**: Wrong entries that look right are worse than slow entries that are transparent.
- **Architecture undecided**: Ledger engine (HLedger vs PyLedger vs Beancount vs custom) to be determined during research phase. Must support: double-entry, multi-currency (CAD primary), reporting, MCP integration.
- **Solo operator**: No team workflow needed. Single user with CPA as read-only consumer.

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep CPA for tax filing | T2/CO-17 complexity, legal risk, PSB awareness | — Pending |
| December 31 fiscal year-end | Standard calendar year | — Pending |
| RBC-only for v1 | Only bank in use, simplifies import development | — Pending |
| Defer Enact revenue tracking | Pre-revenue, avoid premature complexity | — Pending |
| Self-hosted, local data | Financial data sensitivity, privacy | — Pending |
| Rules-first + LLM for edge cases | Community-proven approach, 95% accuracy vs 8% pure-LLM | — Pending |
| Ledger engine TBD | Research phase will compare HLedger, PyLedger, Beancount | — Pending |

---
*Last updated: 2026-02-18 after initialization*
