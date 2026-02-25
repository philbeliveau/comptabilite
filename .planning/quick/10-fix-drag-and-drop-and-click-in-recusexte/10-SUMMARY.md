---
phase: quick-10
plan: 01
subsystem: ui
tags: [fava, jinja2, drag-and-drop, innerHTML, inline-events]

requires:
  - phase: 04-05
    provides: RecusExtension upload page
provides:
  - Working drag-and-drop and click-to-upload in Fava SPA context
affects: []

tech-stack:
  added: []
  patterns: [inline event attributes for Fava SPA innerHTML injection]

key-files:
  created: []
  modified:
    - src/compteqc/fava_ext/recus/templates/RecusExtension.html

key-decisions:
  - "Inline event attributes instead of script block (browsers skip script tags injected via innerHTML)"

patterns-established:
  - "Fava extension templates must use inline event attributes (onclick/ondrop/etc), never script blocks"

requirements-completed: [QUICK-10]

duration: 1min
completed: 2026-02-20
---

# Quick Task 10: Fix Drag-and-Drop and Click in RecusExtension Summary

**Replaced script block with inline event attributes to fix broken upload interactions in Fava SPA**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-20T17:22:53Z
- **Completed:** 2026-02-20T17:23:33Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Removed non-functional script block (40 lines) that browsers ignore when injected via innerHTML
- Added 5 inline event attributes: onclick, ondragover, ondragleave, ondrop, onchange
- Click-to-select, drag-and-drop with visual feedback, and auto-submit all functional

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace script block with inline event attributes** - `224dd44` (feat)

## Files Created/Modified
- `src/compteqc/fava_ext/recus/templates/RecusExtension.html` - Replaced script block with inline onclick/ondragover/ondragleave/ondrop/onchange attributes

## Decisions Made
- Inline event attributes instead of script block: Fava is a Svelte SPA that injects extension HTML via innerHTML. Browsers do not execute script tags inserted via innerHTML, so inline attributes are the correct approach.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Upload page fully functional for both click and drag-and-drop workflows
- No blockers

---
*Phase: quick-10*
*Completed: 2026-02-20*
