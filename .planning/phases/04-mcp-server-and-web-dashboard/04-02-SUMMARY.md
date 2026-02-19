---
phase: 04-mcp-server-and-web-dashboard
plan: 02
subsystem: mcp
tags: [mcp, categorisation, approbation, paie, guardrail, mutation, fastmcp]

# Dependency graph
requires:
  - phase: 04-mcp-server-and-web-dashboard
    plan: 01
    provides: "FastMCP server, AppContext, 7 query tools, services layer"
  - phase: 03-ai-categorization-and-review-workflow
    provides: "PipelineCategorisation, pending.py (approve/reject), ResultatPipeline"
  - phase: 02-quebec-domain-logic
    provides: "calculer_paie, generer_transaction_paie, payroll domain"
provides:
  - "6 mutation MCP tools (proposer_categorie, lister_pending_tool, approuver_lot, rejeter, calculer_paie_tool, lancer_paie)"
  - "$2,000 guardrail on approuver_lot and lancer_paie"
  - "French reasoning in proposer_categorie response"
  - "Auto-approve for high-confidence low-amount transactions"
  - "Unified payroll confirmation guard with raison field"
  - "trouver_pending_par_id composite key lookup in services.py"
affects: [04-03, 04-04, fava-extensions]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Mutation tool pattern: check read_only, execute, reload()", "Composite key ID: date|payee|narration[:20]", "Unified confirmation guard with raison enum"]

key-files:
  created:
    - src/compteqc/mcp/tools/categorisation.py
    - src/compteqc/mcp/tools/approbation.py
    - src/compteqc/mcp/tools/paie.py
    - tests/test_mcp_mutations.py
  modified:
    - src/compteqc/mcp/server.py
    - src/compteqc/mcp/services.py

key-decisions:
  - "charger_regles() function instead of ConfigRegles.charger() (Pydantic model has no classmethod)"
  - "Composite key date|payee|narration[:20] for pending transaction identification"
  - "Auto-approve threshold: confiance >= 0.95, revue_obligatoire=False, abs(montant) <= 2000"
  - "Unified payroll confirmation with raison field: nouveau_montant, gros_montant, nouveau_et_gros_montant"

patterns-established:
  - "Mutation tool pattern: check read_only first, execute operation, call app.reload() after write"
  - "Confirmation guard pattern: return {status: confirmation_requise, raison, message, calcul} for user review"
  - "French error messages throughout all mutation tool responses"

requirements-completed: [MCP-02, MCP-03, MCP-04]

# Metrics
duration: 6min
completed: 2026-02-19
---

# Phase 4 Plan 2: MCP Mutation Tools Summary

**6 mutation MCP tools (categorization with French reasoning, batch approval with $2,000 guardrail, rejection with correction, payroll dry-run and write) bringing total to 13 tools**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-19T13:57:01Z
- **Completed:** 2026-02-19T14:03:05Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- 13 total MCP tools registered (7 query + 6 mutation) covering the full accounting workflow
- proposer_categorie with French reasoning, auto-approve for high-confidence low-amount transactions
- $2,000 guardrail on approuver_lot and lancer_paie with confirmation flow
- 18 mutation tests + 12 existing = 30 total MCP tests all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement categorization and approval MCP tools with $2,000 guardrail** - `2fdbb31` (feat)
2. **Task 2: Implement payroll MCP tools and write mutation tests** - `d1bc708` (feat)

## Files Created/Modified
- `src/compteqc/mcp/tools/categorisation.py` - proposer_categorie with pipeline integration, French reasoning, auto-approve
- `src/compteqc/mcp/tools/approbation.py` - lister_pending_tool, approuver_lot with $2,000 guardrail, rejeter with compte_corrige
- `src/compteqc/mcp/tools/paie.py` - calculer_paie_tool (dry-run), lancer_paie (write) with unified confirmation guard
- `src/compteqc/mcp/services.py` - Added trouver_pending_par_id for composite key lookup
- `src/compteqc/mcp/server.py` - Added imports for categorisation, approbation, paie tool modules
- `tests/test_mcp_mutations.py` - 18 tests covering all mutation tools, guardrails, read-only mode

## Decisions Made
- Used `charger_regles()` standalone function instead of `ConfigRegles.charger()` (Pydantic model, no classmethod)
- Composite key `date|payee|narration[:20]` matches existing dedup pattern from Phase 1
- Auto-approve bypasses pending queue when confiance >= 0.95, no revue_obligatoire, and montant <= $2,000
- Unified payroll confirmation with `raison` field distinguishing nouveau_montant, gros_montant, nouveau_et_gros_montant

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ConfigRegles.charger() to charger_regles()**
- **Found during:** Task 1 (categorisation tool)
- **Issue:** Plan referenced `ConfigRegles.charger()` but ConfigRegles is a Pydantic BaseModel without a `charger` classmethod; the actual function is `charger_regles()` in regles.py
- **Fix:** Changed to `from compteqc.categorisation.regles import ConfigRegles, charger_regles` and call `charger_regles(regles_path)`
- **Files modified:** src/compteqc/mcp/tools/categorisation.py
- **Verification:** Import succeeds, tests pass
- **Committed in:** d1bc708 (Task 2 commit, after test discovery)

**2. [Rule 1 - Bug] Fixed ConfigRegles constructor (no comptes_valides param)**
- **Found during:** Task 2 (tests)
- **Issue:** `ConfigRegles(regles=[], comptes_valides=set())` failed because ConfigRegles Pydantic model has no `comptes_valides` field
- **Fix:** Changed to `ConfigRegles(regles=[])` when no rules file exists
- **Files modified:** src/compteqc/mcp/tools/categorisation.py
- **Verification:** All 18 tests pass
- **Committed in:** d1bc708 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correct integration with existing categorisation module API. No scope creep.

## Issues Encountered
- Mock patching for proposer_categorie required patching at source module level (compteqc.categorisation.pipeline.PipelineCategorisation, compteqc.categorisation.moteur.MoteurRegles, compteqc.categorisation.capex.DetecteurCAPEX) rather than at the tool module level, because the tool uses local imports inside the function body

## User Setup Required
None - no external service configuration required. MCP mutation tools work with existing server setup.

## Next Phase Readiness
- 13 MCP tools cover full workflow: query ledger, categorize, review, approve/reject, run payroll
- Ready for Fava dashboard integration (04-03) and web UI (04-04)
- All tools enforce read-only mode and reload ledger after mutations

---
*Phase: 04-mcp-server-and-web-dashboard*
*Completed: 2026-02-19*
