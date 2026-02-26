---
phase: 14-fava-extension-tab-mcp
plan: 03
subsystem: api
tags: [mcp, ap, ar, aging, fastmcp, beancount]

# Dependency graph
requires:
  - phase: 11-ap-foundation
    provides: "FactureFournisseur, RegistreFournisseurs, journal entry generators"
  - phase: 12-aging-ar-cli
    provides: "vieillissement module with calculer_vieillissement_ar/ap, ResumeVieillissement"
provides:
  - "6 MCP tools for AP/AR management: ap_list, ap_add, ap_pay, ar_aging, ap_aging, apar_summary"
  - "Claude can query and mutate AP data and generate aging reports via MCP"
affects: [14-fava-extension-tab-mcp]

# Tech tracking
tech-stack:
  added: []
  patterns: ["MCP tool with local imports for lazy loading", "Patch __init__/methods for testing local-import MCP tools"]

key-files:
  created:
    - src/compteqc/mcp/tools/apar.py
    - tests/test_mcp_apar.py
  modified:
    - src/compteqc/mcp/server.py

key-decisions:
  - "Adapted aging tools to use list-based API (calculer_vieillissement_ar/ap accept lists, return ResumeVieillissement) rather than passing registries directly"
  - "Used local imports in tool functions for lazy loading, consistent with existing MCP tool pattern"
  - "Patched __init__ and methods on registry classes for test mocking instead of module-level patch (local imports not patchable at module level)"

patterns-established:
  - "MCP AP/AR tool pattern: local imports, structured dict returns, read-only guard on mutations"

requirements-completed: [MCAP-01, MCAP-02, MCAP-03, MCAP-04]

# Metrics
duration: 5min
completed: 2026-02-26
---

# Phase 14 Plan 03: AP/AR MCP Tools Summary

**6 MCP tools for AP/AR management: bill listing/creation/payment and AR/AP aging reports with combined cash position summary**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-26T16:26:55Z
- **Completed:** 2026-02-26T16:32:49Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created 6 MCP tools (ap_list, ap_add, ap_pay, ar_aging, ap_aging, apar_summary) enabling Claude to manage AP/AR data conversationally
- All mutation tools (ap_add, ap_pay) include read-only mode guard, journal entry generation, and ledger reload
- Comprehensive test suite with 18 unit tests all passing, no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ap_list, ap_add, ap_pay MCP tools** - `6da1b15` (feat)
2. **Task 2: Create ar_aging, ap_aging, apar_summary MCP tools and tests** - `1331125` (feat)

## Files Created/Modified
- `src/compteqc/mcp/tools/apar.py` - 6 MCP tools for AP/AR management with French docstrings
- `src/compteqc/mcp/server.py` - Registration import for apar tools module
- `tests/test_mcp_apar.py` - 18 unit tests covering all 6 tools

## Decisions Made
- Adapted aging tools to use the actual vieillissement module API (list-based, returns ResumeVieillissement dataclass) rather than the plan's dict-based approach
- Used patch on __init__ and methods of registry classes for testing, since local imports in tool functions cannot be patched at module level
- Added start value of Decimal("0") to sum() calls in apar_summary to avoid empty sequence errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adapted aging tool API to match actual vieillissement module**
- **Found during:** Task 2
- **Issue:** Plan assumed aging functions accept registries and return dicts. Actual API accepts lists and returns ResumeVieillissement dataclass.
- **Fix:** Changed ar_aging/ap_aging to pass registre.lister() result and access .totaux_par_tranche/.total_impaye/.nombre_total
- **Files modified:** src/compteqc/mcp/tools/apar.py
- **Committed in:** 1331125

**2. [Rule 1 - Bug] Fixed test mocking strategy for local imports**
- **Found during:** Task 2
- **Issue:** @patch on module-level attributes failed because tool functions use local imports (names not on module)
- **Fix:** Patched __init__ and methods on the actual registry classes instead of module-level names
- **Files modified:** tests/test_mcp_apar.py
- **Committed in:** 1331125

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 6 MCP tools registered and functional
- Claude can now list AP bills, create bills, record payments, and generate aging reports via MCP
- Ready for Fava extension integration (chat tab can invoke these tools)

---
*Phase: 14-fava-extension-tab-mcp*
*Completed: 2026-02-26*
