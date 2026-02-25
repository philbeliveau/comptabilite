---
phase: 05-reporting-cpa-export-and-document-management
plan: 05
subsystem: compliance
tags: [deadlines, payroll-remittances, calendar, alerts, cli, freezegun, rich]

# Dependency graph
requires:
  - phase: 02-quebec-domain-logic
    provides: "Payroll journal entries with Passifs:Retenues and Passifs:Cotisations-Employeur accounts"
  - phase: 02-quebec-domain-logic
    provides: "Shareholder loan tracking (pret_actionnaire/suivi.py) with EtatPret and avances_ouvertes"
provides:
  - "Filing deadline calendar derived from fiscal year-end date"
  - "Alert system with 4 urgency levels (critique/urgent/normal/info)"
  - "Payroll remittance tracking (owed vs remitted by month)"
  - "CLI subcommands: cqc echeances calendrier/remises/rappels"
  - "Shareholder loan s.15(2) deadlines unified into calendar"
affects: [fava-echeances-extension, phase-05-integration]

# Tech tracking
tech-stack:
  added: [freezegun, python-dateutil]
  patterns: [pydantic-model-echeance, rich-cli-formatting, weekday-adjustment]

key-files:
  created:
    - src/compteqc/echeances/__init__.py
    - src/compteqc/echeances/calendrier.py
    - src/compteqc/echeances/remises.py
    - tests/test_echeances.py
  modified:
    - src/compteqc/cli/app.py

key-decisions:
  - "Weekend adjustment: Saturday/Sunday deadlines pushed to Monday (standard CRA rule)"
  - "Urgency thresholds: critique <= 7d, urgent <= 14d, normal <= 30d, info <= 90d"
  - "CLI footer shows only alerts within 30 days (per discretion recommendation)"
  - "Payroll remittance assumes regular remitter (15th of following month)"

patterns-established:
  - "TypeEcheance enum for all filing deadline types"
  - "obtenir_alertes() with freezegun-testable date injection"
  - "formater_rappels_cli() returns Rich markup or None"

requirements-completed: [AUTO-01, AUTO-03]

# Metrics
duration: 4min
completed: 2026-02-19
---

# Phase 05 Plan 05: Filing Deadline Calendar Summary

**Fiscal deadline calendar with alert urgency levels, payroll remittance tracking, and CLI integration covering T2/CO-17/T4/TPS-TVQ/s.15(2) deadlines**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-19T14:46:00Z
- **Completed:** 2026-02-19T14:50:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Filing deadline calculator deriving all dates from fiscal year-end (not hardcoded to Dec 31)
- Weekend adjustment pushing Saturday/Sunday deadlines to Monday
- Alert system with 4 urgency levels and configurable alert windows per deadline type
- Shareholder loan s.15(2) deadlines integrated into unified calendar
- Payroll remittance tracking computing owed vs remitted by month from Beancount entries
- CLI subcommands for calendar view, remittance status, and active alerts
- 20 tests covering all deadline types, urgency levels, weekend adjustment, remittance tracking

## Task Commits

Each task was committed atomically:

1. **Task 1: Filing deadline calendar and payroll remittance tracking** - `4a09791` (feat)
2. **Task 2: CLI integration for deadlines and tests** - `b41327e` (feat)

## Files Created/Modified
- `src/compteqc/echeances/__init__.py` - Module init with public exports
- `src/compteqc/echeances/calendrier.py` - Deadline calculator, alerts, CLI formatter
- `src/compteqc/echeances/remises.py` - Payroll remittance tracking (owed vs remitted)
- `src/compteqc/cli/app.py` - Added echeances sub-app with calendrier/remises/rappels commands
- `tests/test_echeances.py` - 20 tests with freezegun for date control

## Decisions Made
- Weekend adjustment: Saturday/Sunday deadlines pushed to Monday (standard CRA rule)
- Urgency thresholds: critique <= 7d, urgent <= 14d, normal <= 30d, info <= 90d
- CLI footer shows only alerts within 30 days (per discretion recommendation)
- Payroll remittance assumes regular remitter (15th of following month); threshold and quarterly remitters deferred

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- echeances module now available for Fava EcheancesExtension (04-05) which was already built with try-import pattern
- Payroll remittance tracking ready for integration with CPA export package
- All deadline types calculable from any fiscal year-end date

---
*Phase: 05-reporting-cpa-export-and-document-management*
*Completed: 2026-02-19*
