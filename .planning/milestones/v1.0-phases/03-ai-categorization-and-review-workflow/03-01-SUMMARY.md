---
phase: 03-ai-categorization-and-review-workflow
plan: 01
subsystem: categorisation
tags: [sklearn, svc, ml, capex, cca, pipeline, confidence-scoring]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "Beancount transaction model and MoteurRegles rule engine"
  - phase: 02-quebec-domain-logic
    provides: "CLASSES_DPA CCA class definitions"
provides:
  - "PredicteurML: sklearn SVC wrapper with probability-based confidence scoring"
  - "DetecteurCAPEX: amount threshold + vendor pattern CAPEX detection with CCA class suggestion"
  - "PipelineCategorisation: 3-tier cascade orchestrator (rules->ML->LLM) with threshold routing"
  - "ClassificateurLLM Protocol: interface for LLM tier (implemented in 03-02)"
  - "ResultatPipeline: unified result dataclass with confidence, source, CAPEX flags"
affects: [03-02, 03-03]

# Tech tracking
tech-stack:
  added: [smart-importer, scikit-learn, numpy, scipy]
  patterns: [sklearn-pipeline-svc-probability, tier-cascade-with-fallback, protocol-based-dependency-injection]

key-files:
  created:
    - src/compteqc/categorisation/ml.py
    - src/compteqc/categorisation/capex.py
    - src/compteqc/categorisation/pipeline.py
    - tests/test_pipeline.py
    - tests/test_capex.py
  modified:
    - pyproject.toml

key-decisions:
  - "Direct sklearn pipeline instead of smart_importer.EntryPredictor (too coupled to beangulp import workflow)"
  - "SVC(probability=True) for Platt scaling confidence scores"
  - "ClassificateurLLM as runtime_checkable Protocol for loose coupling with 03-02"
  - "CAPEX keyword-based CCA class suggestion (class 50 computers, 8 furniture, 10 vehicles, 12 software)"

patterns-established:
  - "Tier cascade: each tier only processes uncategorized remainder from previous tier"
  - "Confidence thresholds: <0.80 revue, 0.80-0.95 pending, >0.95 direct"
  - "CAPEX forces pending destination regardless of confidence level"
  - "Tier disagreement forces mandatory review with both suggestions preserved"

requirements-completed: [CAT-02, CAT-04, CAT-05, CAT-09]

# Metrics
duration: 4min
completed: 2026-02-19
---

# Phase 03 Plan 01: Three-Tier Categorization Pipeline Summary

**sklearn SVC pipeline with probability confidence scoring, CAPEX detector with CCA class suggestions, and 3-tier cascade orchestrator routing transactions to direct/pending/revue queues**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-19T13:13:45Z
- **Completed:** 2026-02-19T13:17:56Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- PredicteurML wraps sklearn SVC(probability=True) with cold start handling (MIN_TRAINING_SIZE=20, 2+ accounts)
- DetecteurCAPEX flags transactions by amount threshold ($500) and known vendor patterns with CCA class suggestions
- PipelineCategorisation cascades rules->ML->LLM with confidence-based routing and tier disagreement detection
- 29 TDD tests covering all pipeline, ML, and CAPEX logic

## Task Commits

Each task was committed atomically:

1. **Task 1: Install smart-importer and create ML wrapper** - `a933fde` (feat)
2. **Task 2: Create CAPEX detector and pipeline orchestrator** - `f29ca30` (feat)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified
- `src/compteqc/categorisation/ml.py` - PredicteurML with sklearn SVC(probability=True) confidence scoring
- `src/compteqc/categorisation/capex.py` - DetecteurCAPEX with amount/vendor/keyword CCA class detection
- `src/compteqc/categorisation/pipeline.py` - PipelineCategorisation 3-tier cascade orchestrator
- `tests/test_pipeline.py` - 17 tests for ML predictor and pipeline orchestrator
- `tests/test_capex.py` - 12 tests for CAPEX detection and CCA class suggestion
- `pyproject.toml` - Added smart-importer dependency

## Decisions Made
- Used direct sklearn pipeline (CountVectorizer + SVC) instead of subclassing smart_importer.EntryPredictor, which is too coupled to beangulp's import hook workflow for standalone use
- SVC(probability=True) enables Platt scaling for predict_proba() confidence scores
- ClassificateurLLM defined as a runtime_checkable Protocol for loose coupling -- Plan 03-02 implements the concrete class
- CAPEX CCA class suggestions use keyword matching against payee+narration text

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused make_union import**
- **Found during:** Task 2 verification (ruff lint)
- **Issue:** `make_union` imported but not used in ml.py
- **Fix:** Removed unused import
- **Files modified:** src/compteqc/categorisation/ml.py
- **Verification:** ruff check passes clean
- **Committed in:** f29ca30 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial lint fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Pipeline orchestrator ready for LLM tier integration (03-02) via ClassificateurLLM Protocol
- Review workflow (03-03) can use determiner_destination() for transaction routing
- smart_importer installed but not directly used (sklearn pipeline used instead due to beangulp coupling)
- Blocker note: smart_importer + Beancount v3 compatibility concern from STATE.md resolved -- we bypass smart_importer's import hook entirely

---
*Phase: 03-ai-categorization-and-review-workflow*
*Completed: 2026-02-19*
