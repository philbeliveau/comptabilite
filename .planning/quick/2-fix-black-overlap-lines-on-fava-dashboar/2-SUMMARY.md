---
phase: quick-2
plan: 01
subsystem: ui
tags: [css, tooltip, fava, browser-paint, visibility]

# Dependency graph
requires:
  - phase: 06-01
    provides: Tooltip CSS in ThemeQCExtension.js THEME_CSS template literal
provides:
  - Tooltip pseudo-elements that do not paint when invisible (visibility: hidden + opacity: 0 combo)
affects: [06-02, fava-dashboard-ux]

# Tech tracking
tech-stack:
  added: []
  patterns: [visibility+opacity dual toggle for CSS pseudo-element paint prevention]

key-files:
  created: []
  modified:
    - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js

key-decisions:
  - "Use visibility: hidden alongside opacity: 0 to prevent browser painting near-black tooltip background as artifact"
  - "Transition both opacity and visibility (200ms ease each) so fade-in/out stays smooth"

patterns-established:
  - "CSS pseudo-element artifact prevention: always pair opacity: 0 with visibility: hidden when element has a dark background color, to stop browser from painting the background layer during compositing"

requirements-completed:
  - QUICK-2-fix-tooltip-artifacts

# Metrics
duration: 3min
completed: 2026-02-19
---

# Quick Task 2: Fix Black Overlap Lines on Fava Dashboard Summary

**CSS tooltip paint artifact eliminated by pairing opacity: 0 with visibility: hidden on [data-tooltip]::after pseudo-elements**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-19T00:00:00Z
- **Completed:** 2026-02-19T00:03:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `visibility: hidden` to `[data-tooltip]::after` block, preventing the browser from painting the near-black (#0A1628) tooltip background at opacity: 0
- Extended the `transition` property to cover both `opacity 200ms ease` and `visibility 200ms ease`, maintaining smooth fade behavior
- Added `visibility: visible` to the hover/focus-within/focus block so tooltips appear correctly on interaction

## Task Commits

Each task was committed atomically:

1. **Task 1: Add visibility: hidden to tooltip CSS to prevent paint artifacts** - `fbb46b2` (fix)

## Files Created/Modified

- `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` - Three-line change within THEME_CSS tooltip block: added visibility: hidden, updated transition, added visibility: visible in hover rule

## Decisions Made

- `visibility: hidden` is the correct fix because browsers may still composite (paint) pseudo-element backgrounds even at `opacity: 0` during CSS transitions with z-index stacking, especially on Chromium. `visibility: hidden` instructs the layout engine to skip painting entirely.
- Transitioning `visibility` alongside `opacity` is necessary: without it, the element would appear and disappear abruptly on the last frame rather than fading.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Tooltip artifact is fixed. Table rows and amounts in Fava dashboard should display cleanly with no dark horizontal bands.
- No further action needed for this quick fix.

---
*Phase: quick-2*
*Completed: 2026-02-19*
