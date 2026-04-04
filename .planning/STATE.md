---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: AP/AR & Financial Operations
status: unknown
last_updated: "2026-04-04T16:05:00.000Z"
progress:
  total_phases: 13
  completed_phases: 11
  total_plans: 23
  completed_plans: 23
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Every dollar that flows through the corporation is correctly categorized, traceable to source documents, and ready for CPA review -- without manual data entry.
**Current focus:** Phase 15 - Receipt-to-AP Pipeline (v1.2 AP/AR & Financial Operations)

## Current Position

Phase: 15 of 15 (Receipt-to-AP Pipeline)
Plan: 2 of 2 in current phase (Plan 02 complete)
Status: Phase 15 complete -- all 2 plans done
Last activity: 2026-02-26 - Completed Plan 15-02: AR/AP Match Suggestions in Approval Queue

Progress: [####################] 100% (v1.2 phases 11-15)

## Performance Metrics

**Velocity:**
- Total plans completed: 23 (v1.0) + 17 quick tasks
- Average duration: ~45 min (v1.0)
- Total execution time: ~17 hours (v1.0)

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Ledger Foundation | 3 | ~2h | ~40 min |
| 2. Quebec Domain | 5 | ~4h | ~48 min |
| 3. AI Categorization | 3 | ~2h | ~40 min |
| 4. MCP + Dashboard | 5 | ~4h | ~48 min |
| 5. Reports + Export | 5 | ~4h | ~48 min |

**By Phase (v1.2):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 11. AP Foundation | 2/2 | 5min | 2.5 min |
| 12. Aging AR/CLI | 2/2 | 9min | 4.5 min |
| 13. Recurring Invoices | 2/2 | 9min | 4.5 min |
| 14. Fava Extension Tab | 3/3 | 8min | 2.7 min |
| 15. Receipt-to-AP | 2/2 | 4min | 2 min |
| 15. Receipt-to-AP | 1/2 | 1min | 1 min |

## Accumulated Context

### Decisions

All v1.0 decisions logged in PROJECT.md Key Decisions table (14 entries).
Key v1.1/v1.2 decisions affecting AP/AR work:
- Flat Passifs:ComptesFournisseurs (GIFI 2010) for AP -- solo consultant does not need sub-accounts
- Mirror existing Facture/RegistreFactures pattern for AP bill tracking (consistency over novelty)
- Per-line taux_itc/taux_itr for partial ITC/ITR eligibility (meals at 50%)
- Inline form expansion (not modal) for AP/AR invoice creation in Fava tab
- Receipt-to-AP pipeline via URL query parameters for stateless form pre-fill
- cqc-tab-toggle pattern for sub-tab switching within a single Fava extension
- Design doc: docs/design/accounts-payable-receivable.md (1671 lines) is the implementation reference
- Reuse TAUX_TPS/TAUX_TVQ/QUANTIZE_CENT from factures.modeles for AP module (consistency)
- tps/tvq model properties compute full tax; partial ITC/ITR split deferred to journal entry generator (Plan 02)
- AP credit computed as negative sum of all debit postings (guarantees exact balance, avoids rounding drift)
- Postings accumulated via defaultdict(Decimal) to consolidate multi-line same-account debits
- Aging module accepts model lists (not registries) -- pure functions with no I/O for testability
- Status derivation as standalone function (determiner_statut) not model method
- Revenue grouping uses defaultdict to consolidate multi-line same-account debits in AR journal entries
- Payment recording via mettre_a_jour_statut with montant_paye param (reuse existing registry API)
- AP aging table includes vendor reference number column for cross-referencing
- Solde column in AR invoice list only shows value when different from total (cleaner display)
- RegistreRecurrents mirrors RegistreFactures YAML persistence pattern for recurring templates
- avancer_date() uses relativedelta for months, timedelta for bimensuel (2 weeks)
- Removed prompt on --frequence CLI option (default 'mensuel', prompt breaks non-interactive use)
- Protocol pattern (FactureOuverte) for forward-compatible auto-matching interface
- Shared _calculer_score() eliminates AR/AP duplication in matching engine
- Registry path injection in _afficher_rapprochements for testability
- Chart.js callbacks as JSON placeholders for data-chart pattern compatibility
- Aging classification uses days past due threshold (30/60/90) with CSS class mapping
- MCP aging tools use list-based vieillissement API (ResumeVieillissement) not registry-based
- Local imports in MCP tool functions for lazy loading, patched via __init__/methods in tests
- [Phase 14]: Form action URLs use /g.beancount_file_slug/extension/name/endpoint pattern for POST endpoints
- [Phase 14]: Dynamic line items use indexed form fields (description_0, description_1...) parsed with while loop
- [Phase 14]: URL query parameter prefill hook for stateless cross-extension form pre-population
- [Phase 15]: Conditional imports for rapprochement/fournisseurs ensure graceful degradation in approval queue
- [Phase 15]: Match suggestion rows as sibling <tr> elements (not modals) for AR/AP matches
- [Phase 15]: lier_apar endpoint follows same redirect-back UX as approuver/rejeter
- [Phase 15]: Stateless URL query parameter handoff between RecusExtension and ComptesFournisseursExtension
- [Phase 15]: Forward-compatible AP link (404 acceptable if Phase 14 not yet deployed)

### Pending Todos

None yet.

### Blockers/Concerns

- v1.1 phases 6-9 not yet complete. v1.2 depends on v1.1 for UI infrastructure (Chart.js, design system).

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 11 | Fix dark mode compatibility, sidebar darkness, and header filter box colors on Fava built-in pages | 2026-02-26 | fa6e36d | [11-fix-font-and-color-issues-on-fava-built-](./quick/11-fix-font-and-color-issues-on-fava-built-/) |
| 12 | Research RBC bank connection options and security | 2026-02-26 | 258d79c | [12-research-rbc-bank-connection-options-sec](./quick/12-research-rbc-bank-connection-options-sec/) |
| 13 | Surface double-entry validation on dashboard | 2026-02-26 | 26ac262 | [13-document-and-surface-double-entry-valida](./quick/13-document-and-surface-double-entry-valida/) |
| 14 | Add Operations tab with all CLI commands as web UI | 2026-02-26 | 343e5ca | [14-add-operations-tab-with-all-cli-commands](./quick/14-add-operations-tab-with-all-cli-commands/) |
| 15 | Design AP/AR system for Quebec IT consulting | 2026-02-26 | 851fdc4 | [15-design-accounts-payable-and-accounts-rec](./quick/15-design-accounts-payable-and-accounts-rec/) |
| 16 | Design chat tab integration for discussions with Claude | 2026-02-26 | 9ca2b0b | [16-design-chat-tab-integration-for-discussi](./quick/16-design-chat-tab-integration-for-discussi/) |
| 17 | Add UI/UX design section to AP/AR design document | 2026-02-26 | 33fd206 | [17-add-ui-ux-design-section-to-ap-ar-design](./quick/17-add-ui-ux-design-section-to-ap-ar-design/) |
| 18 | Make ApprobationExtension table responsive with horizontal scroll | 2026-02-26 | 57430ec | [18-make-approbationextension-table-responsi](./quick/18-make-approbationextension-table-responsi/) |
| 19 | Reflect and improve Fava left sidebar grouping and default Operations landing view | 2026-04-04 | pending | [260404-gij-reflect-and-improve-fava-left-sidebar-gr](./quick/260404-gij-reflect-and-improve-fava-left-sidebar-gr/) |
| 20 | Investigate Fava/UI inconsistency for stale or missing ledger entries and apply minimal fix if needed | 2026-04-04 | pending | [260404-gga-investigate-fava-ui-inconsistency-for-st](./quick/260404-gga-investigate-fava-ui-inconsistency-for-st/) |

## Session Continuity

Last session: 2026-02-26
Stopped at: Completed 15-02-PLAN.md -- AR/AP match suggestions in approval queue (Phase 15 all plans complete, v1.2 milestone complete)
Resume file: None
