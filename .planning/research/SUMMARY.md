# Project Research Summary

**Project:** CompteQC -- AI-Assisted Accounting System
**Domain:** Financial automation / plain-text accounting for Quebec CCPC (IT consultant)
**Researched:** 2026-02-18
**Confidence:** MEDIUM-HIGH

## Executive Summary

This project is a self-hosted, AI-assisted double-entry accounting system for a solo Quebec IT consultant operating through a CCPC. The expert consensus is clear: use **Beancount v3** as the ledger engine with a **tiered categorization pipeline** (deterministic rules first, ML second, LLM last). Pure-LLM categorization achieves only 8.33% accuracy for double-entry; the hybrid rules+ML+LLM approach reaches 95%. Every serious practitioner in the plain-text accounting community follows this pattern. The system exposes ledger operations via a custom MCP server for Claude interaction, uses Fava for web-based ledger exploration, and builds a lightweight FastAPI+HTMX layer for the approval workflow and CPA export.

The recommended approach is **Beancount + custom Python orchestration**. Beancount provides 10+ years of battle-tested double-entry validation, plain-text auditability, and a Python-native plugin system that lets Quebec-specific modules (payroll, GST/QST, CCA, shareholder loan) hook directly into the ledger processing pipeline. Alternatives were evaluated and rejected: HLedger requires Haskell for plugins (impractical for tax modules), PyLedger is too young with no community, and building a custom ledger engine wastes months on solved problems. The stack is pure Python with no JS build toolchain -- HTMX handles frontend interactivity.

The critical risks are: (1) floating-point currency storage causing silent drift in tax calculations, (2) incorrect GST/QST calculation order (Quebec requires independent rounding, not combined rates), (3) LLM hallucinating account codes outside the valid chart of accounts, and (4) dual CRA/Revenu Quebec filing mismatches now that both agencies cross-match with AI. All four are preventable with correct upfront design -- but retrofitting any of them is expensive. The chart of accounts must be GIFI-mapped from day one, monetary amounts must use `Decimal` (Beancount handles this natively), and all AI categorizations must be constrained to a closed account list with mandatory human review.

## Key Findings

### Recommended Stack

Beancount v3 is the foundation: plain-text ledger files that are git-diffable, with Python plugins for validation and domain logic. The MCP Python SDK (v1.26.x) bridges Claude to the accounting system. FastAPI serves the approval dashboard and REST API. SQLite stores metadata (import batches, approval status, confidence scores) -- it is NOT the ledger. uv manages the entire Python toolchain.

**Core technologies:**
- **Beancount v3:** Double-entry ledger engine -- Python-native plugins, strict validation, 10-year track record
- **MCP Python SDK 1.26.x:** Claude integration -- official Anthropic SDK, supports tools/resources/prompts
- **FastAPI + HTMX + Jinja2:** Approval dashboard -- server-rendered, no JS build step, lightweight
- **Fava 1.30.x:** Ledger exploration UI -- production-quality charts, reports, BQL queries out of the box
- **beangulp + smart_importer:** Import pipeline -- beangulp for parsing RBC CSV/OFX, smart_importer for ML categorization
- **SQLite:** Metadata store -- approval queue, audit trail, classification logs (not the ledger)
- **uv:** Package management -- 10-100x faster than pip, handles Python versions and lockfiles
- **Typer + Rich:** CLI framework -- type-hint-driven commands with polished terminal output

### Expected Features

**Must have (table stakes):**
- Double-entry ledger with audit trail (Beancount)
- RBC CSV/OFX transaction import (beangulp)
- Quebec chart of accounts with GIFI mapping (1000-6999)
- Tiered categorization: rules (60-70%) -> ML (20-25%) -> LLM (5-10%) -> human review
- Confidence scoring with human review workflow
- GST (5%) / QST (9.975%) tracking with separate ITC/ITR
- Payroll calculation engine (QPP, RQAP, EI, FSS, CNESST, federal+Quebec tax)
- CCA tracking with half-year rule
- Shareholder loan tracking with repayment deadline alerts
- Basic reporting (trial balance, P&L, balance sheet)
- CLI interface

