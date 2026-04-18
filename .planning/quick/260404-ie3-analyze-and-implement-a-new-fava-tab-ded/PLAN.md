# Quick Plan

## Task

Analyze and implement a quarterly GST/QST remittance-prep Fava tab for a Quebec incorporated small business.

## Intent

- Reuse the existing Quebec tax domain instead of duplicating logic in the template layer.
- Keep the tab operational and audit-friendly without pretending to be filing software.
- Make quarter selection, due dates, warnings, and transaction drilldowns deterministic.

## Steps

1. Inspect the existing TPS/TVQ summary code, Fava tab, ledger accounts, and relevant tests.
2. Confirm quarter-remittance prep requirements against official CRA and Revenu Quebec sources.
3. Add shared quarterly remittance-prep helpers under `compteqc.quebec.taxes`.
4. Refactor `TaxesQCExtension` into a quarter-focused preparation tab with warnings, drilldowns, and checklist.
5. Add focused tests for period selection, sign-safe tax aggregation, and extension behavior.
6. Run targeted Ruff and pytest validation for the touched tax and Fava surfaces.
