---
phase: quick-17
plan: 01
subsystem: ui
tags: [fava-extension, jinja2, chart-js, ap-ar, wireframes, design-doc]

requires:
  - phase: quick-15
    provides: AP/AR backend design document (Sections 1-7)
provides:
  - Complete UI/UX design section (Section 8) for AP/AR Fava extension tab
  - Wireframes for page layout, tables, forms, receipt-to-AP pipeline, auto-matching
  - Updated implementation roadmap with Phase E
affects: [ap-ar-implementation, fava-extensions, dashboard, approbation, recus]

tech-stack:
  added: []
  patterns: [cqc-tab-toggle for sub-tab switching, receipt-to-AP query-param prefill, match-suggestion row in approval table]

key-files:
  created: []
  modified:
    - docs/design/accounts-payable-receivable.md

key-decisions:
  - "Inline form expansion (not modal) for invoice/bill creation -- simpler for Fava SPA context"
  - "Receipt-to-AP via URL query parameters for form pre-fill -- stateless, no server-side sessions"
  - "Phase E added as dependency on both D (tab exists) and C (matching logic exists)"

patterns-established:
  - "cqc-tab-toggle: two-button toggle for switching sub-views within a single extension tab"
  - "Receipt-to-form pipeline: extraction result -> button -> navigate with query params -> pre-filled form"
  - "Match suggestion row: collapsible info row below transaction with Lier button for AP/AR linking"

requirements-completed: [QUICK-17]

duration: 4min
completed: 2026-02-26
---

# Quick Task 17: UI/UX Design Section for AP/AR Summary

**Complete UI/UX design for AP/AR Fava extension tab with 12 subsections covering KPIs, tables, forms, receipt pipeline, auto-matching, and dashboard integration**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-26T13:57:39Z
- **Completed:** 2026-02-26T14:01:20Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added Section 8 "UI/UX Design -- Fava Extension" with 12 subsections (8.1-8.12) totaling 820 new lines
- ASCII wireframes for: full page layout, AR table, AR creation form, AP creation form, receipt-to-AP prompt, auto-matching row in approval queue
- All UI elements reference existing CQC CSS classes (cqc-kpi-row, cqc-table, cqc-badge, cqc-btn, cqc-card, cqc-chart-container)
- Updated implementation roadmap with Phase E (Receipt-to-AP Pipeline and Auto-matching UX)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Section 8 UI/UX Design to AP/AR document** - `33fd206` (feat)

## Files Created/Modified

- `docs/design/accounts-payable-receivable.md` - Added Section 8 (820 lines) with complete UI/UX design for AP/AR Fava extension tab

## Decisions Made

- Inline form expansion (not modal) for invoice/bill creation -- simpler within Fava's SPA article replacement pattern
- Receipt-to-AP pipeline uses URL query parameters for form pre-fill -- stateless approach matching existing sessionStorage pattern
- Phase E added as new roadmap phase depending on both D (tab exists) and C (matching logic exists)
- Default sub-tab is AR (most frequently checked for a consultant tracking client payments)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- AP/AR design document is now a complete implementation reference covering backend (Sections 1-7) and frontend (Section 8)
- Ready for implementation: a developer can build the Fava extension tab without ambiguity about layout, forms, interactions, or CSS patterns
- Phase A (Foundation) remains the first implementation step per the roadmap

---
*Phase: quick-17*
*Completed: 2026-02-26*
