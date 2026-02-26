---
phase: 11-ap-foundation
plan: 01
subsystem: accounting
tags: [pydantic, yaml, beancount, accounts-payable, gst-qst, itc-itr]

# Dependency graph
requires:
  - phase: 01-ledger-foundation
    provides: "Chart of accounts (comptes.beancount), Beancount ledger structure"
  - phase: 05-reports-export
    provides: "AR factures module (compteqc.factures.modeles, registre) -- mirrored pattern"
provides:
  - "FactureFournisseur, LigneFactureFournisseur, BillStatus Pydantic models"
  - "RegistreFournisseurs YAML-backed bill registry with FOUR-YYYY-NNN numbering"
  - "Passifs:ComptesFournisseurs (GIFI 2010) in chart of accounts"
  - "Per-line taux_itc/taux_itr for partial ITC/ITR eligibility"
affects: [11-02-PLAN, ap-journal-entries, fava-ap-tab]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Mirror AR factures pattern for AP fournisseurs module"]

key-files:
  created:
    - "src/compteqc/fournisseurs/__init__.py"
    - "src/compteqc/fournisseurs/modeles.py"
    - "src/compteqc/fournisseurs/registre.py"
    - "tests/test_fournisseurs.py"
  modified:
    - "ledger/comptes.beancount"

key-decisions:
  - "Reuse TAUX_TPS, TAUX_TVQ, QUANTIZE_CENT from compteqc.factures.modeles for consistency"
  - "tps/tvq properties compute full tax (vendor bill amounts); partial ITC/ITR split deferred to journal entry generator (Plan 02)"

patterns-established:
  - "AP fournisseurs module mirrors AR factures module structure (modeles.py + registre.py)"
  - "FOUR-YYYY-NNN numbering convention for vendor bills (vs FAC-YYYY-NNN for invoices)"

requirements-completed: [APFN-01, APFN-02, APFN-05]

# Metrics
duration: 3min
completed: 2026-02-26
---

# Phase 11 Plan 01: AP Data Model Summary

**Pydantic vendor bill models with GST/QST auto-calculation, YAML registry with FOUR-YYYY-NNN numbering, and Passifs:ComptesFournisseurs (GIFI 2010) in chart of accounts**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T15:32:12Z
- **Completed:** 2026-02-26T15:35:10Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Added Passifs:ComptesFournisseurs (GIFI 2010) to chart of accounts -- Beancount validates with 0 errors
- Created FactureFournisseur/LigneFactureFournisseur models with GST 5% + QST 9.975% auto-calculation and per-line taux_itc/taux_itr for partial ITC/ITR
- Created RegistreFournisseurs with full CRUD, unpaid bill filtering, and FOUR-YYYY-NNN sequential numbering
- Comprehensive test suite: 22 tests covering tax math, solde tracking, registry persistence, and numbering -- all passing with no AR regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add AP account and create data models** - `b0580aa` (feat)
2. **Task 2: Create RegistreFournisseurs YAML registry** - `28fc2df` (feat)
3. **Task 3: Comprehensive tests** - `c90e194` (test)

## Files Created/Modified
- `ledger/comptes.beancount` - Added Passifs:ComptesFournisseurs with GIFI 2010
- `src/compteqc/fournisseurs/__init__.py` - Package init for AP module
- `src/compteqc/fournisseurs/modeles.py` - FactureFournisseur, LigneFactureFournisseur, BillStatus models
- `src/compteqc/fournisseurs/registre.py` - RegistreFournisseurs YAML-backed registry
- `tests/test_fournisseurs.py` - 22 unit tests for AP models and registry

## Decisions Made
- Reused TAUX_TPS, TAUX_TVQ, QUANTIZE_CENT constants from compteqc.factures.modeles for consistency across AR/AP
- tps/tvq model properties compute full tax amounts (as the vendor bills them); partial ITC/ITR split via taux_itc/taux_itr is deferred to the journal entry generator in Plan 02

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AP data model and registry ready for Plan 02 (journal entry generation)
- FactureFournisseur.taux_itc/taux_itr fields ready for partial ITC/ITR split in journal entries
- Passifs:ComptesFournisseurs account available for AP postings

## Self-Check: PASSED

All 4 created files verified. All 3 commit hashes verified.

---
*Phase: 11-ap-foundation*
*Completed: 2026-02-26*
