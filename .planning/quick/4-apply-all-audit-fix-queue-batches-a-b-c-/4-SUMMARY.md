---
phase: quick-4
plan: 01
subsystem: categorisation, payroll, ledger
tags: [beancount, categorisation, payroll-tax, shareholder-loan, balance-sheet]

requires:
  - phase: quick-1
    provides: audit report identifying 21 issues across 4 severity levels
  - phase: quick-3
    provides: CRITICAL and HIGH ledger data corrections applied
provides:
  - 5 code bug fixes (balance sheet, payroll tax, auto-approve threshold)
  - 5 categorization pipeline hardening fixes
  - Shareholder loan carry-forward behavior
  - Opening balance placeholder for bank account
  - 1 missing transaction restored, duplicate CC payment confirmed absent
  - Human review items documented for D2-D6
affects: [categorisation, payroll, bilan, pret-actionnaire, tax-rules]

tech-stack:
  added: []
  patterns:
    - "-v for credit-normal accounts instead of abs() in balance sheet"
    - "Strict > 0.95 threshold for auto-approve (not >=)"
    - "Prior-year carry-forward for shareholder loan tracking"

key-files:
  created:
    - .planning/quick/4-apply-all-audit-fix-queue-batches-a-b-c-/HUMAN-REVIEW-NEEDED.md
  modified:
    - src/compteqc/mcp/tools/ledger.py
    - src/compteqc/quebec/paie/impot_federal.py
    - src/compteqc/quebec/paie/impot_quebec.py
    - src/compteqc/quebec/rates.py
    - src/compteqc/mcp/tools/categorisation.py
    - rules/categorisation.yaml
    - src/compteqc/categorisation/feedback.py
    - src/compteqc/categorisation/llm.py
    - src/compteqc/cli/importer.py
    - rules/taxes.yaml
    - src/compteqc/quebec/pret_actionnaire/suivi.py
    - ledger/main.beancount
    - ledger/comptes.beancount
    - ledger/pending.beancount
    - tests/test_feedback.py
    - tests/test_reviser.py
    - tests/test_pret_actionnaire.py

key-decisions:
  - "Balance sheet uses -v instead of abs() for equity/passif accounts to correctly handle contra-equity (Dividendes-Declares)"
  - "Auto-approve threshold harmonized to strict > 0.95 across pipeline.py and MCP tool"
  - "Auto-rule generation threshold raised from 2 to 5 to prevent false positive rule creation"
  - "Shareholder loan tracker includes all prior-year transactions for accurate carry-forward balance"
  - "Opening balance deferred as TODO comment (user must look up actual bank balance)"
  - "D7 duplicate CC payment (CSV line 110) already absent from ledger -- no action needed"

patterns-established:
  - "Negative flip (-v) for credit-normal accounts in balance sheet calculations"
  - "CORRECTIONS CONNUES section in LLM prompt for audit-learned overrides"

requirements-completed: []

duration: 22min
completed: 2026-02-20
---

# Quick Task 4: Apply All Audit Fix Queue Batches A-D Summary

**Fixed 15 audit items: balance sheet abs() bug, payroll tax constants, categorization pipeline hardening, shareholder loan carry-forward, and 6 US SaaS vendor tax rules**

## Performance

- **Duration:** 22 min
- **Started:** 2026-02-20T02:55:49Z
- **Completed:** 2026-02-20T03:18:47Z
- **Tasks:** 3
- **Files modified:** 17

## Accomplishments

- Fixed CRITICAL balance sheet equation bug (abs() on equity accounts broke contra-equity like Dividendes-Declares, off by $219)
- Hardened categorization pipeline: Mollo Cafe corrected to personal expense, auto-rule threshold raised to 5, LLM prompt contradictions removed
- Updated payroll tax calculations: Canada Employment Amount ($1,501), Quebec deduction pour travailleur ($1,450), federal K constants
- Added 6 US SaaS vendors to TPS-only tax rules (Anthropic, OpenRouter, Perplexity, Railway, Spotify, Microsoft)
- Shareholder loan now tracks carry-forward from prior years
- Documented 5 items requiring human judgment (D2-D6)

## Task Commits

1. **Task 1: Batch A code bugs** - `9552aec` (fix)
2. **Task 2: Batch B categorization pipeline** - `1d0b7a0` (fix)
3. **Task 3: Batch C+D shareholder loan, opening balance, data** - `d2398ad` (fix)

## Files Created/Modified

