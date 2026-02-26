---
phase: 06-design-system-foundation
plan: 01
subsystem: ui
tags: [chart.js, animation, accessibility, reduced-motion, spa, fava-extension]

# Dependency graph
requires:
  - phase: 04-mcp-server-and-web-dashboard
    provides: ThemeQCExtension.js base with CSS design system and tooltip infrastructure
provides:
  - Chart.js 4.4.8 lazy CDN loader with Promise caching
  - Chart registry with destroy-on-navigate lifecycle
  - renderCharts() engine discovering [data-chart] containers
  - animateKPIs() engine discovering [data-value] elements
  - Page entry animation (fade + translateY) on SPA navigation
  - prefers-reduced-motion CSS and JS guards
  - Chart container CSS (.cqc-chart-container)
affects: [07-dashboard-homepage, 08-table-and-extension-polish]

# Tech tracking
tech-stack:
  added: [chart.js-4.4.8-umd, intl-numberformat-fr-ca, requestanimationframe]
  patterns: [lazy-cdn-loading, chart-registry-lifecycle, reduced-motion-first]

key-files:
  created: []
  modified:
    - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js

key-decisions:
  - "Custom rAF animation instead of CountUp.js -- zero dependencies, 30 lines, fr-CA formatting built-in"
  - "Chart.js loaded via CDN UMD (not bundled) to avoid build tooling complexity in Fava extension context"
  - "Chart registry uses Map with string keys for O(1) lookup and explicit destroy lifecycle"

patterns-established:
  - "Lazy CDN loading: check window global, cache Promise, inject script once"
  - "SPA cleanup: destroy all tracked instances at top of onPageLoad before creating new ones"
  - "Accessibility-first: check prefersReducedMotion() before any animation, CSS @media guard as safety net"
  - "Fire-and-forget async: renderCharts() called without await in onPageLoad -- non-blocking by design"

requirements-completed: [DSYS-02, DSYS-03]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 6 Plan 01: Chart.js Infrastructure and Animation Engine Summary

**Chart.js 4.4.8 lazy CDN loader with registry lifecycle, KPI count-up animation via rAF + Intl.NumberFormat, page entry CSS animation, and prefers-reduced-motion guards across JS and CSS**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T01:01:38Z
- **Completed:** 2026-02-26T01:03:26Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Chart.js loads lazily from CDN only when a page contains [data-chart] containers, with Promise caching for single-load guarantee
- Chart registry (Map) tracks all Chart.js instances and destroys them at the top of every onPageLoad() to prevent canvas reuse errors on SPA navigation
- renderCharts() discovers containers, parses JSON data attributes, and creates Chart.js instances with Quebec-palette theme defaults (line, bar, doughnut)
- animateKPIs() animates numeric values from 0 to target using requestAnimationFrame with ease-out cubic easing and Intl.NumberFormat fr-CA formatting
- Page entry animation (fade + translateY 6px over 200ms) fires on every SPA navigation
- All animations suppressed when user has prefers-reduced-motion enabled (both CSS @media guard and JS checks)

## Task Commits

Each task was committed atomically:

1. **Task 1: Chart.js CDN loader, chart registry, and renderCharts() engine** - `7bdf45e` (feat)
2. **Task 2: KPI count-up animation, page entry animation, and reduced-motion guards** - `d7af87e` (feat)

## Files Created/Modified
- `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` - Added 5 functions (loadChartJs, destroyAllCharts, getChartThemeOptions, renderCharts, animateKPIs, prefersReducedMotion, animatePageEntry), chart registry Map, CSS keyframes, chart container styles, reduced-motion media query

## Decisions Made
- Used custom requestAnimationFrame loop instead of CountUp.js library -- zero extra dependencies, native Intl.NumberFormat for fr-CA locale
- Chart.js loaded via CDN UMD rather than npm bundle -- Fava extensions have no build step, CDN is the pragmatic choice
- Chart registry uses Map with string keys (container.id or canvas.id or index fallback) for explicit lifecycle management

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Python `import compteqc` verification could not run due to Python version mismatch (3.10.8 vs >=3.12 required) -- pre-existing environment issue, not a regression from these changes. JS file verification via grep confirmed all functions and patterns present.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Chart.js infrastructure ready for Phase 7 (Dashboard Homepage) to create actual charts with [data-chart] containers
- KPI animation ready for Phase 7/8 to add data-value attributes to KPI tiles
- Page entry animation active immediately on all SPA navigations
- Reduced-motion guards protect all future animations added to the design system

---
*Phase: 06-design-system-foundation*
*Completed: 2026-02-25*
