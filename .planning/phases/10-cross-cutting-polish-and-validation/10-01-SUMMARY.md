---
phase: 10-cross-cutting-polish-and-validation
plan: 01
subsystem: ui
tags: [css, design-tokens, typography, accessibility, cross-browser, firefox, focus-visible]

requires:
  - phase: 06-design-system-foundation
    provides: "Type scale tokens (--cqc-font-*) and weight tokens (--cqc-weight-*)"
provides:
  - "Consistent typography token usage across all CSS rules"
  - "Firefox scrollbar support in sidebar"
  - "Keyboard focus-visible indicators on all interactive elements"
  - "Backdrop-filter Safari/Firefox fallbacks"
affects: [10-cross-cutting-polish-and-validation]

tech-stack:
  added: []
  patterns: ["CSS custom property tokens for all font-size/font-weight values", "focus-visible for keyboard-only focus rings", "scrollbar-width for Firefox thin scrollbar"]

key-files:
  created: []
  modified:
    - "src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js"

key-decisions:
  - "Map hardcoded font-size values to nearest --cqc-font-* token (within 2px tolerance)"
  - "Replace non-standard font-weight: 450 with var(--cqc-weight-normal) (400)"
  - "Keep Fava override font-size values hardcoded with intentional comments"
  - "Use :focus-visible (not :focus) to avoid showing focus rings on mouse clicks"
  - "Document hardcoded alert hex colors as intentional a11y contrast choices"

patterns-established:
  - "All font-size values use var(--cqc-font-*) tokens or are documented as intentional exceptions"
  - "All font-weight values use var(--cqc-weight-*) tokens"
  - "Hardcoded colors on alert backgrounds include a11y justification comments"

requirements-completed: [QUALITY-GATE]

duration: 3min
completed: 2026-02-25
---

# Phase 10 Plan 01: Typography Token Migration and Cross-Browser CSS Summary

**Migrated all hardcoded font-size/font-weight to design system tokens, added Firefox scrollbar support, keyboard focus-visible rings, and backdrop-filter fallbacks**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T02:12:57Z
- **Completed:** 2026-02-26T02:15:55Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Migrated 37 hardcoded font-size values to var(--cqc-font-*) tokens across the entire THEME_CSS
- Normalized all font-weight values (including non-standard 450) to var(--cqc-weight-*) tokens
- Added Firefox scrollbar-width: thin and scrollbar-color for sidebar
- Added :focus-visible outlines for all interactive elements (buttons, badges, links, inputs)
- Added -webkit-backdrop-filter and solid background fallback for header search inputs
- Documented 5 hardcoded alert hex colors with a11y contrast justification comments

## Task Commits

Each task was committed atomically:

1. **Task 1: Typography token migration and font-weight normalization** - `d148fa5` (feat)
2. **Task 2: Cross-browser CSS fixes and focus-visible styles** - `b7435aa` (feat)

## Files Created/Modified
- `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` - Typography tokens, scrollbar, focus-visible, backdrop-filter fallbacks, a11y color comments

## Decisions Made
- Mapped hardcoded font-size values to nearest token using the plan's mapping rules (0.72-0.78em -> xs, 0.8-0.85em -> sm, 0.88-1em -> base, etc.)
- Left Fava override section font-sizes hardcoded with "intentional: Fava override value" comments
- Used var(--cqc-weight-normal) for 450 values (450 is non-standard, normalized to 400)
- 3em preview icon size documented as "intentional: not in type scale" (genuinely outside scale)
- Focus-visible uses var(--qc-blue) for outline color and 4px rgba shadow for enhanced visibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Typography is now fully tokenized, enabling future type scale adjustments from a single :root definition
- Cross-browser CSS gaps closed for Firefox and Safari
- Keyboard accessibility baseline established with focus-visible
- Ready for Plan 10-02

---
*Phase: 10-cross-cutting-polish-and-validation*
*Completed: 2026-02-25*
