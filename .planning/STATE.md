# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** Every dollar that flows through the corporation is correctly categorized, traceable to source documents, and ready for CPA review -- without manual data entry.
**Current focus:** Phase 3: AI Categorization and Review Workflow

## Current Position

Phase: 3 of 5 (AI Categorization and Review Workflow)
Plan: 1 of 3 in current phase
Status: In Progress
Last activity: 2026-02-19 -- Completed 03-01 (Three-Tier Categorization Pipeline)

Progress: [████████░░] 65%

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: 5.5 min
- Total execution time: 0.73 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 3 | 19 min | 6.3 min |
| 02 | 4 | 21 min | 5.3 min |
| 03 | 1 | 4 min | 4.0 min |

**Recent Trend:**
- Last 5 plans: 02-01 (5 min), 02-03 (4 min), 02-04 (5 min), 02-02 (7 min), 03-01 (4 min)
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
- [02-04]: CCA transactions use '!' flag for discretionary CPA review (not auto-posted)
- [02-04]: s.15(2) inclusion date from fiscal year-end + 1 year (not loan date + 1 year)
- [02-04]: FIFO repayment allocation for per-advance s.15(2) deadline tracking
- [02-04]: Circularity detection: 20% tolerance, 30-day window per s.15(2.6)
- [02-02]: Salary offset Pret-Actionnaire uses credit posting (not debit) for correct transaction balancing
- [02-02]: FSS estimated by annualizing from (YTD + current) mass salariale
- [03-01]: Direct sklearn pipeline instead of smart_importer.EntryPredictor (too coupled to beangulp)
- [03-01]: SVC(probability=True) for Platt scaling confidence scores
- [03-01]: ClassificateurLLM as runtime_checkable Protocol for loose coupling with 03-02
- [03-01]: CAPEX keyword-based CCA class suggestion (class 50 computers, 8 furniture, 10 vehicles, 12 software)

### Pending Todos

None yet.

### Blockers/Concerns

- smart_importer + Beancount v3 compatibility: resolved by bypassing EntryPredictor, using direct sklearn
- CPA export format preference unknown (consult CPA before Phase 5)
- Quebec Law 25 compliance for sending financial data to cloud LLM (affects Phase 3)

## Session Continuity

Last session: 2026-02-19
Stopped at: Completed 03-01-PLAN.md
Resume file: .planning/phases/03-ai-categorization-and-review-workflow/03-01-SUMMARY.md
