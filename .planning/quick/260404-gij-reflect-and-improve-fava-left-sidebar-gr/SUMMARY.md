# Quick Summary

## Outcome

The left sidebar is now grouped by user intent:

- `Demarrer`: dashboard and Operations
- `Traiter`: approval queue, receipts, AP/AR
- `Conformite Quebec`: payroll, GST/QST, CCA, shareholder loan, deadlines, CPA export
- `Rapports`: financial statements and reference views
- `Maintenance`: editor, errors, import, query, options

The implementation moved from grouping whole `ul.navigation` blocks to grouping individual links. That removes the "everything is clumped together" effect and lets the active section expand automatically.

Entry routes now redirect to:

`/compteqc-corporation-consultation-it-quebec/extension/OperationsExtension/?filter=fichier_source%3A%22%5Edebit%5C-march%5C.csv%24%22`

## Files

- `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js`

## Validation

- `node --input-type=module -e "await import('file:///Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js'); console.log('ok');"`: passed
- `uv run pytest tests/test_fava_gap_closure.py tests/test_fava_quebec.py tests/test_fava_ext.py`: 68 passed, 1 failed

## Validation Note

The remaining pytest failure is pre-existing and unrelated to this change: `tests/test_fava_quebec.py::test_main_beancount_has_all_extensions` still expects `8` Fava extensions while `ledger/main.beancount` currently declares `12`.