**Should have (differentiators):**
- MCP server for conversational Claude interaction with the ledger
- CPA export package (6 components: trial balance, GIFI financials, bank rec, shareholder loan schedule, CCA schedule, GST/QST reconciliation)
- Correction feedback loop (human corrections auto-generate rules)
- Receipt/invoice parsing via Claude Vision
- Invoice generation with GST/QST
- Filing deadline alerts
- OPEX vs CAPEX auto-classification ($500 threshold)

**Defer (v2+):**
- Full web dashboard (Fava covers ledger exploration; custom UI only for approval)
- Payroll remittance tracking
- Year-end checklist automation
- Multi-currency support
- Real-time bank sync (Plaid/Flinks)
- Tax return filing (CPA handles this)
- Mobile app

### Architecture Approach

The system follows a layered architecture: Beancount files are the single source of truth, Quebec domain modules are pure Python functions with no Beancount dependency (testable in isolation), thin Beancount plugins wrap these modules for ledger integration, and presentation layers (MCP server, Fava extensions, CLI) all consume the same core logic. A staging-then-commit pattern ensures AI-categorized transactions live in `pending.beancount` with a `#pending` tag until human-approved, preventing unchecked errors from reaching the official ledger.

**Major components:**
1. **Ingestion Layer** -- Parses RBC CSV/OFX, applies rule+ML+LLM categorization pipeline, writes to staging
2. **Beancount Core** -- Source of truth for all financial data; validates integrity, runs plugins, executes BQL queries
3. **Quebec Modules** (`src/quebec/`) -- Pure Python: payroll, GST/QST, CCA, shareholder loan calculations with centralized `rates.py`
4. **Beancount Plugins** (`src/plugins/`) -- Thin wrappers calling Quebec modules within Beancount's plugin pipeline
5. **MCP Server** (`src/mcp/`) -- Exposes tools for categorization, querying, reporting, approval workflow to Claude
6. **Fava + Extensions** -- Ledger exploration via Fava; custom extensions for approval UI and CPA export

### Critical Pitfalls

1. **Floating-point currency storage** -- Use `Decimal` everywhere (Beancount does this natively); never `float`. A Montreal business accumulated $3,400 in QST errors from rounding drift. Must be correct from Phase 1.
2. **GST/QST calculation order** -- Calculate GST and QST separately on pre-tax amount, each rounded independently per line item. `round(amount * 0.05, 2) + round(amount * 0.09975, 2)` -- never a combined `0.14975` rate. Must be correct from Phase 1.
3. **LLM hallucinating account codes** -- Constrain LLM output to a closed enumerated list of valid accounts. Every LLM categorization gets confidence scoring and human review. Pin model versions; run drift detection monthly.
4. **Dual CRA/ARQ filing mismatch** -- Both agencies now cross-match with AI. Generate GST and QST amounts from a single calculation pass, stored together at the transaction level. Automated reconciliation before filing.
5. **Shareholder loan repayment deadline** -- CRA has a specific audit initiative for s.15(2). Track every debit balance with a computed inclusion date; alert at 9, 11, and 12.5 months. Detect circular borrow/repay patterns.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation -- Ledger, COA, and Import Pipeline
**Rationale:** Everything depends on the double-entry ledger and chart of accounts. The architecture research confirms "everything requires the Double-Entry Ledger" as the universal dependency. Getting the data model right prevents the costliest pitfalls (floating-point, GST/QST calculation order, mutable entries, GIFI mapping).
**Delivers:** Working Beancount ledger with Quebec COA (GIFI-mapped), RBC CSV/OFX importer, rule-based categorization engine, basic CLI for import and query.
**Addresses:** Double-entry ledger, COA, transaction import, rule-based categorization, CLI interface
**Avoids:** Floating-point currency (Beancount uses Decimal natively), mutable ledger entries (Beancount files are append-only), GIFI mapping errors (enforce at account creation)

