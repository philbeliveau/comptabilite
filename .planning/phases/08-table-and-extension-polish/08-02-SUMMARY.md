---
phase: 08-table-and-extension-polish
plan: 02
subsystem: ui
tags: [keyboard-shortcuts, confidence-bars, sidebar-badge, fava-extension, spa-cleanup]

# Dependency graph
requires:
  - phase: 08-table-and-extension-polish
    provides: "Utility CSS classes (cqc-row-focused, cqc-col-checkbox), table hover/header enhancements"
provides:
  - "Confidence bar visualization (cqc-confidence-high/medium/low with bar + percentage)"
  - "Keyboard navigation for approval queue (j/k/Space/Enter/a with AbortController cleanup)"
  - "Sidebar notification badge with async pending count fetch"
  - "JSON endpoint GET /extension/ApprobationExtension/count"
affects: [09-upload-ux-and-feedback]

# Tech tracking
tech-stack:
  added: []
  patterns: ["AbortController for SPA keyboard listener cleanup", "Fire-and-forget async sidebar badge fetch", "extension_endpoint for JSON API alongside HTML endpoints"]

key-files:
  created: []
  modified:
    - src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html
    - src/compteqc/fava_ext/approbation/__init__.py
    - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js

key-decisions:
  - "Used AbortController signal pattern for keyboard listener cleanup across SPA navigations"
  - "Confidence thresholds: high >= 0.95, medium >= 0.7, low < 0.7 (visual only, independent of Python niveau_confiance)"
  - "Sidebar badge fetches from bfileSlug-relative URL to support Fava multi-file routing"

patterns-established:
  - "AbortController cleanup: store controller at module scope, abort + recreate on each onPageLoad"
  - "JSON endpoints on Fava extensions: use @extension_endpoint with GET for lightweight data APIs"
  - "Cosmetic async features: wrap in try/catch with silent failure, never break the page"

requirements-completed: [TBLX-02, TBLX-04]

# Metrics
duration: 3min
completed: 2026-02-25
---

# Phase 8 Plan 2: Approval Queue UX Summary

**Confidence bar visualization with colored fill/percentage, keyboard shortcuts (j/k/Space/a) with AbortController cleanup, and sidebar pending-count badge fetched from new JSON endpoint**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T01:47:09Z
- **Completed:** 2026-02-26T01:50:04Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Replaced plain text confidence badges with colored bar + percentage visualization (green/amber/red)
- Added keyboard navigation (j/k rows, Space/Enter toggle, a approve) with AbortController SPA cleanup
- Added sidebar notification badge showing pending approval count, fetched async from new JSON endpoint
- High-confidence rows get green left border, low-confidence rows get amber left border
- Keyboard shortcut hint displayed below action buttons

## Task Commits

Each task was committed atomically:

1. **Task 1: Approval queue template redesign and pending count endpoint** - `37578c9` (feat)
2. **Task 2: Keyboard shortcuts, sidebar badge, and confidence bar CSS** - `dcc915e` (feat)

## Files Created/Modified
- `src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html` - Confidence bars, data-row-index, row classes, keyboard hint
- `src/compteqc/fava_ext/approbation/__init__.py` - Added pending_count JSON endpoint
- `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` - Confidence bar CSS, sidebar badge CSS/JS, keyboard handler, onPageLoad wiring

## Decisions Made
- Used AbortController signal pattern for keyboard listener cleanup -- ensures no duplicate handlers across SPA navigations
- Confidence thresholds for visual display (0.95/0.7) are independent of Python niveau_confiance thresholds (0.95/0.80) -- visual categories serve UX scanning, not business logic
- Sidebar badge fetch uses bfileSlug-relative URL derived from window.location.pathname to support Fava multi-file routing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Approval queue is now keyboard-navigable and visually scannable
- Sidebar badge provides ambient awareness of pending items across all pages
- All form mechanics preserved -- approve/reject workflows unchanged

---
*Phase: 08-table-and-extension-polish*
*Completed: 2026-02-25*
