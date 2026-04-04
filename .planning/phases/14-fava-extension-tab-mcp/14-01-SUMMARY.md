---
phase: 14-fava-extension-tab-mcp
plan: 01
subsystem: ui
tags: [fava, jinja2, chart-js, ap, ar, aging, dashboard]

requires:
  - phase: 11-ap-foundation
    provides: "FactureFournisseur model, RegistreFournisseurs, BillStatus"
  - phase: 12-aging-ar-cli
    provides: "vieillissement module with calculer_vieillissement_ar/ap functions"
provides:
  - "ComptesFournisseursExtension Fava tab with combined AP/AR view"
  - "KPI row (AR total, AR overdue, AP total, net position)"
  - "AR/AP invoice list tables with aging colors and status badges"
  - "Chart.js aging stacked bar visualization"
  - "Dashboard Position AR/AP KPI card"
  - "expense_accounts(), client_names(), vendor_names() helpers for Plan 02"
affects: [14-02, 14-03]

tech-stack:
  added: []
  patterns: ["cqc-tab-toggle sub-tab switching pattern", "aging row color classification", "AP/AR status badge mapping"]

key-files:
  created:
    - "src/compteqc/fava_ext/comptes_fournisseurs/__init__.py"
    - "src/compteqc/fava_ext/comptes_fournisseurs/templates/ComptesFournisseursExtension.html"
  modified:
    - "ledger/main.beancount"
    - "src/compteqc/fava_ext/tableau_bord/__init__.py"
    - "src/compteqc/fava_ext/tableau_bord/templates/TableauBordExtension.html"

key-decisions:
  - "Chart.js callbacks provided as JSON placeholders (not inline JS) for data-chart pattern compatibility"
  - "Aging classification uses days past due threshold (30/60/90) with CSS class mapping"

patterns-established:
  - "cqc-tab-toggle: two-button toggle for sub-tab switching within single extension"
  - "cqc-aging-* classes: border-left color coding for aging rows (green/yellow/orange/red)"
  - "cqc-badge-* classes: status badge variants for AR and AP statuses"

requirements-completed: [FVAP-01, FVAP-02, FVAP-03, FVAP-06]

duration: 3min
completed: 2026-02-26
---

# Phase 14 Plan 01: ComptesFournisseursExtension Summary

**Combined AP/AR Fava tab with KPI row, sub-tab toggle, invoice tables with aging colors/status badges, Chart.js aging bar chart, and dashboard net position KPI**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T16:26:48Z
- **Completed:** 2026-02-26T16:29:36Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- ComptesFournisseursExtension backend with kpis(), factures_ar(), factures_ap(), aging_chart_json() methods
- Full Jinja2 template with KPI row (4 KPIs), tab toggle, AR table, AP table, Chart.js aging chart
- Status badges color-coded for all AR and AP statuses
- Dashboard homepage shows net AR/AP position KPI card
- Extension registered in main.beancount

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ComptesFournisseursExtension Python backend** - `2b8930b` (feat)
2. **Task 2: Create Jinja2 template, register extension, dashboard KPI** - `90c4fa0` (feat)

**Plan metadata:** `3def1fc` (docs: complete plan)

## Files Created/Modified
- `src/compteqc/fava_ext/comptes_fournisseurs/__init__.py` - Extension class with KPI, list, chart data methods
- `src/compteqc/fava_ext/comptes_fournisseurs/templates/ComptesFournisseursExtension.html` - Full template with KPI row, tab toggle, AR/AP tables, aging chart
- `ledger/main.beancount` - Extension registration directive
- `src/compteqc/fava_ext/tableau_bord/__init__.py` - Added _position_apar() method and position_apar KPI
- `src/compteqc/fava_ext/tableau_bord/templates/TableauBordExtension.html` - Added Position AR/AP KPI card

## Decisions Made
- Chart.js callback placeholders in JSON rather than inline JS, compatible with existing data-chart pattern from ThemeQCExtension
- Aging classification uses days past due (not days since invoice date) for consistent user mental model

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Extension backend and template complete, ready for Plan 02 (CRUD forms and endpoints)
- expense_accounts(), client_names(), vendor_names() helpers already in place for form autocomplete
- Tab toggle and table structure ready for action button integration

---
*Phase: 14-fava-extension-tab-mcp*
*Completed: 2026-02-26*