### Phase 2: Quebec Domain Logic
**Rationale:** Payroll, GST/QST, CCA, and shareholder loan are independent of the AI layer and can be built once the ledger exists. These are HIGH complexity, custom-build-required modules with no existing libraries. Building them early allows testing against known CRA/RQ published tables before layering AI on top.
**Delivers:** Payroll engine with all Quebec deductions, GST/QST ITC/ITR module, CCA calculator with half-year rule, shareholder loan tracker with deadline alerts.
**Uses:** Python `Decimal` math, centralized `rates.py`, pure-function architecture pattern
**Implements:** Quebec Modules component, Beancount Plugins component
**Avoids:** GST/QST calculation order errors (tested against RQ examples), CCA class misassignment (deterministic rules, not LLM), shareholder loan deadline misses (computed inclusion dates)

### Phase 3: AI Categorization Layer
**Rationale:** Requires the rule engine from Phase 1 and chart of accounts to constrain LLM output. The tiered pipeline (rules -> smart_importer -> LLM -> human review) depends on all previous components. This is where the MCP server skeleton is introduced.
**Delivers:** smart_importer ML integration, LLM categorization via MCP with confidence scoring, staging/approval workflow (`pending.beancount` with `#pending` tag), MCP server with core tools (categorize, query, approve).
**Addresses:** LLM categorization, confidence scoring, human review workflow, MCP server
**Avoids:** LLM hallucinated accounts (closed account list), direct AI writes to ledger (staging pattern), prompt injection (sanitized descriptions, structured prompts)

### Phase 4: Reporting and CPA Export
**Rationale:** CPA export is the capstone -- it requires all financial features (GST/QST, CCA, payroll, shareholder loan) to be flowing into the ledger. Cannot produce a complete package without Phase 2 data. Also includes dual-filing reconciliation checks.
**Delivers:** Full CPA export package (6 components), Fava setup with custom extensions, Quebec report views, automated GST/QST reconciliation (CRA vs ARQ alignment), period-end checklist.
**Addresses:** CPA export, basic reporting upgrade, filing deadline alerts, Fava integration
**Avoids:** Dual filing mismatch (single-pass tax calculation, automated reconciliation), GIFI export errors (Schedule 100 balance validation before export), incomplete CPA package (checklist validation)

### Phase 5: Polish, Automation, and Enhancements
**Rationale:** Convenience features that depend on all prior layers being stable. Receipt parsing, invoice generation, and the correction feedback loop add value but are not blocking.
**Delivers:** Receipt/invoice parsing (Claude Vision), invoice generation with GST/QST, correction feedback loop (auto-generate rules from repeated corrections), payroll remittance tracking, year-end checklist automation, expanded MCP tools.
**Addresses:** Receipt parsing, invoice generation, correction feedback loop, OPEX/CAPEX auto-classification

### Phase Ordering Rationale

