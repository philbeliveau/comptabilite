---
phase: quick-15
plan: 01
subsystem: design
tags: [accounts-payable, accounts-receivable, aging, gst-qst, itc-itr, beancount, pydantic]

requires:
  - phase: 01-ledger-foundation
    provides: chart of accounts, Beancount ledger structure
  - phase: factures
    provides: Facture model, journal entry generation, YAML registry
provides:
  - AP/AR system design document
  - FactureFournisseur data model specification
  - Aging report logic specification
  - GST/QST ITC/ITR handling specification
  - 4-phase implementation roadmap
affects: [fournisseurs, vieillissement, fava-dashboard, mcp-server, import-pipeline]

tech-stack:
  added: []
  patterns: [mirror-existing-facture-pattern, yaml-registry, french-account-names]

key-files:
  created:
    - docs/design/accounts-payable-receivable.md
  modified: []

key-decisions:
  - "Flat Passifs:ComptesFournisseurs account (GIFI 2010) without sub-accounts for solo consultant simplicity"
  - "Mirror existing Facture/RegistreFactures pattern for AP bill tracking"
  - "Per-line taux_itc/taux_itr fields for partial ITC/ITR eligibility (meals at 50%)"
  - "Derive invoice status from payment state rather than adding PARTIAL enum value"
  - "4-phase implementation roadmap: Foundation -> Aging/CLI -> Recurring/Auto-match -> Dashboard/MCP"

patterns-established:
  - "AP mirrors AR: same model structure, same YAML registry pattern, same journal entry generation"
  - "Aging buckets: Current (0-30), 30-60, 60-90, 90+ days past due"

requirements-completed: [APAR-DESIGN]

duration: 3min
completed: 2026-02-26
---

# Quick Task 15: AP/AR Design Summary

**Comprehensive AP/AR design document covering new vendor bill tracking (Passifs:ComptesFournisseurs GIFI 2010), AR enhancements (aging, partial payments, recurring invoices), GST/QST ITC/ITR handling, and 4-phase implementation roadmap**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T13:32:39Z
- **Completed:** 2026-02-26T13:35:42Z
- **Tasks:** 1
- **Files created:** 1

## Accomplishments

- Analyzed existing AR system (Facture model, journal entries, YAML registry) and identified 5 gaps
- Designed complete AP system: account structure (GIFI 2010), FactureFournisseur Pydantic model, BillStatus enum, RegistreFournisseurs
- Specified GST/QST ITC/ITR handling with per-line eligibility rates for restricted expenses (meals at 50%)
- Designed AR/AP aging reports with 4 buckets and combined position summary
- Defined integration points: import pipeline auto-matching, AI categorizer, Fava dashboard panel, MCP tools
- Created phased implementation roadmap (A: Foundation, B: Aging/CLI, C: Recurring/Auto-match, D: Dashboard/MCP)

## Task Commits

1. **Task 1: Write AP/AR design document** - `851fdc4` (docs)

## Files Created/Modified

- `docs/design/accounts-payable-receivable.md` - Complete AP/AR design document (851 lines) with 7 major sections, Beancount journal entry examples, Pydantic model sketches, and implementation roadmap

## Decisions Made

- Used flat `Passifs:ComptesFournisseurs` (GIFI 2010) without sub-accounts -- solo consultant volume does not warrant the complexity
- Mirrored existing Facture/RegistreFactures pattern exactly for AP, reducing learning curve and implementation effort
- Added `taux_itc`/`taux_itr` per-line fields for partial ITC/ITR eligibility rather than a separate meals-handling system
- Recommended deriving invoice status from payment amounts rather than adding a PARTIAL enum, keeping the model simpler
- Structured roadmap so Phase A (foundation) is prerequisite, then B and C can run in parallel

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - design document only, no code changes.

## Next Phase Readiness

- Design document is ready to serve as implementation spec for Phase A (AP foundation)
- Existing AR enhancement specs (aging, partial payments, recurring) are ready for Phase B/C
- All Beancount account names and GIFI codes are validated against existing chart of accounts

---
*Quick Task: 15-design-accounts-payable-and-accounts-rec*
*Completed: 2026-02-26*
