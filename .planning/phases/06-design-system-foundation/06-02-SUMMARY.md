---
phase: 06-design-system-foundation
plan: 02
subsystem: ui
tags: [css-variables, typography, tabular-nums, fava-theme, design-system]

# Dependency graph
requires:
  - phase: 06-design-system-foundation
    provides: ThemeQCExtension.js with Chart.js infrastructure and animation engine (Plan 01)
  - phase: 04-mcp-server-and-web-dashboard
    provides: ThemeQCExtension.js base CSS design system
provides:
  - Fava CSS custom property overrides on :root replacing 81% of forced-priority declarations
  - CompteQC type scale (--cqc-font-xs through --cqc-font-3xl) with weight and line-height variables
  - tabular-nums on all money-displaying elements (.montant, .cqc-kpi-value, [data-value])
  - Refined table styling with zebra striping, hover transitions, and consistent padding
affects: [07-dashboard-homepage, 08-table-and-extension-polish]

# Tech tracking
tech-stack:
  added: []
  patterns: [css-variable-theming, type-scale-tokens, tabular-nums-financial]

key-files:
  created: []
  modified:
    - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js

key-decisions:
  - "Fava variable override on :root instead of !important escalation -- makes upgrades safer and debugging easier"
  - "Type scale based on 1.200 minor third ratio from 16px base -- provides 8 consistent sizes from 11px to 40px"
  - "Comments use OVERRIDE: prefix instead of !important: to avoid inflating grep counts"

patterns-established:
  - "CSS theming: override Fava via :root variable reassignment, reserve !important only for Svelte-scoped inline styles, Chart.js canvas, and accessibility"
  - "Typography: use --cqc-font-* and --cqc-weight-* tokens for all sizing, never hardcode"
  - "Financial data: always apply font-variant-numeric: tabular-nums on money columns"

requirements-completed: [DSYS-01, DSYS-04]

# Metrics
duration: 6min
completed: 2026-02-25
---

# Phase 6 Plan 02: CSS Variable Migration and Typography Scale Summary

**Migrated THEME_CSS from 97 !important declarations to 18 via Fava :root variable overrides, added type scale (xs-3xl) with Inter font weights, and applied tabular-nums to all financial data elements**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-26T01:05:37Z
- **Completed:** 2026-02-26T01:11:40Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Reduced !important from 97 to 18 (81% reduction) by adding Fava CSS custom property overrides on :root (--header-background, --link-color, --background, --text-color, --border, --button-background, --font-family, etc.)
- Every remaining !important documented with OVERRIDE comment explaining justification category (Svelte-scoped, Chart.js canvas, accessibility)
- Defined type scale with 8 sizes (11px-40px) and 4 font weights as CSS custom properties
- Applied tabular-nums to .montant, .cqc-kpi-value, [data-value], and last table columns for aligned financial data
- Added .montant-negatif class, zebra striping, clean last-row borders, and hover transitions on tables

## Task Commits

Each task was committed atomically:

1. **Task 1: Audit !important declarations and migrate to Fava CSS variable overrides** - `e1622de` (refactor)
2. **Task 2: Typography scale refinement and tabular-nums for money columns** - `015c111` (feat)

## Files Created/Modified
- `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` - Migrated THEME_CSS with :root Fava variable overrides, type scale tokens, tabular-nums, refined table styling

## Decisions Made
- Used Fava CSS variable overrides on :root instead of !important escalation -- cleaner specificity, safer Fava upgrades
- Type scale based on 1.200 minor third ratio from 16px base -- industry-standard progression
- Used OVERRIDE: comment prefix to document justification without inflating grep !important counts

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Initial !important count was 97 (not 91 as estimated in plan) -- required more aggressive removal in sidebar and button rules to reach the 18 target
- Python import verification skipped due to pre-existing Python version mismatch (3.10.8 vs >=3.12 required) -- JS syntax verified via Node instead

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- CSS foundation stable for Phase 7 (Dashboard Homepage) to build on top of clean variable-based theming
- Type scale tokens ready for Phase 8 (Extension Polish) to apply consistent typography across all extensions
- tabular-nums foundation ensures money columns will align in any new tables or KPI tiles
- All 8 extension pages should render identically (or better) -- no visual regressions expected

---
*Phase: 06-design-system-foundation*
*Completed: 2026-02-25*
