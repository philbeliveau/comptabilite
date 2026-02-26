---
phase: 13-recurring-invoices-auto-matching
plan: 02
subsystem: reconciliation
tags: [matching, AR, AP, confidence-scoring, difflib, bank-import]

# Dependency graph
requires:
  - phase: 11-ap-foundation
    provides: "FactureFournisseur model, RegistreFournisseurs registry"
  - phase: 13-01
    provides: "Recurring invoice infrastructure (same phase)"
provides:
  - "Auto-matching engine: suggerer_rapprochement_ar(), suggerer_rapprochement_ap()"
  - "SuggestionRapprochement model with confidence scoring"
  - "calculer_similarite() string similarity helper"
  - "Import pipeline integration displaying match suggestions after bank import"
affects: [14-fava-extension-tab-mcp, reconciliation-ui]

# Tech tracking
tech-stack:
  added: [difflib.SequenceMatcher]
  patterns: [protocol-based-matching, confidence-scoring, tolerance-matching]

key-files:
  created:
    - src/compteqc/rapprochement.py
    - tests/test_rapprochement.py
  modified:
    - src/compteqc/cli/importer.py

key-decisions:
  - "Used Protocol pattern (FactureOuverte) for forward compatibility with any invoice-like object"
  - "Shared _calculer_score() and helper functions (_est_paye, _obtenir_solde) eliminate AR/AP duplication"
  - "AP matching uses real FactureFournisseur since Phase 11 already shipped (no stubs needed)"
  - "_afficher_rapprochements accepts optional registry paths for testability"
  - "Beancount-to-TransactionNormalisee conversion separated into _beancount_vers_transactions for clarity"

patterns-established:
  - "Confidence scoring: 0.7 for amount match (within $0.02) + up to 0.3 for name similarity"
  - "String similarity via SequenceMatcher with case-normalized comparison"
  - "Registry path injection pattern for testable CLI functions"

requirements-completed: [RECM-03, RECM-04]

# Metrics
duration: 5min
completed: 2026-02-26
---

# Phase 13 Plan 02: Auto-Matching Engine Summary

**Bank transaction auto-matching against AR invoices and AP bills with confidence scoring via amount tolerance and name similarity**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-26T16:05:20Z
- **Completed:** 2026-02-26T16:10:35Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- AR auto-matching detects deposits corresponding to open invoices with correct confidence scoring (0.7 for amount + up to 0.3 for name)
- AP auto-matching detects withdrawals corresponding to open vendor bills with same scoring model
- Import pipeline displays match suggestions in Rich tables after successful bank file import
- 18 tests covering AR matching, AP matching, string similarity, and integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create auto-matching engine with TDD** - `f8e458b` (feat)
2. **Task 2: Integrate auto-matching suggestions into import pipeline** - `ec8bf2d` (feat)

## Files Created/Modified
- `src/compteqc/rapprochement.py` - Auto-matching engine with AR/AP suggestion functions, confidence scoring, string similarity
- `tests/test_rapprochement.py` - 18 tests: 8 AR, 5 AP, 3 similarity, 2 integration (353 lines)
- `src/compteqc/cli/importer.py` - Added _afficher_rapprochements() and _beancount_vers_transactions() for import pipeline integration

## Decisions Made
- Used Protocol pattern (FactureOuverte) for forward compatibility, though Phase 11 already shipped
- Shared _calculer_score() helper eliminates duplication between AR and AP matching logic
- _est_paye() uses string-based status checking to support any enum type
- _obtenir_solde() prefers solde over total to handle partial payments correctly
- _afficher_rapprochements() accepts optional registry paths for testability (avoids Path mocking)
- AP matching fully functional now (Phase 11 shipped), not behind try/except ImportError

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] AP module already exists, no stubs needed**
- **Found during:** Task 1 (test fixture creation)
- **Issue:** Plan assumed Phase 11 had not shipped and prescribed BillStub dataclass. Phase 11 is complete.
- **Fix:** Used real FactureFournisseur model directly instead of creating stubs.
- **Files modified:** tests/test_rapprochement.py
- **Verification:** All AP tests pass with real model

**2. [Rule 1 - Bug] Separated beancount entry conversion from display function**
- **Found during:** Task 2 (integration testing)
- **Issue:** _afficher_rapprochements() accepting beancount entries required isinstance(entry, data.Transaction) which fails with mock objects and couples the function to beancount.
- **Fix:** Split into _beancount_vers_transactions() (conversion) and _afficher_rapprochements() (display accepting TransactionNormalisee). Added optional path parameters for registries.
- **Files modified:** src/compteqc/cli/importer.py
- **Verification:** Integration tests pass cleanly without complex mocking

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes improved code quality. No scope creep.

## Issues Encountered
None - implementation proceeded smoothly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Auto-matching engine is fully functional for both AR and AP
- Import pipeline displays suggestions automatically after bank imports
- Ready for Phase 14 (Fava extension / MCP integration) which could surface match suggestions in the UI

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 13-recurring-invoices-auto-matching*
*Completed: 2026-02-26*
