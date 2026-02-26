---
phase: quick-13
plan: 01
subsystem: fava-dashboard
tags: [double-entry, validation, kpi, dashboard, beancount]
dependency_graph:
  requires: [balance_verification, calculer_soldes]
  provides: [dashboard-balance-kpi, ledger-balance-docs]
  affects: [tableau_bord_extension]
tech_stack:
  patterns: [debit-credit-equilibrium-check, inline-ledger-documentation]
key_files:
  created: []
  modified:
    - src/compteqc/fava_ext/tableau_bord/__init__.py
    - src/compteqc/fava_ext/tableau_bord/templates/TableauBordExtension.html
    - ledger/main.beancount
decisions:
  - Compute balance health from soldes dict (reuse calculer_soldes) rather than importing BalanceVerification class -- simpler, avoids GIFI dependency
  - Debit/credit split approach matches balance_verification.py convention (positive = debit, negative = credit)
metrics:
  duration: 2min
  completed: 2026-02-26
  tasks: 2
  files: 3
---

# Quick Task 13: Document and Surface Double-Entry Validation

**Balance health KPI on Fava dashboard with debit=credit equilibrium check and beancount balance assertion documentation in ledger.**

## What Was Done

### Task 1: Add balance health KPI to dashboard (c8decc5)

Added a `_compute_balance_health()` method to `TableauBordExtension` that computes the algebraic sum of all account balances from `calculer_soldes()`. In a correct double-entry system, the sum of all debit balances must equal the sum of all credit balances (net zero). The method returns a tuple of `(equilibre: bool, ecart: Decimal)`.

Two new keys added to `_kpis` dict: `equilibre` and `ecart`. A public `balance_health()` method exposes these values.

The dashboard template now has a 6th KPI card "Equilibre comptable" that shows:
- Green "Equilibre" when debits equal credits
- Red "Ecart: X.XX $" when there is an imbalance

A subtitle "Debits = Credits" serves as inline documentation of the concept.

### Task 2: Add balance assertions documentation to ledger (26ac262)

Replaced the minimal 3-line TODO comment in `ledger/main.beancount` with a comprehensive documentation block explaining:
- What balance assertions are and how Beancount verifies them at load time
- The `balance` directive syntax with examples
- The `pad + balance` pair for opening balances
- Recommended usage pattern (after each bank reconciliation)
- Preserved the TODO for the real opening balance

The ledger loads with 246 entries and 0 errors.

## Deviations from Plan

None -- plan executed exactly as written.

## Pre-existing Issues Noted

- `tests/test_categorisation.py::TestChargerRegles::test_charger_fichier_vide` fails on main branch before our changes. Out of scope.

## Verification

- Import check: `from compteqc.fava_ext.tableau_bord import TableauBordExtension` -- OK
- Fava extension tests: 18 passed
- Report tests: 37 passed (combined with fava ext)
- Ledger load: 246 entries, 0 errors
- Template has 6 KPI cards (was 5)