- `src/compteqc/mcp/tools/ledger.py` - Fixed abs() to -v for equity/passif in bilan
- `src/compteqc/quebec/paie/impot_federal.py` - Updated Canada Employment Amount to $1,501
- `src/compteqc/quebec/paie/impot_quebec.py` - Added deduction pour travailleur ($1,450 max)
- `src/compteqc/quebec/rates.py` - Corrected federal K constants for brackets 3-5
- `src/compteqc/mcp/tools/categorisation.py` - Harmonized auto-approve to strict > 0.95
- `rules/categorisation.yaml` - Fixed Mollo Cafe to Passifs:Pret-Actionnaire
- `src/compteqc/categorisation/feedback.py` - Raised SEUIL_AUTO_REGLE from 2 to 5
- `src/compteqc/categorisation/llm.py` - Removed contradictory DEPOT DE PAIE guidance, added CORRECTIONS CONNUES
- `src/compteqc/cli/importer.py` - ML training includes Passifs:Pret-Actionnaire
- `rules/taxes.yaml` - Added 6 US SaaS vendors to tps_seulement
- `src/compteqc/quebec/pret_actionnaire/suivi.py` - Changed year filter from != to > for carry-forward
- `ledger/main.beancount` - Added opening balance TODO placeholder
- `ledger/comptes.beancount` - Added Capital:Ouverture account
- `ledger/pending.beancount` - Added missing CSV line 22 transaction
- `tests/test_feedback.py` - Updated tests for threshold = 5
- `tests/test_reviser.py` - Updated auto-rule test for threshold = 5
- `tests/test_pret_actionnaire.py` - Updated year filter test for carry-forward behavior
- `.planning/quick/4-apply-all-audit-fix-queue-batches-a-b-c-/HUMAN-REVIEW-NEEDED.md` - D2-D6 items for user

## Decisions Made

- Used `-v` instead of `abs()` for credit-normal accounts (passifs and capitaux) to correctly handle contra-equity accounts like Dividendes-Declares
- Harmonized auto-approve threshold to strict `> 0.95` (not `>=`) for safety margin
- Raised auto-rule generation threshold from 2 to 5 to prevent false positive rules from insufficient data
- Changed shareholder loan year filter from `!= annee` to `> annee` to include prior-year carry-forward
- Opening balance left as commented-out TODO (user must provide actual bank statement balance)
- D7 (duplicate CC payment at CSV line 110) confirmed already absent from ledger -- gap exists between lines 109 and 111

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test updates for threshold change**
- **Found during:** Task 2 (feedback threshold change)
- **Issue:** 4 tests in test_feedback.py and 1 test in test_reviser.py expected SEUIL_AUTO_REGLE = 2
- **Fix:** Updated tests to use 5 corrections before expecting rule generation
- **Files modified:** tests/test_feedback.py, tests/test_reviser.py
- **Committed in:** 1d0b7a0 (Task 2 commit)

**2. [Rule 1 - Bug] Shareholder loan test expected old filter behavior**
- **Found during:** Task 3 (year filter change)
- **Issue:** test_obtenir_etat_pret_filters_by_fiscal_year expected prior-year exclusion
- **Fix:** Renamed test, updated assertions for carry-forward, added new test for future-year exclusion
- **Files modified:** tests/test_pret_actionnaire.py
- **Committed in:** d2398ad (Task 3 commit)

**3. [Rule 1 - Bug] Capital:Ouverture missing GIFI metadata**
- **Found during:** Task 3 (opening balance)
- **Issue:** New account failed test_chaque_compte_a_metadata_gifi validation
- **Fix:** Added gifi: "3849" to Capital:Ouverture account definition
- **Files modified:** ledger/comptes.beancount
- **Committed in:** d2398ad (Task 3 commit)

**4. [Rule 1 - Bug] Unused pad directive caused bean-check failure**
- **Found during:** Task 3 (opening balance)
- **Issue:** pad with balance 0 CAD triggers "Unused Pad entry" error in beancount
- **Fix:** Changed to commented-out example with TODO instructions
- **Files modified:** ledger/main.beancount
- **Committed in:** d2398ad (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (4 bugs)
**Impact on plan:** All auto-fixes necessary for test correctness and ledger validation. No scope creep.

## Issues Encountered

- 14 pre-existing test failures confirmed across test suite (all present before any changes). These are unrelated to audit fix queue items.
- D7 (duplicate CC payment at CSV line 110) was already absent from the ledger -- confirmed by gap between CSV lines 109 and 111 in pending.beancount. No action was needed.

## Items Deferred

- **C1 (Tax decomposition):** OUT OF SCOPE per plan -- requires larger architecture change to wire tax modules into import pipeline
- **D2-D6:** Require human judgment -- documented in HUMAN-REVIEW-NEEDED.md

## User Setup Required

None - no external service configuration required.

## Next Steps

- User should review HUMAN-REVIEW-NEEDED.md and provide answers for D2-D6 items
- User should look up actual bank balance for Nov 5, 2025 and update the opening balance in ledger/main.beancount
- C1 (tax decomposition into import pipeline) should be planned as a separate task

---
*Quick Task: 4-apply-all-audit-fix-queue-batches-a-b-c-*
*Completed: 2026-02-20*