- **Phase 1 before everything:** The ledger is the universal dependency. Every researcher independently confirmed this. Getting Decimal math, GIFI mapping, and append-only patterns right here prevents the three highest-recovery-cost pitfalls.
- **Phase 2 before Phase 3:** Quebec domain logic is deterministic and testable against published government tables. It must exist before the AI layer so the categorization pipeline can trigger tax calculations and the LLM is constrained to valid accounts.
- **Phase 3 before Phase 4:** The approval workflow must be in place before producing reports -- otherwise reports include unreviewed AI categorizations. The MCP server enables Claude to participate in the review process.
- **Phase 4 after domain logic:** CPA export requires all financial modules to be complete. This is the "capstone" phase that integrates everything.
- **Phase 5 last:** Enhancement features that improve efficiency but do not affect correctness.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Quebec Domain Logic):** Payroll calculation is HIGH complexity with 7+ deduction types, annual maximums, and Quebec-specific rates. The formulas are documented but subtle (QPP exemption amount, RQAP vs EI interaction, FSS threshold tiers). Needs `/gsd:research-phase` with CRA T4032-QC tables and RQ TP-1015.TR.
- **Phase 3 (AI Categorization):** smart_importer compatibility with Beancount v3 needs verification. The beangulp adapter pattern may require investigation. MCP server tool design (what to expose, safety boundaries) benefits from research.
- **Phase 4 (CPA Export):** The exact format CPAs expect varies. TaxCycle GIFI import format and Caseware XML need investigation. Recommend consulting the actual CPA early.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Beancount setup, beangulp importers, and rule engines are extremely well-documented with official examples and Context7 snippets.
- **Phase 5 (Polish):** Receipt parsing via Claude Vision and invoice templating are straightforward integration patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Beancount, FastAPI, MCP SDK all verified via Context7 + PyPI with active maintainers. Version compatibility confirmed. |
| Features | HIGH | Domain is specific and well-understood (solo Quebec IT consultant CCPC). Feature list derived from real-world tools and Quebec tax obligations. |
| Architecture | MEDIUM-HIGH | Beancount plugin system and Fava extension API verified via official docs. smart_importer's Beancount v3 compatibility is the main uncertainty. |
| Pitfalls | MEDIUM-HIGH | Tax/compliance pitfalls from official CRA/RQ sources (HIGH). Architecture pitfalls from practitioner reports (MEDIUM). Recovery costs are estimates. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **smart_importer + Beancount v3 compatibility:** Verify that smart_importer decorators work with beangulp importers in v3. May need an adapter. Test early in Phase 3.
- **Fava extension API stability:** Fava's `FavaExtensionBase` is not formally documented as a stable API. Extensions may break on Fava upgrades. Pin Fava version.
- **CPA export format:** The exact format the CPA prefers (TaxCycle, Caseware, plain CSV) is unknown. Consult CPA before building Phase 4.
- **Docling vs Claude Vision for receipts:** Docling is newer with heavy dependencies (torch). Claude Vision is simpler for low-volume use. Defer decision to Phase 5.
- **MCP SDK v2 breaking changes:** MCP SDK v2 is expected Q1 2026 with breaking changes. Pin `mcp>=1.25,<2` and plan migration when v2 stabilizes.
- **Quebec Law 25 compliance:** Sending financial data to cloud LLM API may violate Quebec privacy law if personal info is included. Need to establish a redaction strategy before Phase 3 LLM integration.

## Sources

### Primary (HIGH confidence)
- Beancount official docs (Context7, 1910 snippets) -- plugin system, importer protocol, ledger format
- MCP Python SDK (Context7, 330 snippets) -- server creation patterns, tool definitions
- Fava (Context7, 131 snippets) -- REST API, extension system
- CRA T4032-QC 2026 payroll tables -- QPP/EI rates, federal deduction tables
- Revenu Quebec 2026 Employer's Kit -- RQAP/FSS/CNESST rates, Quebec deduction tables
- CRA GIFI documentation (RC4088) -- financial statement mapping codes
- CRA Income Tax Folio S3-F1-C1 -- shareholder loan rules
- Modern Treasury -- integer-cents storage best practice

### Secondary (MEDIUM confidence)
- hledger-mcp (npm/GitHub) -- MCP server patterns for accounting
- Beancount smart_importer (PyPI/GitHub) -- ML categorization decorator
- Beancount community forum -- hybrid rules+LLM achieving 95% accuracy
- FinNLP 2025 research -- LLM-only 8.33% accuracy baseline
- Mackisen CPA Montreal -- GST/QST filing mistakes
- TideSpark -- GIFI code mapping guide
- hledger vs Beancount vs Ledger comparison (community forum)

### Tertiary (LOW confidence)
- Docling (PyPI) -- AI-powered document extraction; evaluate before committing
- PyLedger (GitHub) -- Python accounting with MCP; rejected but informed analysis

---
*Research completed: 2026-02-18*
*Ready for roadmap: yes*
