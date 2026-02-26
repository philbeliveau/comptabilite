---
phase: 12-aging-ar-cli
plan: 01
subsystem: accounting
tags: [aging, ar, ap, partial-payments, status-derivation, beancount]

# Dependency graph
requires:
  - phase: 11-ap-foundation
    provides: FactureFournisseur model, RegistreFournisseurs with lister/lister_impayees
provides:
  - Enhanced Facture model with partial payments (montant_paye, solde, est_paye_integralement)
  - InvoiceStatus.PARTIAL enum value
  - determiner_statut() automatic status derivation function
  - LigneFacture.compte_revenu configurable per-line revenue account
  - generer_ecriture_paiement_partiel() for partial payment journal entries
  - RegistreFactures.enregistrer_paiement() and lister_impayees()
  - vieillissement module with AR/AP aging bucket calculations and combined position summary
affects: [12-02-PLAN, 14-fava-extension-tab-mcp]

# Tech tracking
tech-stack:
  added: []
  patterns: [pure-function-aging-engine, status-derivation-pattern, per-line-revenue-grouping]

key-files:
  created:
    - src/compteqc/vieillissement.py
    - tests/test_factures_modeles.py
    - tests/test_vieillissement.py
  modified:
    - src/compteqc/factures/modeles.py
    - src/compteqc/factures/journal.py
    - src/compteqc/factures/registre.py

key-decisions:
  - "Aging module accepts lists of model objects (not registries) keeping it pure and testable"
  - "Status derivation is a standalone function, not a model method, for flexibility"
  - "Revenue grouping uses defaultdict to consolidate multi-line same-account debits"

patterns-established:
  - "Pure function aging engine: calculer_vieillissement_ar/ap accept model lists, no I/O"
  - "Status derivation pattern: determiner_statut() derives from payment state + due date"
  - "Per-line revenue grouping: journal entries group by compte_revenu with defaultdict"

requirements-completed: [AREN-01, AREN-02, AREN-04, AGNG-01, AGNG-02, AGNG-03]

# Metrics
duration: 4min
completed: 2026-02-26
---

# Phase 12 Plan 01: AR/AP Aging Domain Logic Summary

**Enhanced Facture model with partial payment tracking, automatic status derivation, configurable per-line revenue accounts, and pure-function aging bucket engine for AR/AP with combined net position summary**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-26T15:45:09Z
- **Completed:** 2026-02-26T15:49:33Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Facture model enhanced with montant_paye, solde, est_paye_integralement for partial payment tracking
- determiner_statut() correctly derives DRAFT/SENT/PARTIAL/PAID/OVERDUE from payment state and due date
- LigneFacture.compte_revenu enables per-line revenue account (Revenus:Consultation default, Revenus:Produit-Logiciel for software)
- Pure-function aging module buckets AR and AP into 0-30/31-60/61-90/91+ day tranches
- Combined AR/AP position summary with net position and 30-day cash flow impact

## Task Commits

Each task was committed atomically:

1. **Task 1: Enhance Facture model with partial payments, status derivation, and configurable revenue account** - `1b0bd30` (feat)
2. **Task 2: Create aging calculation module with AR, AP, and combined summary** - `b84c50c` (feat)

_Note: TDD tasks had RED/GREEN phases within each commit_

## Files Created/Modified
- `src/compteqc/factures/modeles.py` - Added PARTIAL status, montant_paye/solde/est_paye_integralement fields, determiner_statut(), compte_revenu on LigneFacture
- `src/compteqc/factures/journal.py` - Per-line revenue grouping in generer_ecriture_facture(), new generer_ecriture_paiement_partiel()
- `src/compteqc/factures/registre.py` - Added enregistrer_paiement() and lister_impayees() methods
- `src/compteqc/vieillissement.py` - New aging bucket engine with AR, AP, and combined position functions
- `tests/test_factures_modeles.py` - 16 tests for partial payments, status derivation, revenue accounts, journal entries, registry
- `tests/test_vieillissement.py` - 16 tests for aging calculations, edge cases, combined summary

## Decisions Made
- Aging module accepts lists of model objects (not registries) keeping it pure and testable -- CLI layer (Plan 02) handles registry loading
- Status derivation is a standalone function rather than model method for flexibility in calling from different contexts
- Revenue grouping uses defaultdict to consolidate multi-line same-account debits in journal entries

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Domain logic layer complete and tested (32 tests passing)
- Ready for Plan 02 (CLI commands) to consume these pure functions
- vieillissement module API is stable: calculer_vieillissement_ar(), calculer_vieillissement_ap(), rapport_position_apar()

---
*Phase: 12-aging-ar-cli*
*Completed: 2026-02-26*
