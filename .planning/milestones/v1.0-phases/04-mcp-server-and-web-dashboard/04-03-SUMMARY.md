---
phase: 04-mcp-server-and-web-dashboard
plan: 03
subsystem: ui
tags: [fava, beancount, extension, approval-queue, confidence-badges]

requires:
  - phase: 04-01
    provides: "MCP services layer (lister_pending, calculer_soldes)"
  - phase: 03-02
    provides: "Pending queue with AI categorization metadata"
provides:
  - "Fava web dashboard with approval queue extension"
  - "ApprobationExtension with batch approve/reject endpoints"
  - "Confidence badge rendering (elevee/moderee/revision)"
  - "$2,000 visual flagging guardrail"
affects: [04-04, 05-01]

tech-stack:
  added: [fava>=1.30]
  patterns: [fava-extension-endpoint, confidence-badge-levels, gros-montant-guardrail]

key-files:
  created:
    - src/compteqc/fava_ext/__init__.py
    - src/compteqc/fava_ext/approbation/__init__.py
    - src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html
    - tests/test_fava_ext.py
  modified:
    - pyproject.toml
    - ledger/main.beancount
    - src/compteqc/mcp/services.py

key-decisions:
  - "lister_pending supports both meta key conventions (confiance/source_ia and confidence/ai-source) for compatibility"
  - "niveau_confiance and est_gros_montant as module-level helpers for testability"
  - "Standard HTML form POST + redirect (no HTMX) per research recommendation"

patterns-established:
  - "Fava extension pattern: FavaExtensionBase subclass with extension_endpoint decorators"
  - "Confidence badge levels: elevee >= 0.95, moderee >= 0.80, revision < 0.80"
  - "Gros montant guardrail: > $2,000 requires explicit confirmation checkbox"

requirements-completed: [WEB-01, WEB-02, WEB-05]

duration: 3min
completed: 2026-02-19
---

# Phase 4 Plan 3: Fava Approval Queue Summary

**Fava extension with confidence-badge approval queue, batch approve/reject endpoints, and $2,000 guardrail**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-19T13:56:55Z
- **Completed:** 2026-02-19T14:00:32Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Fava installed and ApprobationExtension registered in main.beancount
- Approval queue with confidence badges (green/yellow/red) and AI source tags
- Batch approve/reject via HTML form POST with $2,000 confirmation guardrail
- 18 tests covering importability, badge logic, and gros montant flagging

## Task Commits

Each task was committed atomically:

1. **Task 1: Install Fava, configure extensions, create approval extension** - `b72dc28` (feat)
2. **Task 2: Test Fava extension importability and approval workflow** - `7b8651d` (test)

## Files Created/Modified
- `src/compteqc/fava_ext/__init__.py` - Package init for Fava extensions
- `src/compteqc/fava_ext/approbation/__init__.py` - ApprobationExtension with approve/reject endpoints, confidence helpers
- `src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html` - HTML template with badges, batch selection, source tags
- `tests/test_fava_ext.py` - 18 tests for extension, badge logic, and flagging
- `pyproject.toml` - Added fava>=1.30 dependency
- `ledger/main.beancount` - Registered fava-extension directive
- `src/compteqc/mcp/services.py` - Added compte_propose field and dual meta key support

## Decisions Made
- lister_pending now supports both `confiance`/`source_ia` (from pending.py) and `confidence`/`ai-source` (from MCP) meta key conventions
- niveau_confiance and est_gros_montant extracted as module-level helpers for direct testability without Fava server
- Standard HTML form POST + redirect pattern (no HTMX), following research recommendation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed lister_pending meta key mismatch and missing compte_propose**
- **Found during:** Task 1 (ApprobationExtension creation)
- **Issue:** lister_pending used `confidence`/`ai-source` meta keys but pending.py writes `confiance`/`source_ia`. Also missing `compte_propose` field needed by template.
- **Fix:** Support both key conventions with fallback, added compte_propose to output dict
- **Files modified:** src/compteqc/mcp/services.py
- **Verification:** Existing MCP tests (12) still pass, new tests (18) pass
- **Committed in:** b72dc28 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for correctness -- template needs compte_propose and correct meta keys. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Fava dashboard ready for visual verification when ledger has pending transactions
- Extension shares pending queue with MCP server via lister_pending service
- Ready for 04-04 (integration testing / polish)

---
*Phase: 04-mcp-server-and-web-dashboard*
*Completed: 2026-02-19*
