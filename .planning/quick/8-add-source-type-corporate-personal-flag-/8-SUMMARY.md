---
phase: quick-8
plan: 01
subsystem: cli
tags: [typer, beancount, pipeline, shareholder-loan]

requires:
  - phase: 03-categorisation
    provides: PipelineCategorisation and ResultatPipeline
provides:
  - "--source-type corporate|personal CLI flag for import command"
  - "Personal source short-circuit bypassing categorization pipeline"
affects: [importer, pipeline, shareholder-loan]

tech-stack:
  added: []
  patterns: [source-type short-circuit in _appliquer_pipeline_et_router]

key-files:
  created: []
  modified:
    - src/compteqc/cli/importer.py
    - src/compteqc/categorisation/pipeline.py
    - tests/test_pipeline.py
    - tests/test_cli.py

key-decisions:
  - "Personal transactions get flag '*' (auto-approved) since no human review needed"
  - "Pipeline creation skipped entirely for personal imports (no ML/LLM initialization overhead)"

patterns-established:
  - "source_type parameter threading: CLI -> _importer_avec -> _appliquer_pipeline_et_router"

requirements-completed: [QUICK-8]

duration: 8min
completed: 2026-02-20
---

# Quick Task 8: Add --source-type corporate|personal Flag Summary

**CLI --source-type flag routing personal bank CSVs directly to Passifs:Pret-Actionnaire, bypassing rules/ML/LLM/CAPEX pipeline entirely**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-20T16:40:30Z
- **Completed:** 2026-02-20T16:48:02Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `--source-type` / `-s` CLI option with `corporate` (default) and `personal` values
- Personal source transactions skip entire categorization pipeline and route to `Passifs:Pret-Actionnaire` with flag `*` and `source_type=personal` metadata
- Corporate imports remain completely unchanged -- zero behavioral difference
- 4 new tests covering short-circuit logic, pipeline interaction, CLI validation, and default value

## Task Commits

Each task was committed atomically:

1. **Task 1: Add --source-type flag to CLI and wire personal short-circuit** - `06fc761` (feat)
2. **Task 2: Add tests for personal source-type pipeline short-circuit** - `45af8a4` (test)

## Files Created/Modified
- `src/compteqc/cli/importer.py` - Added --source-type flag, validation, personal short-circuit in _appliquer_pipeline_et_router, pipeline skip in _importer_avec
- `src/compteqc/categorisation/pipeline.py` - Updated ResultatPipeline source docstring to include "personal"
- `tests/test_pipeline.py` - 2 new tests: personal short-circuit and corporate pipeline call verification
- `tests/test_cli.py` - 2 new tests: CLI validation and default value check

## Decisions Made
- Personal transactions get flag `*` (auto-approved) since shareholder loan entries need no human categorization review
- Pipeline creation is entirely skipped for personal imports (avoids ML training, LLM client init overhead)
- Validation uses early exit with `typer.Exit(1)` matching existing CLI error patterns

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing test failures found in `test_cli.py` (4 tests: `test_soldes_ledger_vide`, `test_balance_ledger_vide`, `test_resultats_ledger_vide`, `test_bilan_ledger_vide`) and `test_categorisation.py` (`test_charger_fichier_vide`). These fail due to real ledger data leaking into tmp fixtures via includes. Not caused by this task's changes -- verified by running the same tests before applying any changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Personal bank CSV import workflow is ready for use
- Usage: `cqc importer fichier personal_bank.csv --source-type personal`

---
*Quick Task: 8*
*Completed: 2026-02-20*
