---
phase: 05-reporting-cpa-export-and-document-management
plan: 04
subsystem: documents
tags: [claude-vision, anthropic, pillow, receipt-ocr, beancount-document, matching]

# Dependency graph
requires:
  - phase: 03-ai-categorization-and-review-workflow
    provides: "Anthropic API patterns (lazy client, structured output)"
provides:
  - "DonneesRecu Pydantic model for structured receipt data"
  - "Receipt upload with image resize and file validation"
  - "Claude Vision extraction via tool_use structured output"
  - "Receipt-to-transaction matching by amount+date proximity"
  - "Beancount document directive generation and writing"
  - "CLI commands: cqc recu telecharger/lister/lier"
affects: [05-05, cpa-export]

# Tech tracking
tech-stack:
  added: [Pillow]
  patterns: [Claude Vision tool_use extraction, amount+date proximity matching]

key-files:
  created:
    - src/compteqc/documents/__init__.py
    - src/compteqc/documents/upload.py
    - src/compteqc/documents/extraction.py
    - src/compteqc/documents/matching.py
    - src/compteqc/documents/beancount_link.py
    - src/compteqc/cli/receipt.py
    - tests/test_documents.py
  modified:
    - src/compteqc/cli/app.py
    - pyproject.toml

key-decisions:
  - "Claude Vision tool_use for structured extraction (not messages.parse -- tool_use gives cleaner JSON)"
  - "Amount (60%) + date (40%) weighted scoring for receipt matching"
  - "Image resize to 1568px max via Pillow before sending to Claude Vision"
  - "Pillow added as project dependency for image processing"

patterns-established:
  - "Claude Vision tool_use: define tool schema from Pydantic model, force tool_choice"
  - "Receipt storage: ledger/documents/{YYYY}/{MM}/{date}.{vendor-slug}.{ext}"
  - "Proximity matching: linear decay scoring with configurable threshold"

requirements-completed: [DOC-01, DOC-02, DOC-03, DOC-04]

# Metrics
duration: 5min
completed: 2026-02-19
---

# Phase 5 Plan 4: Document Ingestion Summary

**Receipt upload pipeline with Claude Vision extraction, amount+date proximity matching, and Beancount document directives**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T14:45:56Z
- **Completed:** 2026-02-19T14:50:26Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Complete receipt ingestion pipeline: upload -> extract -> match -> link
- Claude Vision extracts vendor, date, subtotal, TPS, TVQ, total with confidence score
- Transaction matching scores by 60% amount proximity + 40% date proximity
- 15 tests all passing (upload, resize, matching, directive format, mocked extraction)

## Task Commits

Each task was committed atomically:

1. **Task 1: Receipt upload, AI extraction, and transaction matching** - `816eb8e` (feat)
2. **Task 2: Receipt CLI commands and tests** - `09142a3` (feat)

## Files Created/Modified
- `src/compteqc/documents/__init__.py` - Package init with public API exports
- `src/compteqc/documents/upload.py` - File validation, image resize, storage
- `src/compteqc/documents/extraction.py` - Claude Vision extraction with DonneesRecu model
- `src/compteqc/documents/matching.py` - Proximity matching with Correspondance model
- `src/compteqc/documents/beancount_link.py` - Document directive generation
- `src/compteqc/cli/receipt.py` - CLI commands (telecharger, lister, lier)
- `src/compteqc/cli/app.py` - Register receipt_app under 'recu'
- `tests/test_documents.py` - 15 tests covering all modules
- `pyproject.toml` - Added Pillow dependency

## Decisions Made
- Used Claude Vision `tool_use` pattern instead of `messages.parse()` -- tool_use provides cleaner structured JSON extraction directly from the model
- Matching weights: 60% amount + 40% date, with linear decay ($0.05-$5.00 for amount, 0-7 days for date)
- Image resize to 1568px max per Anthropic recommendation for cost/speed optimization
- Added Pillow as project dependency for image processing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added Pillow to pyproject.toml dependencies**
- **Found during:** Task 1 (Upload handler implementation)
- **Issue:** Pillow was available in the environment but not declared in pyproject.toml
- **Fix:** Added `"Pillow>=11"` to project dependencies
- **Files modified:** pyproject.toml
- **Verification:** `uv sync` succeeded, import works
- **Committed in:** 816eb8e (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential dependency declaration. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. ANTHROPIC_API_KEY must be set in .env for extraction (already configured from Phase 3).

## Next Phase Readiness
- Document pipeline complete, ready for CPA export integration
- Receipt data can be linked to transactions in Beancount ledger
- CLI provides full upload-extract-match-link workflow

---
*Phase: 05-reporting-cpa-export-and-document-management*
*Completed: 2026-02-19*
