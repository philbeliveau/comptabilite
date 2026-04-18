# Quick Summary

## Outcome

The existing `TaxesQCExtension` was upgraded into a quarterly remittance-prep tab instead of adding a second tax tab.

The new view now:

- defaults to the last completed civil quarter
- shows the selected quarter and remittance deadline
- reports GST collected/perceivable, QST collected/perceivable, GST ITCs, QST ITRs, and net remittance or refund
- breaks source transactions into collection, input-tax, and adjustment buckets
- surfaces warnings for asymmetric TPS/TVQ postings, adjustment-style tax entries, incomplete descriptions, and ongoing periods
- includes an operator checklist framed as preparation support rather than filing automation

The supporting domain layer lives in `src/compteqc/quebec/taxes/remise.py`.

## Important Refactor

`generer_sommaire_periode()` is now sign-aware for tax accounts:

- credits on `Passifs:TPS-Percue` / `Passifs:TVQ-Percue` count as collected/perceivable tax
- debits on `Actifs:TPS-Payee` / `Actifs:TVQ-Payee` count as CTI/RTI
- reverse-direction postings are no longer miscounted as collected tax

That prevents remittance or reclassification entries from inflating the quarter totals.

## Validation

- `uv run ruff check src/compteqc/quebec/taxes/remise.py src/compteqc/fava_ext/taxes_qc/__init__.py tests/test_taxes.py tests/test_fava_quebec.py`
- `uv run pytest tests/test_taxes.py tests/test_fava_quebec.py tests/test_fava_ext.py tests/test_fava_gap_closure.py`
