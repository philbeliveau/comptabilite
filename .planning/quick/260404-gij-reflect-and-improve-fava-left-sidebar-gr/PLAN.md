# Quick Plan

## Task

Reflect and improve the Fava left sidebar grouping, and make the platform land on the filtered Operations view for `debit-march.csv`.

## Intent

- Reorganize navigation around the operator workflow instead of Fava's raw mixed tab list.
- Make the first screen operational and immediately scoped to the March debit import review flow.
- Keep the change isolated to the theme/navigation layer so ledger and extension backends remain untouched.

## Steps

1. Inspect the current sidebar grouping and default landing behavior.
2. Replace list-level grouping with link-level grouping so each tab can be placed in the right workflow section.
3. Add route-aware expansion so the active section stays open.
4. Redirect entry routes to `OperationsExtension` with the requested `filter` query.
5. Run narrow validation for JS syntax and Fava-related pytest coverage.
