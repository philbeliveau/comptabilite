---
phase: 15-receipt-to-ap-pipeline
plan: 02
subsystem: ui
tags: [fava, approval-queue, ar-ap-matching, rapprochement, payment-linking]

# Dependency graph
requires:
  - phase: 13-recurring-invoices
    provides: rapprochement module with suggerer_rapprochement_ar/ap
  - phase: 14-fava-extension-tab-mcp
    provides: ApprobationExtension with approval queue UI
provides:
  - AR/AP match suggestion enrichment in approval queue
  - lier_apar POST endpoint for one-click payment recording
  - Match suggestion rows in approval queue HTML template
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [conditional-import-for-forward-compat, match-suggestion-row-pattern]

key-files:
  created:
    - tests/test_approval_matching.py
  modified:
    - src/compteqc/fava_ext/approbation/__init__.py
    - src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html

key-decisions:
  - "Conditional imports for rapprochement and fournisseurs modules ensure graceful degradation"
  - "Match suggestion rows inserted as sibling <tr> elements after matching transaction rows"
  - "lier_apar endpoint follows same pattern as existing approuver/rejeter endpoints"

patterns-established:
  - "Match suggestion row: cqc-match-suggestion class with blue-bordered info box"
  - "Conditional enrichment: silently skip when dependency modules unavailable"

requirements-completed: [RCAP-03, RCAP-04]

# Metrics
duration: 2min
completed: 2026-02-26
---

# Phase 15 Plan 02: AR/AP Match Suggestions in Approval Queue Summary

**Approval queue enriched with AR/AP match suggestions and one-click payment linking via lier_apar endpoint**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T16:47:26Z
- **Completed:** 2026-02-26T16:49:42Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Pending transactions automatically enriched with AR/AP match suggestions from rapprochement module
- Match suggestion rows displayed below matching transactions with invoice/bill details and confidence
- One-click "Lier comme paiement AR/AP" button records payment and updates invoice/bill status
- All enrichment gracefully degrades when dependency modules are unavailable

## Task Commits

Each task was committed atomically:

1. **Task 1: Add AR/AP match enrichment to ApprobationExtension backend** - `a770d9e` (feat)
2. **Task 2: Add match suggestion rows to ApprobationExtension HTML template** - `54c245a` (feat)
3. **Task 3: Add tests for approval queue matching and lier_apar endpoint** - `465ed99` (test)

## Files Created/Modified
- `src/compteqc/fava_ext/approbation/__init__.py` - Added _enrichir_rapprochements(), lier_apar endpoint, _lier_ar(), _lier_ap()
- `src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html` - Added match suggestion rows and CSS
- `tests/test_approval_matching.py` - 9 tests for matching logic and parameter validation

## Decisions Made
- Conditional imports for rapprochement and fournisseurs modules ensure graceful degradation when Phase 13 modules are not yet available
- Match suggestion rows inserted as sibling `<tr>` elements after matching transaction rows (not modals)
- lier_apar endpoint follows same redirect-back UX pattern as existing approuver/rejeter endpoints

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MagicMock spec for no-match test**
- **Found during:** Task 3 (tests)
- **Issue:** MagicMock without spec returned MagicMock for .solde attribute, causing TypeError in _obtenir_solde comparison
- **Fix:** Used `MagicMock(spec=[])` to ensure getattr returns None for missing attributes
- **Files modified:** tests/test_approval_matching.py
- **Verification:** All 9 tests pass
- **Committed in:** 465ed99 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test mock fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 15 plan 02 complete
- AR/AP matching integrated into approval queue
- Ready for manual verification with real data

---
*Phase: 15-receipt-to-ap-pipeline*
*Completed: 2026-02-26*
