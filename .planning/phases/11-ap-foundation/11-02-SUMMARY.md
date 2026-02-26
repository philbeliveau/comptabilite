---
phase: 11-ap-foundation
plan: 02
subsystem: accounting
tags: [beancount, ap, journal-entries, itc, itr, gst, qst, accounts-payable]

# Dependency graph
requires:
  - phase: 11-ap-foundation plan 01
    provides: FactureFournisseur model, LigneFactureFournisseur, RegistreFournisseurs
provides:
  - generer_ecriture_facture_fournisseur() for AP bill recording entries
  - generer_ecriture_paiement_fournisseur() for AP payment entries
  - Balanced Beancount transaction generation with partial ITC/ITR support
affects: [ap-fava-ui, ap-cli, ap-mcp, reports]

# Tech tracking
tech-stack:
  added: []
  patterns: [defaultdict accumulation for multi-line journal entries, balancing via negative sum of debits]

key-files:
  created:
    - src/compteqc/fournisseurs/journal.py
  modified:
    - tests/test_fournisseurs.py

key-decisions:
  - "AP credit computed as negative sum of all debit postings (not independently from bill.total) to guarantee balance"
  - "Postings accumulated per account via defaultdict to consolidate multi-line same-account debits"
  - "Sorted output: expenses first, then assets, then liabilities for consistent readable output"

patterns-established:
  - "Partial ITC/ITR: non-claimable tax portion added to expense account, not tax receivable"
  - "Payment method routing via COMPTE_PAIEMENT dict with fallback to COMPTE_PAIEMENT_DEFAUT"

requirements-completed: [APFN-03, APFN-04]

# Metrics
duration: 2min
completed: 2026-02-26
---

# Phase 11 Plan 02: AP Journal Entry Generators Summary

**Beancount journal entry generators for AP bill recording (multi-line expense + partial ITC/ITR) and payment (method-based account routing with partial payment support)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T15:37:14Z
- **Completed:** 2026-02-26T15:39:39Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- generer_ecriture_facture_fournisseur: per-line expense posting with partial ITC/ITR for restricted expenses (meals at 50%)
- generer_ecriture_paiement_fournisseur: full/partial payment with cheque/virement/carte-credit routing
- 33 total tests passing (22 from Plan 01 + 11 new journal entry tests), all entries verified balanced

## Task Commits

Each task was committed atomically:

1. **Task 1: Create journal entry generators** - `1ea8090` (feat)
2. **Task 2: Tests for journal entry generation** - `9aecea5` (test)

## Files Created/Modified
- `src/compteqc/fournisseurs/journal.py` - AP bill recording and payment Beancount entry generators
- `tests/test_fournisseurs.py` - 11 new tests for journal entries (balance, partial ITC/ITR, narration, dates, payment methods)

## Decisions Made
- AP credit computed as negative sum of all accumulated debit postings to guarantee exact balance (avoids rounding drift from independent total computation)
- Postings accumulated via defaultdict(Decimal) to consolidate multiple lines posting to the same expense account
- Output sorted deterministically: expenses, then assets, then liabilities

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AP data layer complete (models, registry, journal entries)
- Ready for AP CLI commands, Fava UI tab, or MCP integration
- Mirrors AR pattern (factures/) for consistency

---
*Phase: 11-ap-foundation*
*Completed: 2026-02-26*
