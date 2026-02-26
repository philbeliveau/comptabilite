# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Every dollar that flows through the corporation is correctly categorized, traceable to source documents, and ready for CPA review -- without manual data entry.
**Current focus:** Phase 10 in progress

## Current Position

Phase: 10 of 10 (Cross-Cutting Polish and Validation)
Plan: 2 of 2 in current phase (10-02 complete)
Status: Phase 10 COMPLETE -- v1.1 milestone complete
Last activity: 2026-02-26 - Completed quick task 16: Design chat tab integration

Progress: [####################] 75% (33/44 total plans -- 23 v1.0 complete, 10/10 v1.1)

## Performance Metrics

**Velocity:**
- Total plans completed: 23 (v1.0) + 14 quick tasks
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

*v1.1 metrics will populate as plans execute*
| Phase 07 P02 | 1min | 2 tasks | 2 files |
| Phase 08 P01 | 3min | 2 tasks | 5 files |
| Phase 08 P02 | 3min | 2 tasks | 3 files |
| Phase 09 P01 | 2min | 2 tasks | 3 files |
| Phase 09 P02 | 2min | 2 tasks | 2 files |
| Phase 10 P01 | 3min | 2 tasks | 1 files |
| Phase 10 P02 | 5min | 2 tasks | 8 files |

## Accumulated Context

### Decisions

All v1.0 decisions logged in PROJECT.md Key Decisions table (14 entries).
v1.1 decisions confirmed:
- Stay within Fava extension architecture (no custom frontend)
- Chart.js 4.4.8 UMD for data visualization (CDN lazy-loading, not bundled)
- Keep Quebec blue identity (#003DA5 palette)
- Custom rAF animation instead of CountUp.js (zero dependencies, native Intl.NumberFormat fr-CA)
- Chart registry Map with destroy-on-navigate lifecycle for SPA safety
- Fava CSS variable overrides on :root instead of !important escalation (81% reduction)
- Type scale based on 1.200 minor third ratio (--cqc-font-xs through --cqc-font-3xl)
- tabular-nums on all financial data elements for aligned money columns
- fava.beans.funcs.hash_entry with beancount fallback for entry context linking
- Revenue negation at computation time for clean data API
- Top 6 + Autres bucket for expense category doughnut chart
- Single-quote wrapping for data-chart JSON attributes to avoid double-quote escaping
- Server-rendered formatted values as no-JS fallback inside data-value elements
- Contextual CSS (.cqc-card-flush > .cqc-section-title) over wrapper div classes for template cleanliness
- Utility CSS classes (cqc-text-muted, cqc-cell-flex, cqc-col-checkbox) for template standardization
- AbortController pattern for SPA keyboard listener cleanup in ThemeQCExtension.js
- JSON endpoints on Fava extensions via @extension_endpoint for lightweight data APIs
- Sidebar badge with bfileSlug-relative URL for Fava multi-file routing
- XHR with FormData for upload progress (fetch lacks upload.onprogress)
- Lier button kept as form POST redirect for intentional page navigation
- dragCounter pattern for flicker-free drag-and-drop (simpler than relatedTarget)
- Blue palette for dragover state (green reserved for completion)
- HEIC treated as icon since browsers cannot render HEIC natively
- Sequential upload loop (not parallel) for clear per-file progress
- All font-size/font-weight values migrated to design system tokens (--cqc-font-*, --cqc-weight-*)
- :focus-visible (not :focus) for keyboard-only focus rings on interactive elements
- Firefox scrollbar-width: thin for sidebar, -webkit-backdrop-filter for Safari
- ARIA role=meter for confidence bars (semantic percentage indicator, not progressbar)
- aria-live=polite (not assertive) on sidebar badge to avoid interrupting screen reader flow
- Keyboard shortcuts kept as-is per research (no scoping change unless screen reader usage confirmed)
- Compute balance health from soldes dict (reuse calculer_soldes) rather than importing BalanceVerification -- simpler, avoids GIFI dependency
- Flat Passifs:ComptesFournisseurs (GIFI 2010) for AP -- solo consultant does not need sub-accounts
- Mirror existing Facture/RegistreFactures pattern for AP bill tracking (consistency over novelty)
- Per-line taux_itc/taux_itr for partial ITC/ITR eligibility (meals at 50%)
- Direct Anthropic API with tool_use over MCP subprocess for chat integration (simplicity for single-user)
- Disable lancer_paie in chat context for safety (payroll mutations require dedicated UI)
- sessionStorage for chat conversation persistence (stateless backend, no server-side sessions)

### Pending Todos

None yet.

### Blockers/Concerns

- Fava `<article>` replacement behavior needs runtime confirmation in Phase 6
- Chart.js canvas sizing resolved with .cqc-chart-container CSS (300px height, responsive canvas)
- Upload endpoint returns raw HTML -- RESOLVED in 09-01: converted to JSON via jsonify()

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 11 | Fix dark mode compatibility, sidebar darkness, and header filter box colors on Fava built-in pages | 2026-02-26 | fa6e36d | [11-fix-font-and-color-issues-on-fava-built-](./quick/11-fix-font-and-color-issues-on-fava-built-/) |
| 12 | Research RBC bank connection options and security | 2026-02-26 | 258d79c | [12-research-rbc-bank-connection-options-sec](./quick/12-research-rbc-bank-connection-options-sec/) |
| 13 | Surface double-entry validation on dashboard | 2026-02-26 | 26ac262 | [13-document-and-surface-double-entry-valida](./quick/13-document-and-surface-double-entry-valida/) |
| 14 | Add Operations tab with all CLI commands as web UI | 2026-02-26 | 343e5ca | [14-add-operations-tab-with-all-cli-commands](./quick/14-add-operations-tab-with-all-cli-commands/) |
| 15 | Design AP/AR system for Quebec IT consulting | 2026-02-26 | 851fdc4 | [15-design-accounts-payable-and-accounts-rec](./quick/15-design-accounts-payable-and-accounts-rec/) |
| 16 | Design chat tab integration for discussions with Claude | 2026-02-26 | 9ca2b0b | [16-design-chat-tab-integration-for-discussi](./quick/16-design-chat-tab-integration-for-discussi/) |

## Session Continuity

Last session: 2026-02-26
Stopped at: Completed quick task 16 -- Design chat tab integration
Resume file: N/A
