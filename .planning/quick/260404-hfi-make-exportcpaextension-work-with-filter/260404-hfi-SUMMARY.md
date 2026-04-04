---
phase: quick-260404-hfi
type: fix
subsystem: fava-export-cpa
tags: [fava, export-cpa, filters, ui]
completed: 2026-04-04
---

# Quick Task 260404-hfi: Make ExportCPAExtension work with filter URLs

## Root Cause

`ExportCPAExtension` was still a stub. The page rendered a generic Phase 5 placeholder and never read Fava's `filter` query parameter, so URLs such as `...?filter=fichier_source:"^debit\\-march\\.csv$"` could not confirm the export scope.

## Fix

- Added server-side filter handling in `src/compteqc/fava_ext/export_cpa/__init__.py`.
- Replaced the placeholder template with a real preview page that shows:
  - the active filter
  - the number of matching transactions
  - the included source files
  - the covered date range
  - a transaction preview table
- Added graceful handling for invalid filter syntax instead of failing silently.
- Added focused tests for filter forwarding, invalid filter handling, and no-request fallback.
- Updated the legacy extension-count assertion in `tests/test_fava_quebec.py` from 8 to 12 to match the current ledger configuration.

## Verification

- `uv run pytest tests/test_export_cpa_extension.py tests/test_fava_quebec.py`
- `uv run python` smoke check with `FavaLedger(...).get_filtered(filter='fichier_source:"^debit\\-march\\.csv$"')` confirms 8 matching transactions from `debit-march.csv`.
