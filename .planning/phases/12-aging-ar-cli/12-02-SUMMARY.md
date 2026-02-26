---
phase: 12-aging-ar-cli
plan: 02
subsystem: cli
tags: [typer, rich, ap-billing, aging-reports, cli, beancount]

# Dependency graph
requires:
  - phase: 12-aging-ar-cli-01
    provides: vieillissement module (aging bucket calculations), enhanced Facture model with partial payments
  - phase: 11-ap-foundation
    provides: FactureFournisseur model, RegistreFournisseurs, AP journal entry generators
provides:
  - CLI commands for AP bill management (cqc fournisseur add/list/voir/pay)
  - CLI commands for aging reports (cqc aging ar/ap/summary)
  - Enhanced AR invoice listing with PARTIAL status filter and Solde column
affects: [14-fava-extension-tab-mcp]

# Tech tracking
tech-stack:
  added: []
  patterns: [mirrored-cli-module-pattern, color-coded-aging-buckets]

key-files:
  created:
    - src/compteqc/cli/fournisseur.py
    - src/compteqc/cli/aging.py
  modified:
    - src/compteqc/cli/facture.py
    - src/compteqc/cli/app.py

key-decisions:
  - "Payment recording via mettre_a_jour_statut with montant_paye parameter rather than separate enregistrer_paiement method"
  - "AP aging table includes vendor reference number column for cross-referencing"
  - "Solde column in AR invoice list only shows value when different from total (cleaner display)"

patterns-established:
  - "Mirrored CLI module pattern: fournisseur.py mirrors facture.py structure exactly for consistency"
  - "Color-coded aging buckets: green (0-30), yellow (31-60), dark_orange (61-90), red (91+)"

requirements-completed: [AREN-03, AGNG-04, CLAP-01, CLAP-02, CLAP-03]

# Metrics
duration: 5min
completed: 2026-02-26
---

# Phase 12 Plan 02: AP/AR CLI Commands Summary

**Full AP bill management CLI (add/list/voir/pay) with aging reports (ar/ap/summary) and enhanced AR invoice listing supporting PARTIAL status**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-26T15:51:58Z
- **Completed:** 2026-02-26T15:56:45Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Complete AP bill lifecycle via CLI: create, list, view details, full/partial payment with Beancount journal entries
- Aging reports for AR and AP with color-coded bucket tables and per-tranche summaries
- Combined AP/AR position summary with net position and 30-day cash flow impact
- Enhanced AR invoice listing with PARTIAL status filter and conditional Solde column

## Task Commits

Each task was committed atomically:

1. **Task 1: Create AP bill CLI commands (fournisseur add/list/voir/pay)** - `c0c67b9` (feat)
2. **Task 2: Create aging CLI commands and register all new sub-apps** - `6baa305` (feat)

## Files Created/Modified
- `src/compteqc/cli/fournisseur.py` - AP bill management: add, list, voir, pay commands with Rich tables
- `src/compteqc/cli/aging.py` - Aging reports: ar, ap, summary commands with color-coded buckets
- `src/compteqc/cli/facture.py` - Added PARTIAL style, updated status help/error messages, added Solde column
- `src/compteqc/cli/app.py` - Registered fournisseur and aging sub-apps

## Decisions Made
- Payment recording uses mettre_a_jour_statut with montant_paye parameter (existing registry API) rather than adding a new enregistrer_paiement method
- AP aging table includes vendor reference number column for easy cross-referencing with vendor invoices
- Solde column in AR invoice list conditionally shows value only when partial payment exists (cleaner display for fully unpaid invoices)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full CLI for AP/AR management and aging reports is complete
- All domain logic (Plan 01) and CLI layer (Plan 02) are operational
- Ready for Fava extension integration (Phase 14) to surface these in the web UI

---
*Phase: 12-aging-ar-cli*
*Completed: 2026-02-26*
