---
phase: 04-mcp-server-and-web-dashboard
plan: 01
subsystem: mcp
tags: [mcp, fastmcp, beancount, stdio, ledger-query, gst-qst, cca, shareholder-loan]

# Dependency graph
requires:
  - phase: 02-quebec-domain-logic
    provides: "Quebec domain modules (taxes, dpa, pret_actionnaire, paie)"
  - phase: 01-core-ledger-and-ingestion
    provides: "Beancount ledger, chart of accounts, rapports pattern"
provides:
  - "FastMCP server instance with stdio transport (7 query tools)"
  - "Shared service layer (services.py) for ledger operations"
  - "AppContext with read-only mode and reload()"
affects: [04-02, 04-03, 04-04, fava-extensions]

# Tech tracking
tech-stack:
  added: ["mcp>=1.25,<2"]
  patterns: ["FastMCP lifespan context injection", "Tool response truncation at 50 items", "French tool docstrings for Claude"]

key-files:
  created:
    - src/compteqc/mcp/__init__.py
    - src/compteqc/mcp/__main__.py
    - src/compteqc/mcp/server.py
    - src/compteqc/mcp/services.py
    - src/compteqc/mcp/tools/__init__.py
    - src/compteqc/mcp/tools/ledger.py
    - src/compteqc/mcp/tools/quebec.py
    - tests/test_mcp_server.py
  modified:
    - pyproject.toml
    - src/compteqc/quebec/pret_actionnaire/__init__.py

key-decisions:
  - "Beancount v3 parse_string is at beancount.parser.parser.parse_string (not beancount.parser)"
  - "Tool response cap at 50 items with tronque flag for pagination"
  - "French field names in all tool responses (comptes, solde, equilibre, tronque)"
  - "AppContext dataclass with reload() for in-memory ledger refresh after mutations"

patterns-established:
  - "MCP tool pattern: @mcp.tool() decorator with Context[ServerSession, AppContext] injection"
  - "Service layer pattern: pure functions in services.py called by both MCP tools and future Fava extensions"
  - "Read-only mode: COMPTEQC_READONLY env var checked in AppContext"

requirements-completed: [MCP-01, MCP-05, MCP-06]

# Metrics
duration: 4min
completed: 2026-02-19
---

# Phase 4 Plan 1: MCP Server Core and Query Tools Summary

**FastMCP server with 7 read-only query tools (4 ledger + 3 Quebec) exposing balances, trial balance, P&L, balance sheet, GST/QST, CCA, and shareholder loan via stdio**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-19T13:49:58Z
- **Completed:** 2026-02-19T13:54:26Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- MCP server starts via stdio with 7 query tools registered via FastMCP decorator API
- Shared service layer (services.py) provides calculer_soldes, lister_pending, formater_montant
- All tool responses are structured dicts with French field names and 50-item truncation
- Read-only mode via COMPTEQC_READONLY environment variable
- 12 tests passing covering services, AppContext, truncation, and read-only mode

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MCP server core with FastMCP lifespan and shared service layer** - `8d37464` (feat)
2. **Task 2: Implement ledger and Quebec query tools with read-only mode and tests** - `cd6b91e` (feat)

## Files Created/Modified
- `src/compteqc/mcp/server.py` - FastMCP instance, AppContext dataclass, app_lifespan context manager
- `src/compteqc/mcp/services.py` - Shared service layer (calculer_soldes, lister_pending, formater_montant)
- `src/compteqc/mcp/tools/ledger.py` - 4 ledger query tools (soldes_comptes, balance_verification, etat_resultats, bilan)
- `src/compteqc/mcp/tools/quebec.py` - 3 Quebec tools (sommaire_tps_tvq, etat_dpa, etat_pret_actionnaire)
- `src/compteqc/mcp/__init__.py` - MCP package marker
- `src/compteqc/mcp/__main__.py` - python -m entry point
- `src/compteqc/mcp/tools/__init__.py` - Tools subpackage marker
- `tests/test_mcp_server.py` - 12 tests for services, AppContext, truncation
- `pyproject.toml` - Added mcp>=1.25,<2 dependency
- `src/compteqc/quebec/pret_actionnaire/__init__.py` - Added obtenir_etat_pret export

## Decisions Made
- Beancount v3 parse_string lives at `beancount.parser.parser.parse_string` (not `beancount.parser`)
- Tool response cap at 50 items with `tronque` flag (prevents Claude context overflow)
- French field names throughout all tool responses for natural Claude interaction
- AppContext dataclass holds in-memory ledger state with reload() for post-mutation refresh

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed beancount.parser import path**
- **Found during:** Task 2 (tests)
- **Issue:** Plan referenced `beancount.parser.parse_string` which does not exist in Beancount v3; the correct import is `beancount.parser.parser.parse_string`
- **Fix:** Changed import to `from beancount.parser import parser as beancount_parser`
- **Files modified:** tests/test_mcp_server.py
- **Verification:** All 12 tests pass
- **Committed in:** cd6b91e (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Import path correction necessary for Beancount v3 compatibility. No scope creep.

## Issues Encountered
None beyond the import path deviation noted above.

## User Setup Required
None - no external service configuration required. MCP server can be registered with Claude Desktop/Code using:
```bash
claude mcp add compteqc -- uv run python -m compteqc.mcp.server
```

## Next Phase Readiness
- MCP server core ready for mutation tools (04-02: categorization, approval)
- Shared service layer ready for Fava extension reuse (04-03, 04-04)
- Read-only mode infrastructure in place for safe exploration

---
*Phase: 04-mcp-server-and-web-dashboard*
*Completed: 2026-02-19*
