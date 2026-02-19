---
phase: 02-quebec-domain-logic
plan: 01
subsystem: payroll
tags: [qpp, rqap, ei, fss, cnesst, decimal, tdd, rates, ytd]

# Dependency graph
requires:
  - phase: 01-ledger-foundation-and-import-pipeline
    provides: "Beancount ledger with chart of accounts, Python project structure"
provides:
  - "Centralized 2026 rate config (obtenir_taux) with all payroll/tax rates as frozen Decimal dataclasses"
  - "Pure-function contribution calculators for QPP 3-tier, RQAP, EI, FSS, CNESST, normes travail"
  - "YTD tracking module deriving cumuls from ledger sub-accounts"
  - "Per-deduction-type liability sub-accounts in chart of accounts"
affects: [02-02-payroll-engine, 02-03-gst-qst, 05-cpa-reports]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Pure Decimal calculation functions with ROUND_HALF_UP", "Frozen dataclass rate registry indexed by year", "YTD derived from ledger sub-accounts (single source of truth)"]

key-files:
  created:
    - src/compteqc/quebec/__init__.py
    - src/compteqc/quebec/rates.py
    - src/compteqc/quebec/paie/__init__.py
    - src/compteqc/quebec/paie/cotisations.py
    - src/compteqc/quebec/paie/ytd.py
    - tests/test_rates.py
    - tests/test_cotisations.py
  modified:
    - ledger/comptes.beancount

key-decisions:
  - "Tuple instead of list for tax brackets in TauxAnnuels (immutability)"
  - "Separate liability sub-accounts per deduction type for trivial YTD queries"
  - "QPP supp1 has NO exemption deduction (differs from base)"

patterns-established:
  - "All rates via obtenir_taux(annee) -- never hardcoded in calculation functions"
  - "All money math uses Decimal with _arrondir() helper (ROUND_HALF_UP to 0.01)"
  - "Contribution functions: (salaire_brut_periode, cumul_annuel, taux, nb_periodes) -> Decimal"

requirements-completed: [PAY-02, PAY-03, PAY-04, PAY-05, PAY-06, PAY-07, PAY-10, PAY-12]

# Metrics
duration: 5min
completed: 2026-02-19
---

# Phase 02 Plan 01: Rates and Contributions Summary

**All 2026 payroll rates as frozen Decimal dataclasses with pure-function contribution calculators for QPP 3-tier, RQAP, EI, FSS, CNESST, and normes du travail, plus YTD tracking from ledger sub-accounts**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T12:49:47Z
- **Completed:** 2026-02-19T12:54:32Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Centralized 2026 rate config with all payroll rates, tax brackets, and thresholds as frozen Decimal dataclasses
- Pure-function calculators for all 7 contribution types with YTD cap enforcement
- Per-deduction-type liability sub-accounts in chart of accounts for clean YTD queries
- 75 tests total (43 rates + 32 contributions) all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create rates.py and update chart of accounts** - `64aeba8` (feat)
2. **Task 2 RED: Failing tests for contribution calculators** - `2f59ea2` (test)
3. **Task 2 GREEN: Implement contribution calculators and YTD tracking** - `002a7c5` (feat)

**Plan metadata:** [pending] (docs: complete plan)

_Note: Task 2 followed TDD with separate RED and GREEN commits._

## Files Created/Modified
- `src/compteqc/quebec/rates.py` - All 2026 rates as frozen dataclasses with obtenir_taux()
- `src/compteqc/quebec/paie/cotisations.py` - Pure Decimal calculators for all 7 contribution types
- `src/compteqc/quebec/paie/ytd.py` - YTD cumul derivation from ledger sub-accounts
- `ledger/comptes.beancount` - Added 13 new liability sub-accounts for payroll tracking
- `tests/test_rates.py` - 43 tests for rate values, immutability, and no-float guarantee
- `tests/test_cotisations.py` - 32 tests for all contribution calculations with cap scenarios

## Decisions Made
- Used tuple instead of list for tax brackets in TauxAnnuels dataclass (ensures immutability)
- Expanded chart of accounts with 13 sub-accounts (7 retenues + 6 cotisations employeur) per research recommendation #3
- QPP supplementaire 1 does NOT deduct exemption (differs from QPP base -- this is correct per Retraite Quebec)

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- rates.py and cotisations.py are ready for the payroll engine (Plan 02-02) to orchestrate
- YTD tracking ready to derive cumuls from real payroll transactions
- Chart of accounts validated with bean-check

---
*Phase: 02-quebec-domain-logic*
*Completed: 2026-02-19*
