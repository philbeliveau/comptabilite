---
phase: 03-ai-categorization-and-review-workflow
plan: 02
subsystem: categorisation
tags: [anthropic, llm, structured-output, pending, jsonl, pipeline-integration, cli]

# Dependency graph
requires:
  - phase: 03-ai-categorization-and-review-workflow
    provides: "PipelineCategorisation, PredicteurML, DetecteurCAPEX, ClassificateurLLM Protocol"
  - phase: 01-foundation
    provides: "Beancount transaction model, MoteurRegles, ecrire_transactions, ajouter_include"
provides:
  - "ClassificateurLLM: Anthropic structured output classifier with JSONL logging"
  - "ResultatClassificationLLM: Pydantic response model for LLM output"
  - "ecrire_pending/lire_pending: pending.beancount staging with #pending tag"
  - "approuver_transactions/rejeter_transactions: pending workflow management"
  - "Full pipeline integration in import CLI (rules -> ML -> LLM -> route)"
affects: [03-03]

# Tech tracking
tech-stack:
  added: [anthropic]
  patterns: [structured-output-with-pydantic, jsonl-audit-log, pending-staging-with-tags, confidence-based-routing]

key-files:
  created:
    - src/compteqc/categorisation/llm.py
    - src/compteqc/categorisation/pending.py
    - tests/test_llm.py
    - tests/test_pending.py
  modified:
    - src/compteqc/categorisation/__init__.py
    - src/compteqc/cli/importer.py
    - pyproject.toml

key-decisions:
  - "Anthropic messages.parse() with Pydantic output_format for constrained structured output"
  - "beancount.parser.parse_string instead of loader.load_file for pending (avoids Open directive validation)"
  - "Lazy Anthropic client initialization to avoid import-time API key requirement"
  - "SHA-256 prompt hash (truncated to 16 chars) for log deduplication without storing full prompts"

patterns-established:
  - "Pending staging: #pending tag + metadata (source_ia, confiance, compte_propose)"
  - "JSONL audit log: timestamp, prompt_hash, model, tokens, response for drift detection"
  - "Import pipeline: extract -> pipeline.categoriser -> determiner_destination -> route"
  - "Graceful degradation: info messages for missing ML data or LLM key (never errors)"

requirements-completed: [CAT-03, CAT-06, CAT-08, CAT-11, CLI-02]

# Metrics
duration: 8min
completed: 2026-02-19
---

# Phase 03 Plan 02: LLM Classifier, Pending Staging, and Full Pipeline Import Summary

**Anthropic structured-output LLM classifier with JSONL audit logging, pending.beancount staging with #pending tags, and full 3-tier pipeline integration into the import CLI command**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-19T13:20:14Z
- **Completed:** 2026-02-19T13:28:33Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- ClassificateurLLM uses Anthropic messages.parse() with Pydantic ResultatClassificationLLM for constrained output
- All LLM interactions logged to JSONL with prompt hash, model, token usage, and timestamp for drift detection
- pending.beancount staging with #pending tag, AI metadata, CAPEX flags, and tier disagreement suggestions
- Import CLI runs full pipeline (rules -> ML -> LLM) and routes to direct/pending/revue based on confidence thresholds
- Graceful degradation: ML cold start and missing ANTHROPIC_API_KEY show info messages, never errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Create LLM classifier with structured output and JSONL logging** - `541341e` (feat)
2. **Task 2: Create pending file management and integrate full pipeline into import CLI** - `d204c2e` (feat)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified
- `src/compteqc/categorisation/llm.py` - ClassificateurLLM with Anthropic structured output, JSONL logging, graceful degradation
- `src/compteqc/categorisation/pending.py` - ecrire_pending, lire_pending, approuver_transactions, rejeter_transactions
- `tests/test_llm.py` - 11 tests for LLM classifier (all mocked, no real API calls)
- `tests/test_pending.py` - 15 tests for pending staging, approval, rejection
- `src/compteqc/categorisation/__init__.py` - Exports all pipeline classes
- `src/compteqc/cli/importer.py` - Full pipeline integration with tiered summary output
- `pyproject.toml` - Added anthropic dependency

## Decisions Made
- Used `messages.parse()` with Pydantic `output_format` (not tool_use or JSON mode) for cleanest structured output integration
- Used `beancount.parser.parse_string()` instead of `loader.load_file()` for reading pending.beancount -- the loader runs full validation including Open directive checks, which fails for a standalone file without account declarations
- Lazy client initialization (`_get_client()`) so that importing the module never requires ANTHROPIC_API_KEY
- SHA-256 prompt hash (16 chars) in JSONL log avoids storing full prompt text while enabling drift detection

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used parse_string instead of load_file for pending.beancount**
- **Found during:** Task 2 (pending tests)
- **Issue:** `loader.load_file()` validates accounts against Open directives, causing "unknown account" errors when reading pending.beancount as a standalone file
- **Fix:** Switched to `beancount.parser.parse_string()` which only parses syntax without semantic validation
- **Files modified:** src/compteqc/categorisation/pending.py
- **Verification:** All 15 pending tests pass including approve roundtrip
- **Committed in:** d204c2e (Task 2 commit)

**2. [Rule 1 - Bug] Test fixtures used non-existent account names**
- **Found during:** Task 2 (pending approval tests)
- **Issue:** Tests used `Depenses:Repas` and `Depenses:Transport` which don't exist in comptes.beancount (correct names: `Depenses:Repas-Representation`, `Depenses:Deplacement:Transport`)
- **Fix:** Updated test fixtures to use actual chart of accounts names
- **Files modified:** tests/test_pending.py
- **Verification:** Approval tests pass with real account names
- **Committed in:** d204c2e (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
- Pre-existing CLI import tests (`test_import_csv_cheques_reussit`, `test_import_cree_transactions_dans_ledger`) fail due to stale `include "2025/11.beancount"` in main.beancount -- not caused by this plan's changes. Verified failure exists on the previous commit as well.

## User Setup Required
- ANTHROPIC_API_KEY environment variable required for LLM tier (optional -- pipeline degrades gracefully without it)
- Source: Anthropic Console -> API Keys (https://console.anthropic.com/settings/keys)

## Next Phase Readiness
- Full pipeline operational: rules -> ML -> LLM with confidence routing
- Review workflow (03-03) can use lire_pending/approuver/rejeter for UI
- JSONL log ready for drift detection analysis
- Blocker note: Pre-existing CLI test failures should be addressed (stale 2025/11.beancount include)

---
*Phase: 03-ai-categorization-and-review-workflow*
*Completed: 2026-02-19*
