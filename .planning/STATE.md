# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** Every dollar that flows through the corporation is correctly categorized, traceable to source documents, and ready for CPA review -- without manual data entry.
**Current focus:** Phase 2: Quebec Domain Logic

## Current Position

Phase: 2 of 5 (Quebec Domain Logic)
Plan: 4 of 4 in current phase
Status: Executing Phase 2
Last activity: 2026-02-19 -- Completed 02-04 (CCA/DPA and Shareholder Loan)

Progress: [██████░░░░] 60%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 5.5 min
- Total execution time: 0.55 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 3 | 19 min | 6.3 min |
| 02 | 3 | 14 min | 4.7 min |

**Recent Trend:**
- Last 5 plans: 01-02 (6 min), 01-03 (8 min), 02-01 (5 min), 02-03 (4 min), 02-04 (5 min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Research]: Beancount v3 selected as ledger engine (Python-native plugins, Decimal math, 10-year track record)
- [Research]: Tiered categorization pipeline: rules first (60-70%), ML second (20-25%), LLM last (5-10%)
- [Research]: FastAPI + HTMX + Fava for web layer; no JS build toolchain
- [01-01]: Beancount v3 name_* options must be in every included file, not just main.beancount
- [01-01]: Float rejection via Pydantic BeforeValidator (strict mode blocks string date coercion)
- [01-02]: Credit card sign convention: CSV positive = purchase, maps to negative on carte account posting
- [01-02]: Dedup strategy: FITID for OFX, date+montant+narration[:20] for CSV
- [01-02]: Empty categorisation rules file -- build rules incrementally from real imports
- [01-02]: appliquer_categorisation creates new Transaction instances (immutable transformation)
- [01-03]: Monthly beancount files require name_* options (same Beancount v3 requirement as comptes.beancount)
- [01-03]: Reports compute balances directly from Transaction postings instead of beanquery
- [01-03]: Bilan includes resultat net under capitaux propres for accounting equation verification
- [02-01]: Tuple instead of list for tax brackets in TauxAnnuels (immutability)
- [02-01]: Per-deduction-type liability sub-accounts for trivial YTD queries
- [02-01]: QPP supp1 has NO exemption deduction (differs from QPP base)
- [02-03]: Plug value rounding: avant_taxes = total - tps - tvq ensures exact sum
- [02-03]: Pydantic BaseModel for YAML tax rule validation (not raw dicts)
- [02-03]: Reconciliation flags TPS-only transactions for human review rather than auto-correcting

### Pending Todos

None yet.

### Blockers/Concerns

- smart_importer + Beancount v3 compatibility unverified (affects Phase 3)
- CPA export format preference unknown (consult CPA before Phase 5)
- Quebec Law 25 compliance for sending financial data to cloud LLM (affects Phase 3)

## Session Continuity

Last session: 2026-02-19
Stopped at: Completed 02-03-PLAN.md
Resume file: .planning/phases/02-quebec-domain-logic/02-03-SUMMARY.md
