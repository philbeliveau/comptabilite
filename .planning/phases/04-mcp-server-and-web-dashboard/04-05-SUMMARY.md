---
phase: 04-mcp-server-and-web-dashboard
plan: 05
subsystem: ui
tags: [fava, extensions, drag-drop, deadlines, upload, jinja2]

requires:
  - phase: 04-mcp-server-and-web-dashboard
    provides: "FavaExtensionBase pattern from existing 6 extensions"
provides:
  - "EcheancesExtension with pluggable Phase 5 alert interface"
  - "RecusExtension with drag-and-drop upload POST endpoint"
  - "8 total fava-extension directives in main.beancount"
affects: [05-reporting-cpa-export-and-document-management]

tech-stack:
  added: []
  patterns: [try-import graceful degradation for Phase 5 modules, extension_endpoint POST for file upload]

key-files:
  created:
    - src/compteqc/fava_ext/echeances/__init__.py
    - src/compteqc/fava_ext/echeances/templates/EcheancesExtension.html
    - src/compteqc/fava_ext/recus/__init__.py
    - src/compteqc/fava_ext/recus/templates/RecusExtension.html
    - tests/test_fava_gap_closure.py
  modified:
    - ledger/main.beancount
    - tests/test_fava_quebec.py

key-decisions:
  - "Try-import pattern for Phase 5 modules (compteqc.echeances.calendrier, compteqc.documents.upload)"
  - "RecusExtension saves files to documents/ dir even without Phase 5 extraction"
  - "4 urgency CSS classes: alerte-critique (red), alerte-urgent (orange), alerte-normal (yellow), alerte-info (blue)"

patterns-established:
  - "Try-import graceful degradation: extensions check for Phase 5 modules at load time via ImportError"
  - "extension_endpoint POST for file operations: RecusExtension upload pattern"

requirements-completed: []

duration: 5min
completed: 2026-02-19
---

# Phase 4 Plan 5: Deadline Alerts and Receipt Upload Fava Extensions Summary

**Two gap-closure Fava extensions: EcheancesExtension with color-coded deadline alert banners and RecusExtension with drag-and-drop file upload zone, both using try-import pattern for Phase 5 pluggability**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T14:23:44Z
- **Completed:** 2026-02-19T14:28:50Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- EcheancesExtension renders 4 urgency-level alert banners (critique/urgent/normal/info) when Phase 5 exists, informative placeholder when not
- RecusExtension provides drag-and-drop upload zone with JavaScript event handlers and POST endpoint saving to documents/
- Both extensions registered in main.beancount (8 total), all 68 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create EcheancesExtension and RecusExtension with templates** - `5e869a1` (feat)
2. **Task 2: Register extensions in main.beancount and add tests** - `b9823e9` (test)

## Files Created/Modified
- `src/compteqc/fava_ext/echeances/__init__.py` - EcheancesExtension with Phase 5 try-import and couleur_urgence helper
- `src/compteqc/fava_ext/echeances/templates/EcheancesExtension.html` - Alert banner dashboard with 4 CSS urgency levels
- `src/compteqc/fava_ext/recus/__init__.py` - RecusExtension with upload POST endpoint and recent documents list
- `src/compteqc/fava_ext/recus/templates/RecusExtension.html` - Drag-and-drop upload zone with JavaScript
- `tests/test_fava_gap_closure.py` - 12 tests for gap-closure extensions
- `ledger/main.beancount` - 8 fava-extension directives
- `tests/test_fava_quebec.py` - Updated for 8 extensions

## Decisions Made
- Try-import pattern for Phase 5 modules (compteqc.echeances.calendrier, compteqc.documents.upload)
- RecusExtension saves files to documents/ dir even without Phase 5 extraction module
- 4 urgency CSS classes: alerte-critique (red), alerte-urgent (orange), alerte-normal (yellow), alerte-info (blue)

## Deviations from Plan

None - plan executed exactly as written.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 5 can plug in by implementing compteqc.echeances.calendrier (calculer_echeances, obtenir_alertes) and compteqc.documents.upload (upload_document) + compteqc.documents.extraction (extraire_donnees)
- All 8 Fava extensions ready for Phase 5 integration

---
*Phase: 04-mcp-server-and-web-dashboard*
*Completed: 2026-02-19*
