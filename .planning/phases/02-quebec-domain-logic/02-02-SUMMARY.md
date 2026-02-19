---
phase: 02-quebec-domain-logic
plan: 02
subsystem: payroll
tags: [federal-tax, quebec-tax, t4127, tp1015fv, payroll-engine, beancount, cli, salary-offset, decimal, tdd]

# Dependency graph
requires:
  - phase: 02-quebec-domain-logic
    plan: 01
    provides: "Rates registry (obtenir_taux), contribution calculators, YTD tracking, payroll sub-accounts"
provides:
  - "Federal income tax withholding per T4127 with 16.5% Quebec abatement"
  - "Quebec income tax withholding per TP-1015.F-V with bracket structure"
  - "Complete payroll engine (calculer_paie) orchestrating all calculations"
  - "Beancount transaction generator with ~21 balanced postings"
  - "CLI command `cqc paie lancer` with dry-run and salary-offset support"
affects: [05-cpa-reports, 02-04-shareholder-loan]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Tax bracket lookup with annualized income", "K-credit system for federal/Quebec tax", "Frozen dataclass ResultatPaie for immutable payroll results", "Salary offset via Passifs:Pret-Actionnaire credit posting"]

key-files:
  created:
    - src/compteqc/quebec/paie/impot_federal.py
    - src/compteqc/quebec/paie/impot_quebec.py
    - src/compteqc/quebec/paie/moteur.py
    - src/compteqc/quebec/paie/journal.py
    - src/compteqc/cli/paie.py
    - tests/test_impot.py
    - tests/test_paie_integration.py
  modified:
    - src/compteqc/cli/app.py

key-decisions:
  - "Salary offset Pret-Actionnaire uses credit (negative) posting to balance transaction correctly"
  - "FSS estimated from annualized mass salariale based on YTD + current period"
  - "Employer QPP contributions mirror employee calc functions (symmetric caps)"

patterns-established:
  - "Tax functions: (brut_periode, nb_periodes, taux, cotisations_annuelles) -> Decimal per-period"
  - "ResultatPaie frozen dataclass with all fields for downstream consumers"
  - "CLI uses Typer sub-app registered via app.add_typer"

requirements-completed: [PAY-01, PAY-08, PAY-09, PAY-11, CLI-04]

# Metrics
duration: 7min
completed: 2026-02-19
---

# Phase 02 Plan 02: Payroll Engine and Tax Withholding Summary

**Federal and Quebec income tax withholding with T4127/TP-1015.F-V formulas, complete payroll engine, balanced Beancount journal generation, and `cqc paie lancer` CLI command with salary-offset support**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-19T12:57:50Z
- **Completed:** 2026-02-19T13:04:45Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Federal tax withholding with T4127 brackets, K1/K2Q/K4 credits, and 16.5% Quebec abatement
- Quebec tax withholding with TP-1015.F-V brackets and provincial personal/cotisation credits
- Complete payroll engine orchestrating 7 contribution types + 2 tax calculations + YTD tracking
- Beancount transaction generator producing balanced 21-posting transactions with all sub-accounts
- CLI command `cqc paie lancer <montant>` with Rich breakdown table, --dry-run, and --salary-offset
- 21 tests total (10 tax + 11 integration) all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Federal and Quebec income tax withholding (TDD)** - `350826f` (feat)
2. **Task 2: Payroll engine, journal generator, and CLI** - `22df6ac` (feat)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified
- `src/compteqc/quebec/paie/impot_federal.py` - Federal tax per T4127 with Quebec abatement
- `src/compteqc/quebec/paie/impot_quebec.py` - Quebec tax per TP-1015.F-V
- `src/compteqc/quebec/paie/moteur.py` - Payroll engine with ResultatPaie dataclass
- `src/compteqc/quebec/paie/journal.py` - Beancount transaction generator (~21 postings)
- `src/compteqc/cli/paie.py` - CLI `cqc paie lancer` command with Rich output
- `src/compteqc/cli/app.py` - Registered paie sub-app
- `tests/test_impot.py` - 10 tests for federal and Quebec tax calculations
- `tests/test_paie_integration.py` - 11 integration tests for engine and journal

## Decisions Made
- Salary offset to Pret-Actionnaire uses a credit (negative) posting to ensure transaction balances. The plan originally specified a debit, but this created a 2x imbalance.
- FSS is estimated by annualizing from (YTD + current period) mass salariale
- Employer QPP contributions use the same calculation functions as employee (symmetric caps apply)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed salary_offset transaction balancing**
- **Found during:** Task 2 (journal generator)
- **Issue:** Plan specified Dr Passifs:Pret-Actionnaire + reduced Cr Bank, creating 2x the offset imbalance
- **Fix:** Changed Pret-Actionnaire posting to credit (negative) so reduced bank Cr + Cr Pret = 0 net change
- **Files modified:** src/compteqc/quebec/paie/journal.py
- **Verification:** Transaction balance test passes (sum of all postings = 0)
- **Committed in:** 22df6ac

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for double-entry correctness. No scope creep.

## Issues Encountered

None beyond the salary_offset balancing issue documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Complete payroll pipeline ready: rates -> contributions -> taxes -> engine -> journal -> CLI
- YTD tracking from ledger enables multi-period payroll runs with cap enforcement
- Salary offset enables shareholder loan repayment via payroll (links to plan 02-04)
- TODO: Validate tax formulas against WebRAS calculator for Quebec deduction-for-workers (~$1,450)

## Self-Check: PASSED

- All 7 created files exist on disk
- Both task commits verified in git log (350826f, 22df6ac)
- 21 tests passing (10 tax + 11 integration)
- Lint clean on all payroll modules
- No float literals in any payroll module

---
*Phase: 02-quebec-domain-logic*
*Completed: 2026-02-19*
