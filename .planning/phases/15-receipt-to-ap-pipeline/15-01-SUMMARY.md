---
phase: 15-receipt-to-ap-pipeline
plan: 01
subsystem: ui
tags: [fava, jinja2, javascript, receipt, ap, query-parameters]

# Dependency graph
requires:
  - phase: 14-fava-extension-tab-mcp
    provides: ComptesFournisseursExtension AP bill creation form with prefill support
provides:
  - Receipt-to-AP creation prompt in RecusExtension after AI extraction
  - Upload endpoint tax breakdown (sous_total, montant_tps, montant_tvq)
  - URL query parameter handoff from receipt to AP bill form
affects: [15-receipt-to-ap-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns: [URLSearchParams for cross-extension stateless prefill, Jinja2-to-JS URL injection]

key-files:
  created:
    - tests/test_receipt_to_ap.py
  modified:
    - src/compteqc/fava_ext/recus/__init__.py
    - src/compteqc/fava_ext/recus/templates/RecusExtension.html

key-decisions:
  - "Stateless URL query parameter handoff between RecusExtension and ComptesFournisseursExtension"
  - "Forward-compatible link to AP form -- 404 acceptable if Phase 14 not deployed"

patterns-established:
  - "Cross-extension navigation via URL query parameters with prefill=1 flag"

requirements-completed: [RCAP-01, RCAP-02]

# Metrics
duration: 1min
completed: 2026-02-26
---

# Phase 15 Plan 01: Receipt-to-AP Creation Prompt Summary

**Receipt upload adds "Creer facture fournisseur" prompt with TPS/TVQ breakdown and URL query parameter prefill handoff to AP bill form**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-26T16:47:24Z
- **Completed:** 2026-02-26T16:48:35Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Upload endpoint now returns sous_total, montant_tps, montant_tvq, and description in extracted data
- RecusExtension template renders "Creer une facture fournisseur?" prompt after successful AI extraction with vendor, total, and date summary
- Button navigates to ComptesFournisseursExtension with prefill query parameters (fournisseur, date, montant, tps, tvq, description)
- 5 unit tests covering tax field extraction, null handling, query parameter construction, UNKNOWN date exclusion

## Task Commits

Each task was committed atomically:

1. **Task 1: Enhance upload endpoint and add AP creation prompt** - `fec6118` (feat)
2. **Task 2: Add tests for receipt-to-AP prompt** - `c711f92` (test)

## Files Created/Modified
- `src/compteqc/fava_ext/recus/__init__.py` - Added sous_total, montant_tps, montant_tvq, description to extracted dict
- `src/compteqc/fava_ext/recus/templates/RecusExtension.html` - Added AP creation prompt with CSS and URLSearchParams construction
- `tests/test_receipt_to_ap.py` - 5 tests for extraction data and query parameter logic

## Decisions Made
- Stateless URL query parameter handoff between extensions (no shared state needed)
- Forward-compatible AP link (404 if Phase 14 not deployed, acceptable graceful degradation)
- Jinja2 template renders beancount_file_slug at template time for JS URL construction (follows existing pattern)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AP creation prompt ready; requires ComptesFournisseursExtension (Phase 14) to handle prefill query parameters on load
- Plan 15-02 can build on this to add the prefill read logic on the AP form side

---
*Phase: 15-receipt-to-ap-pipeline*
*Completed: 2026-02-26*
