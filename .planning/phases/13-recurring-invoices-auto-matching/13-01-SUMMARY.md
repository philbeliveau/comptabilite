---
phase: 13-recurring-invoices-auto-matching
plan: 01
subsystem: invoicing
tags: [recurring, templates, yaml, pydantic, dateutil, typer, cli]

# Dependency graph
requires:
  - phase: 11-ap-foundation
    provides: "Facture/RegistreFactures models and YAML persistence pattern"
provides:
  - "ModeleFactureRecurrente model for recurring invoice templates"
  - "RegistreRecurrents YAML-persisted template registry"
  - "generer_factures_recurrentes() automatic invoice generation from due templates"
  - "CLI commands: template-add, template-list, generate-recurring"
affects: [13-02, fava-extension-tab-mcp]

# Tech tracking
tech-stack:
  added: [python-dateutil (relativedelta)]
  patterns: [recurring-template-registry, frequency-based-date-advancement]

key-files:
  created:
    - src/compteqc/factures/recurrent.py
    - tests/test_recurrent.py
  modified:
    - src/compteqc/cli/facture.py

key-decisions:
  - "Removed prompt on --frequence CLI option (has default 'mensuel', prompt breaks non-interactive use)"
  - "Used model_copy(update=...) for immutable template updates during generation"
  - "Date advancement uses relativedelta for months, timedelta for bimensuel (2 weeks)"

patterns-established:
  - "RegistreRecurrents: mirrors RegistreFactures pattern for YAML persistence of templates"
  - "avancer_date(): pure function for frequency-based date computation"

requirements-completed: [RECM-01, RECM-02]

# Metrics
duration: 4min
completed: 2026-02-26
---

# Phase 13 Plan 01: Recurring Invoice Templates Summary

**Recurring invoice templates with YAML persistence, frequency-based auto-generation, and CLI management commands**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-26T16:05:23Z
- **Completed:** 2026-02-26T16:09:25Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- ModeleFactureRecurrente pydantic model with frequency scheduling (mensuel/bimensuel/trimestriel/annuel)
- RegistreRecurrents YAML registry with add/list/update/persistence operations
- generer_factures_recurrentes() creates invoices from due templates with correct FAC-YYYY-NNN numbering
- CLI commands: template-add, template-list, generate-recurring (with dry-run mode)
- 17 tests covering model validation, YAML persistence, date advancement, generation logic, and CLI integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ModeleFactureRecurrente model, registry, and generation logic with TDD** - `4517dcc` (feat)
2. **Task 2: Add recurring template CLI commands to facture_app** - `3e881fd` (feat)

## Files Created/Modified
- `src/compteqc/factures/recurrent.py` - ModeleFactureRecurrente model, RegistreRecurrents, avancer_date(), generer_factures_recurrentes()
- `tests/test_recurrent.py` - 17 tests: model, registry, generation, CLI integration
- `src/compteqc/cli/facture.py` - Added template-add, template-list, generate-recurring commands

## Decisions Made
- Removed prompt on `--frequence` CLI option since it has a default value of "mensuel" -- prompts break non-interactive CLI usage in tests and scripts
- Used `model_copy(update=...)` for immutable Pydantic model updates when advancing template dates
- `avancer_date()` uses `relativedelta` for month-based frequencies and `timedelta` for bimensuel (2 weeks)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed prompt from --frequence CLI option**
- **Found during:** Task 2 (CLI tests)
- **Issue:** `--frequence` had both a default value ("mensuel") and a prompt, causing Typer to always prompt even when the default was acceptable, breaking non-interactive CLI usage
- **Fix:** Changed `prompt=` to `help=` for the --frequence option
- **Files modified:** src/compteqc/cli/facture.py
- **Verification:** All 17 tests pass including CLI integration tests
- **Committed in:** 3e881fd (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor UX fix for CLI option. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Recurring templates ready for Plan 02 (auto-matching)
- Templates persist in `ledger/factures/modeles-recurrents.yaml`
- Generation logic integrates with existing RegistreFactures and Beancount journal entries

---
*Phase: 13-recurring-invoices-auto-matching*
*Completed: 2026-02-26*
