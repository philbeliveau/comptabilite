---
phase: quick-260404-hfi
type: fix
subsystem: fava-export-cpa
tags: [fava, export-cpa, filters, ui]
completed: 2026-04-04
---

# Quick Task 260404-hfi: Make ExportCPAExtension work with filter URLs

## Root Cause

`ExportCPAExtension` was still a stub. The page rendered a generic Phase 5 placeholder, never read Fava's `filter` query parameter, and provided no way to launch the existing CPA package generator from the UI.

## Fix

- Added server-side filter handling in `src/compteqc/fava_ext/export_cpa/__init__.py`.
- Replaced the placeholder template with a real preview page that shows:
  - the active filter
  - the number of matching transactions
  - the included source files
  - the covered date range
  - a transaction preview table
- Added a POST endpoint that reuses `generer_package_cpa()` and downloads a ZIP generated from the current filtered scope and selected fiscal year.
- Added browser-side form handling so the export can be launched directly from the Fava page with inline error reporting.
- Added graceful handling for invalid filter syntax instead of failing silently.
- Added focused tests for filter forwarding, invalid filter handling, no-request fallback, successful ZIP download, and guarded export failures.
- Updated the legacy extension-count assertion in `tests/test_fava_quebec.py` from 8 to 12 to match the current ledger configuration.

## Verification

- `uv run pytest tests/test_export_cpa_extension.py tests/test_fava_quebec.py`
- `uv run python` smoke check with `FavaLedger(...).get_filtered(filter='fichier_source:"^debit\\-march\\.csv$"')` confirms 8 matching transactions from `debit-march.csv`.
