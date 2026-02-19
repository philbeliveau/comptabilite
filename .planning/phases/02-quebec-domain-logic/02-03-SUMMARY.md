---
phase: 02-quebec-domain-logic
plan: 03
subsystem: taxes
tags: [gst, qst, tps, tvq, decimal, pydantic, yaml, beancount]

# Dependency graph
requires:
  - phase: 01-ledger-foundation-and-import-pipeline
    provides: "Beancount ledger with tax accounts (TPS-Payee, TVQ-Payee, TPS-Percue, TVQ-Percue)"
provides:
  - "Tax extraction math (extraire_taxes, appliquer_taxes) with separate GST/QST rounding"
  - "YAML-driven tax treatment rules engine (vendor > category > default priority)"
  - "Filing period summaries (annual/quarterly) with net remittance calculation"
  - "TPS/TVQ reconciliation check for mismatched tax postings"
affects: [03-ai-categorization-and-review-workflow, 05-year-end-package-and-cpa-export]

# Tech tracking
tech-stack:
  added: []
  patterns: [plug-value-rounding, yaml-rule-engine, pydantic-config-validation]

key-files:
  created:
    - src/compteqc/quebec/taxes/__init__.py
    - src/compteqc/quebec/taxes/calcul.py
    - src/compteqc/quebec/taxes/traitement.py
    - src/compteqc/quebec/taxes/sommaire.py
    - rules/taxes.yaml
    - tests/test_taxes.py
  modified: []

key-decisions:
  - "Plug value pattern for rounding: avant_taxes = total - tps - tvq ensures exact sum"
  - "Pydantic BaseModel for YAML rule validation (not raw dicts)"
  - "Built-in default YAML for test isolation (_default_yaml=True parameter)"
  - "Reconciliation flags TPS-only transactions (e.g. AWS) for human review rather than auto-correcting"

patterns-established:
  - "Plug value rounding: TPS and TVQ rounded independently, pre-tax is the residual"
  - "YAML rule engine with vendor regex > category glob > global default priority"
  - "Filing period summary pattern: iterate entries, filter by date, sum tax account postings"

requirements-completed: [TAX-01, TAX-02, TAX-03, TAX-04, TAX-05, TAX-06]

# Metrics
duration: 4min
completed: 2026-02-19
---

# Phase 2 Plan 3: GST/QST Tax Module Summary

**GST/QST tax extraction with separate rounding, YAML-driven treatment rules (vendor/category/client), filing period summaries, and TPS/TVQ reconciliation checks**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-19T12:49:43Z
- **Completed:** 2026-02-19T12:54:29Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Tax extraction calculates GST (5%) and QST (9.975%) separately with independent rounding; plug value ensures exact total
- Treatment rules engine loads from YAML with priority chain: vendor override > category default > global default
- Revenue tax treatment supports per-client rules: Quebec (TPS+TVQ), out-of-province (TPS only), international (no tax)
- Filing period summaries show collected, ITCs/ITRs, and net remittance for annual or quarterly periods
- Reconciliation check catches transactions with mismatched TPS/TVQ postings

## Task Commits

Each task was committed atomically:

1. **Task 1: Implementer le calcul TPS/TVQ et le moteur de regles de traitement fiscal** - `62a2d99` (feat)
2. **Task 2: Implementer les sommaires de periode et la verification de concordance** - `c479031` (feat)

## Files Created/Modified
- `src/compteqc/quebec/taxes/calcul.py` - Tax extraction/application math with Decimal and ROUND_HALF_UP
- `src/compteqc/quebec/taxes/traitement.py` - Tax treatment rule engine with Pydantic models and regex matching
- `src/compteqc/quebec/taxes/sommaire.py` - Filing period summaries and TPS/TVQ reconciliation
- `src/compteqc/quebec/taxes/__init__.py` - Module exports
- `rules/taxes.yaml` - Tax treatment rules configuration (categories, vendors, clients)
- `tests/test_taxes.py` - 18 tests covering tax math, treatment rules, summaries, and reconciliation

## Decisions Made
- Plug value pattern: pre-tax amount is calculated as `total - tps - tvq` (not independently rounded), ensuring the three components always sum to the exact total. This avoids bean-check balance errors.
- Built-in default YAML for tests: `charger_regles_taxes` accepts `_default_yaml=True` to load embedded rules without requiring a file on disk, enabling isolated test fixtures.
- Reconciliation flags TPS-only transactions (like AWS out-of-province) for human review rather than auto-correcting, since TPS-only is a legitimate treatment.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ruff import sorting in calcul.py and traitement.py**
- **Found during:** Task 2 verification
- **Issue:** ruff I001 import sorting violations in both files
- **Fix:** Ran `ruff check --fix` to auto-sort imports
- **Files modified:** src/compteqc/quebec/taxes/calcul.py, src/compteqc/quebec/taxes/traitement.py
- **Verification:** `ruff check` passes with zero errors
- **Committed in:** c479031 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Cosmetic import ordering fix. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Tax module ready for integration with import pipeline (Phase 3 categorization can auto-extract taxes)
- Filing period summaries ready for CPA export package (Phase 5)
- Reconciliation check available for year-end validation

---
*Phase: 02-quebec-domain-logic*
*Completed: 2026-02-19*
