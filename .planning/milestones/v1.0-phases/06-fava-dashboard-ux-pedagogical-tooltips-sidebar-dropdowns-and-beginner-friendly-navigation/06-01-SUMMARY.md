---
phase: 06-fava-dashboard-ux-pedagogical-tooltips-sidebar-dropdowns-and-beginner-friendly-navigation
plan: 01
subsystem: ui
tags: [fava, javascript, css, sidebar, tooltips, french-ux, pedagogical]

# Dependency graph
requires:
  - phase: 04-mcp-server-and-web-dashboard
    provides: Fava extension system, ThemeQCExtension.js base with CSS design system
  - phase: 05-reporting-cpa-export-and-document-management
    provides: Extension pages (ExportCPA, Echeances, Recus) referenced in REPORT_INTROS
provides:
  - Collapsible sidebar with French section headers using details/summary elements
  - REPORT_INTROS dictionary with 12 French pedagogical entries for all report pages
  - injectReportHeader() function for prepending explanation blocks to article elements
  - Tooltip CSS foundation with [data-tooltip]::after selector (hover + focus-within)
  - Brand injection wired into onPageLoad()
affects: [06-02-PLAN tooltip attachment logic]

# Tech tracking
tech-stack:
  added: []
  patterns: [content-based DOM classification for sidebar grouping, idempotent DOM injection with dataset guards]

key-files:
  modified:
    - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js

key-decisions:
  - "Content-based sidebar grouping: match link text patterns instead of positional index for robustness against beancount config ordering"
  - "SIDEBAR_GROUPS array with catch-all Extensions Quebec group for unmatched ul elements"
  - "Idempotent guards: aside.dataset.cqcGrouped for sidebar, existing element removal for report headers"
  - "12 REPORT_INTROS entries covering 4 native Fava reports and 8 custom extensions, all in beginner-level French"

patterns-established:
  - "DOM reorganization pattern: classify existing elements by content, wrap in semantic containers"
  - "Report intro injection: URL path matching against dictionary keys with idempotent cleanup"

requirements-completed: [UX-01, UX-02, UX-04, UX-05]

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 06 Plan 01: Collapsible Sidebar, Report Headers, and Tooltip CSS Summary

**Collapsible sidebar with 4 French section groups, 12 pedagogical report header blocks, and tooltip CSS foundation in ThemeQCExtension.js**

## Performance

- **Duration:** 2 min (code pre-existed from prior session, verification and documentation)
- **Started:** 2026-02-19T17:47:16Z
- **Completed:** 2026-02-19T17:49:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Collapsible sidebar with 4 French groups (Rapports financiers, Donnees et documents, Outils, Extensions Quebec) using details/summary elements
- 12 pedagogical report header blocks in beginner-level French covering all native Fava and custom extension reports
- Tooltip CSS foundation with [data-tooltip]::after supporting hover, focus-within, and focus states
- Brand injection (injectBrand) wired into onPageLoad alongside reorganizeSidebar and injectReportHeader

## Task Commits

Both tasks were committed together (code implemented atomically in a single session):

1. **Task 1: Collapsible sidebar with French section headers and brand injection** - `4ffbaaf` (feat)
2. **Task 2: Report header blocks and tooltip CSS foundation** - `4ffbaaf` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` - Added reorganizeSidebar(), SIDEBAR_GROUPS, REPORT_INTROS (12 entries), injectReportHeader(), tooltip CSS, sidebar group CSS, report intro CSS; wired all into onPageLoad()

## Decisions Made
- Content-based sidebar grouping: match link text patterns (e.g., "Income Statement", "Balance Sheet") instead of positional index for robustness against beancount config ordering changes
- SIDEBAR_GROUPS as ordered array with catch-all "Extensions Quebec" group for any ul elements not matching defined patterns
- Idempotent guards using aside.dataset.cqcGrouped (persists across SPA navigation) and existing element removal for report headers (re-injects on each page load)
- All 12 REPORT_INTROS entries written in beginner-level French with no unexplained jargon, including qui (who uses it) and fonction (source module) fields

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Tooltip CSS foundation is ready for Plan 02 (attachTooltips logic with 40+ dictionary entries)
- All sidebar groups and report headers are live and functional
- Brand injection is active in onPageLoad

---
*Phase: 06-fava-dashboard-ux-pedagogical-tooltips-sidebar-dropdowns-and-beginner-friendly-navigation*
*Completed: 2026-02-19*

## Self-Check: PASSED
- [x] src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js exists
- [x] Commit 4ffbaaf exists in git history
