---
phase: quick-260404-gga
type: investigate-and-fix
subsystem: fava-ui
tags: [fava, ui, journal, income-statement, filters, sidebar]
completed: 2026-04-04
---

# Quick Task 260404-gga: Fava UI inconsistency investigation

## Root Cause

The ledger itself is correct and Fava loads the included monthly files correctly. The confusing `6.00` expense view came from Fava's normal scoped-report behavior: when the current page carries `account=Actifs:Banque:RBC:Cheques`, native report links inherit that account filter and the income statement only includes transactions touching the chequing account.

That scoped view excludes the `175.00` annual fee because it is posted to `Passifs:CartesCredit:RBC`, not `Actifs:Banque:RBC:Cheques`.

## Verification

- `uv run bean-check ledger/main.beancount` passes.
- `uv run cqc rapport resultats` shows the expected totals.
- Fresh Fava instance on port `5012` loads `ledger/2026/03.beancount` and `ledger/2026/04.beancount`.
- Touching `ledger/2026/04.beancount` triggers `/<slug>/api/changed` and Fava reloads included files.
- Reproduced the exact `6.00` symptom by applying Fava's account filter `Actifs:Banque:RBC:Cheques`.

## Fix

Updated `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` so sidebar links for Fava's global native reports strip inherited `account`, `filter`, `time`, and `conversion` query parameters before navigation.
