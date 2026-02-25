---
phase: 04-mcp-server-and-web-dashboard
plan: 04
subsystem: ui
tags: [fava, jinja2, payroll, gst-qst, cca, shareholder-loan, quebec]

# Dependency graph
requires:
  - phase: 04-01
    provides: "MCP server with Quebec domain bridge functions"
  - phase: 04-03
    provides: "Fava extension pattern (ApprobationExtension) and base template"
  - phase: 02-01
    provides: "Payroll YTD cumuls (calculer_cumuls_depuis_transactions)"
  - phase: 02-03
    provides: "GST/QST sommaire par periode (generer_sommaires_annuels)"
  - phase: 02-04
    provides: "CCA pools (construire_pools), shareholder loan (obtenir_etat_pret, calculer_dates_alerte)"
provides:
  - "PaieQCExtension: YTD payroll dashboard with 7 contributions + income tax"
  - "TaxesQCExtension: GST/QST tracker by filing period with net remittance"
  - "DpaQCExtension: CCA schedule for classes 8, 10, 12, 50, 54"
  - "PretActionnaireExtension: Shareholder loan with s.15(2) countdown alerts"
  - "ExportCPAExtension: Stub for Phase 5 CPA export"
affects: [05-cpa-export]

# Tech tracking
tech-stack:
  added: []
  patterns: [fava-extension-with-domain-bridge, jinja2-table-dashboard, color-coded-alert-levels]

key-files:
  created:
    - src/compteqc/fava_ext/paie_qc/__init__.py
    - src/compteqc/fava_ext/paie_qc/templates/PaieQCExtension.html
    - src/compteqc/fava_ext/taxes_qc/__init__.py
    - src/compteqc/fava_ext/taxes_qc/templates/TaxesQCExtension.html
    - src/compteqc/fava_ext/dpa_qc/__init__.py
    - src/compteqc/fava_ext/dpa_qc/templates/DpaQCExtension.html
    - src/compteqc/fava_ext/pret_actionnaire/__init__.py
    - src/compteqc/fava_ext/pret_actionnaire/templates/PretActionnaireExtension.html
    - src/compteqc/fava_ext/export_cpa/__init__.py
    - src/compteqc/fava_ext/export_cpa/templates/ExportCPAExtension.html
    - tests/test_fava_quebec.py
  modified:
    - ledger/main.beancount

key-decisions:
  - "niveau_alerte_s152 helper as module-level function for testability (same pattern as 04-03)"
  - "CCA extension loads actifs.yaml from ledger directory by default, falls back to empty registre"
  - "TaxesQCExtension supports config string for frequence (annuel/trimestriel)"

patterns-established:
  - "Fava Quebec extension pattern: FavaExtensionBase + after_load_file + domain module bridge + Jinja2 template"
  - "Color-coded alert levels: normal (green), attention (yellow), urgent (orange), critique (red)"

requirements-completed: [WEB-03, WEB-04]

# Metrics
duration: 5min
completed: 2026-02-19
---

# Phase 04 Plan 04: Quebec Fava Dashboards Summary

**Five Fava extensions for Quebec-specific dashboards: payroll YTD with max tracking, GST/QST by filing period, CCA schedule by class, shareholder loan with s.15(2) countdown alerts, and CPA export stub**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T14:05:25Z
- **Completed:** 2026-02-19T14:10:19Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments
- PaieQCExtension shows all 7 contributions (RRQ/QPP base, QPP supp1, RQAP, AE, FSS, CNESST, Normes du travail) plus federal and Quebec income tax, with max-reached indicators
- TaxesQCExtension shows GST/QST by filing period (annual/quarterly) with CTI, RTI, and net remittance
- DpaQCExtension shows CCA schedule for all 5 classes (8, 10, 12, 50, 54) with FNACC opening/closing
- PretActionnaireExtension shows shareholder loan status with s.15(2) deadline countdown and 4-level color-coded alert
- ExportCPAExtension stub ready for Phase 5 with planned export list
- All 6 extensions registered in main.beancount, 32 tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Payroll and GST/QST Fava extensions** - `7a89a6e` (feat)
2. **Task 2: CCA, shareholder loan, and CPA export stub** - `53a7699` (feat)
3. **Task 3: Test all Quebec Fava extensions** - `7fb012f` (test)

## Files Created/Modified
- `src/compteqc/fava_ext/paie_qc/__init__.py` - PaieQCExtension with YTD payroll data from calculer_cumuls_depuis_transactions
- `src/compteqc/fava_ext/paie_qc/templates/PaieQCExtension.html` - Payroll dashboard with cotisations table, impot table, and summary
- `src/compteqc/fava_ext/taxes_qc/__init__.py` - TaxesQCExtension with GST/QST filing period summary
- `src/compteqc/fava_ext/taxes_qc/templates/TaxesQCExtension.html` - Tax tracker with period table and annual totals
- `src/compteqc/fava_ext/dpa_qc/__init__.py` - DpaQCExtension with CCA schedule by class
- `src/compteqc/fava_ext/dpa_qc/templates/DpaQCExtension.html` - CCA table with FNACC, acquisitions, dispositions, DPA
- `src/compteqc/fava_ext/pret_actionnaire/__init__.py` - PretActionnaireExtension with s.15(2) countdown
- `src/compteqc/fava_ext/pret_actionnaire/templates/PretActionnaireExtension.html` - Loan status with alert box and movement history
- `src/compteqc/fava_ext/export_cpa/__init__.py` - ExportCPAExtension stub
- `src/compteqc/fava_ext/export_cpa/templates/ExportCPAExtension.html` - Phase 5 placeholder with planned exports
- `tests/test_fava_quebec.py` - 32 tests for all extensions
- `ledger/main.beancount` - Added 5 fava-extension directives (6 total)

## Decisions Made
- niveau_alerte_s152 as module-level helper for testability (consistent with 04-03 pattern)
- CCA extension loads actifs.yaml from ledger directory by default, falls back to empty registre if not found
- TaxesQCExtension accepts config string for declaration frequency (annuel/trimestriel)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 4 complete: all MCP tools and Fava dashboards built
- ExportCPAExtension stub ready for Phase 5 implementation
- All Quebec-specific modules (payroll, taxes, CCA, shareholder loan) have both MCP and web interfaces

## Self-Check: PASSED

All 11 files verified present. All 3 commit hashes verified in git log.

---
*Phase: 04-mcp-server-and-web-dashboard*
*Completed: 2026-02-19*
