---
phase: 01-ledger-foundation-and-import-pipeline
plan: 03
subsystem: cli
tags: [typer, rich, beancount, cli, french-ui, git-auto-commit]

requires:
  - phase: 01-01
    provides: "Python project structure, Beancount ledger, validation/git/file utilities"
  - phase: 01-02
    provides: "RBC importers (CSV cheques, CSV carte, OFX), categorisation engine"
provides:
  - "CLI `cqc` with French interface installable via pyproject.toml"
  - "Import command: cqc importer fichier <path> with auto-detection, categorisation, validation, rollback, git commit"
  - "Report commands: soldes, rapport balance, rapport resultats, rapport bilan"
  - "Review command: cqc revue for unclassified transaction identification"
  - "21 CLI integration tests covering import, reports, and error handling"
affects: [02-quebec-domain-logic, 03-categorization, 04-review-ui, 05-cpa-export]

tech-stack:
  added: []
  patterns: [Typer CLI with Rich table formatting, global options via callback, isolated test ledgers with tmp_path]

key-files:
  created:
    - src/compteqc/cli/app.py
    - src/compteqc/cli/importer.py
    - src/compteqc/cli/rapports.py
    - tests/test_cli.py
  modified:
    - src/compteqc/ledger/fichiers.py
    - ledger/2026/01.beancount

key-decisions:
  - "Monthly beancount files require name_* options (same Beancount v3 requirement as comptes.beancount)"
  - "Reports compute balances directly from Transaction postings instead of beanquery (simpler, no inventory type handling)"
  - "Bilan includes resultat net (Revenus - Depenses) under capitaux propres for accounting equation verification"

patterns-established:
  - "CLI global options (--ledger, --regles) accessible via get_ledger_path()/get_regles_path()"
  - "Import pipeline: detect -> extract -> categorise -> write -> validate -> rollback-if-invalid -> archive -> commit"
  - "CLI tests use isolated ledger in tmp_path with pre-initialized git repo"
  - "French error messages and table headers throughout CLI"

requirements-completed: [CLI-01, CLI-06]

duration: 8min
completed: 2026-02-19
---

# Phase 1 Plan 3: CLI and Reports Summary

**Typer CLI `cqc` with French interface: import command (auto-detect, categorise, validate, rollback, git commit) and Rich-formatted reports (soldes, balance, resultats, bilan, revue)**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-19T12:29:32Z
- **Completed:** 2026-02-19T12:37:47Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Full import pipeline via CLI: `cqc importer fichier <path>` detects format, extracts transactions, categorises, writes to ledger, validates with bean-check, rolls back on failure, archives source file, and creates git commit
- Five report commands with Rich table formatting: soldes (account balances), balance (trial balance), resultats (P&L), bilan (balance sheet with equation check), revue (unclassified transactions)
- 21 CLI integration tests using isolated temporary ledgers, covering help, version, import, reports, and error handling
- All 99 tests across the phase pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Creer l'application CLI et la commande d'import** - `33e1834` (feat)
2. **Task 2: Creer les commandes de rapport et les tests CLI** - `ec233b8` (feat)

## Files Created/Modified

- `src/compteqc/cli/app.py` - Main Typer app with global options (--ledger, --regles, --version), command registration
- `src/compteqc/cli/importer.py` - Import command with auto-detection, categorisation, validation, rollback, git auto-commit
- `src/compteqc/cli/rapports.py` - Report commands (soldes, balance, resultats, bilan) and revue command
- `src/compteqc/ledger/fichiers.py` - Updated to add Beancount v3 name_* options in monthly files
- `ledger/2026/01.beancount` - Added name_* options for French account name support
- `tests/test_cli.py` - 21 integration tests with isolated ledger fixtures

## Decisions Made

- **Monthly files need name_* options:** Same as comptes.beancount, every included .beancount file that uses French account names must declare name_* options. Updated chemin_fichier_mensuel() to include these automatically.
- **Direct balance computation instead of beanquery:** Report commands iterate over Transaction postings directly instead of using beanquery SQL queries. This avoids handling beanquery's inventory types and is simpler for our single-currency use case.
- **Bilan includes resultat net:** The balance sheet includes Revenus - Depenses as "Resultat net de l'exercice" under capitaux propres, ensuring the accounting equation (Actifs = Passifs + Capitaux) verifies correctly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Monthly beancount files missing name_* options**
- **Found during:** Task 1 (import command)
- **Issue:** Imported transactions written to monthly file caused bean-check to fail with "Invalid account name" for all French accounts because Beancount v3 requires name_* options in every included file
- **Fix:** Updated `chemin_fichier_mensuel()` in fichiers.py to include all 5 name_* option directives when creating new monthly files. Also added options to existing `ledger/2026/01.beancount`.
- **Files modified:** `src/compteqc/ledger/fichiers.py`, `ledger/2026/01.beancount`
- **Verification:** `uv run bean-check ledger/main.beancount` passes after import
- **Committed in:** `33e1834` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix necessary for import to work at all. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 1 is now complete: ledger foundation, importers, categorisation, and CLI are all operational
- The full pipeline works end-to-end: import RBC files -> categorise -> write to ledger -> validate -> git commit -> view reports
- Ready for Phase 2 (Quebec Domain Logic): payroll, GST/QST, CCA modules
- The CLI can be extended with new commands as domain modules are built

## Self-Check: PASSED

All 6 key files verified present. Both task commits (33e1834, ec233b8) verified in git log.

---
*Phase: 01-ledger-foundation-and-import-pipeline*
*Completed: 2026-02-19*
