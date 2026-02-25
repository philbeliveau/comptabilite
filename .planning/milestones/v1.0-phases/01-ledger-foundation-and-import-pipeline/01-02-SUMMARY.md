---
phase: 01-ledger-foundation-and-import-pipeline
plan: 02
subsystem: ingestion
tags: [beancount, beangulp, ofxtools, csv, pydantic, yaml, categorisation]

requires:
  - phase: 01-01
    provides: "Python project structure, Beancount ledger with French accounts, TransactionNormalisee model"
provides:
  - "RBC chequing CSV importer (RBCChequesImporter)"
  - "RBC credit card CSV importer (RBCCarteImporter)"
  - "RBC OFX/QFX importer with FITID deduplication (RBCOfxImporter)"
  - "YAML rule-based categorisation engine (MoteurRegles)"
  - "Immutable transaction categorisation function (appliquer_categorisation)"
  - "Normalisation utilities (beneficiary cleanup, encoding detection, file archival)"
  - "Pydantic models for rule validation (ConfigRegles, Regle, ConditionRegle)"
affects: [01-03, 03-categorization, 05-cpa-export]

tech-stack:
  added: [ofxtools, pyyaml, beangulp]
  patterns: [beangulp.Importer subclass, Decimal-only amounts, FITID dedup for OFX, date+montant+narration dedup for CSV, immutable transaction transformation]

key-files:
  created:
    - src/compteqc/ingestion/normalisation.py
    - src/compteqc/ingestion/rbc_cheques.py
    - src/compteqc/ingestion/rbc_carte.py
    - src/compteqc/ingestion/rbc_ofx.py
    - src/compteqc/categorisation/moteur.py
    - src/compteqc/categorisation/regles.py
    - rules/categorisation.yaml
    - tests/fixtures/rbc_cheques_sample.csv
    - tests/fixtures/rbc_carte_sample.csv
    - tests/fixtures/rbc_sample.ofx
    - tests/test_importers.py
    - tests/test_categorisation.py
  modified:
    - src/compteqc/ingestion/__init__.py
    - src/compteqc/categorisation/__init__.py

key-decisions:
  - "Credit card sign convention: CSV positive amounts (purchases) become negative on carte account (credit) and positive on expense (debit)"
  - "Deduplication strategy differs by format: FITID for OFX, date+montant+narration[:20] for CSV"
  - "Carte credit dedup uses contrepartie posting (index 1) amount to match CSV original sign"
  - "Empty categorisation rules file (regles: []) per user decision to build rules incrementally"
  - "appliquer_categorisation creates new Transaction instances instead of mutating originals"

patterns-established:
  - "beangulp.Importer subclass with identify/account/extract for each bank format"
  - "Two-posting transactions: bank account + Depenses:Non-Classe with flag ! for review"
  - "Metadata on every transaction: source, categorisation, fichier_source"
  - "FITID metadata on OFX transactions for cross-import deduplication"
  - "MoteurRegles validates compte against comptes_valides set, never invents accounts"
  - "File archival with SHA-256 hash and .meta.json sidecar"

requirements-completed: [INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, CAT-01]

duration: 6min
completed: 2026-02-19
---

# Phase 1 Plan 2: RBC Importers and Categorisation Engine Summary

**Three RBC importers (CSV cheques, CSV carte credit, OFX) with FITID/signature deduplication, and YAML rule-based categorisation engine with immutable transaction transformation**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-19T12:21:05Z
- **Completed:** 2026-02-19T12:27:07Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments

- Three bank importers parsing RBC files into Beancount transactions with Decimal amounts, 2 balanced postings, and deduplication
- OFX importer using ofxtools with FITID-based deduplication for cross-import duplicate detection
- YAML rule-based categorisation engine that validates accounts against the ledger and never invents categories
- 64 passing tests covering identify, extract, deduplication, sign conventions, categorisation, and immutability

## Task Commits

Each task was committed atomically:

1. **Task 1: Construire les importateurs CSV RBC (cheques et carte credit) avec normalisation** - `a80bee8` (feat)
2. **Task 2: Construire l'importateur OFX et le moteur de categorisation par regles YAML** - `928b043` (feat)

## Files Created/Modified

- `src/compteqc/ingestion/normalisation.py` - Beneficiary cleanup, encoding detection, file archival with SHA-256
- `src/compteqc/ingestion/rbc_cheques.py` - RBC chequing CSV importer (RBCChequesImporter)
- `src/compteqc/ingestion/rbc_carte.py` - RBC credit card CSV importer (RBCCarteImporter)
- `src/compteqc/ingestion/rbc_ofx.py` - RBC OFX/QFX importer with FITID dedup (RBCOfxImporter)
- `src/compteqc/categorisation/moteur.py` - Rule engine with regex patterns, amount bounds, account validation
- `src/compteqc/categorisation/regles.py` - Pydantic models for YAML rules and charger_regles() loader
- `src/compteqc/categorisation/__init__.py` - appliquer_categorisation() immutable transformer
- `src/compteqc/ingestion/__init__.py` - Module exports for all three importers
- `rules/categorisation.yaml` - Empty rules file ready for user population
- `tests/fixtures/rbc_cheques_sample.csv` - 8-transaction RBC chequing fixture
- `tests/fixtures/rbc_carte_sample.csv` - 8-transaction RBC credit card fixture
- `tests/fixtures/rbc_sample.ofx` - 6-transaction OFX v1 SGML fixture
- `tests/test_importers.py` - 47 tests for all three importers + normalisation
- `tests/test_categorisation.py` - 17 tests for rule engine + appliquer_categorisation

## Decisions Made

- **Credit card sign convention:** RBC CSV uses positive for purchases, negative for payments. In double-entry, purchases credit the carte account (negative posting) and debit the expense (positive posting). The dedup signature builder uses the contrepartie posting to match CSV original sign.
- **Deduplication strategy:** OFX uses FITID (bank-provided unique ID, 100% reliable). CSV uses date + montant + first 20 chars of narration (heuristic but effective for same-file reimports).
- **Empty rules by default:** Per user decision to build categorisation rules incrementally from real imports rather than pre-loading assumptions.
- **Immutable categorisation:** appliquer_categorisation creates new Transaction instances rather than mutating originals, enabling safe replay and undo.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Credit card dedup signature mismatch**
- **Found during:** Task 1 (RBCCarteImporter)
- **Issue:** Dedup failed on re-import because `_construire_signatures_existantes` read posting[0] (carte account, negated amount) while extract() signed with CSV original amount
- **Fix:** Changed `_construire_signatures_existantes` to use posting[1] (contrepartie) which matches the CSV original sign
- **Files modified:** `src/compteqc/ingestion/rbc_carte.py`
- **Verification:** test_deduplication_meme_fichier passes (0 dupes on re-import)
- **Committed in:** `a80bee8` (Task 1 commit)

**2. [Rule 1 - Bug] Unused import in rbc_cheques.py**
- **Found during:** Task 1 (ruff check)
- **Issue:** `import re` was unused (regex handled in normalisation module)
- **Fix:** Removed unused import
- **Files modified:** `src/compteqc/ingestion/rbc_cheques.py`
- **Verification:** `ruff check` passes
- **Committed in:** `a80bee8` (Task 1 commit)

**3. [Rule 1 - Bug] Beancount data.D() is for Decimal, not dates**
- **Found during:** Task 2 (test_categorisation.py)
- **Issue:** Used `data.D("2026-01-15")` in tests, but in beancount v3, `D()` converts strings to Decimal, not dates
- **Fix:** Changed to `datetime.date(2026, 1, 15)` for date construction in tests
- **Files modified:** `tests/test_categorisation.py`
- **Verification:** All 64 tests pass
- **Committed in:** `928b043` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (3 bugs)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three RBC importers ready for real bank files (CSV and OFX)
- Categorisation engine ready to process rules once user populates rules/categorisation.yaml
- Pipeline flow established: import -> extract -> categorise -> post to ledger (01-03 will wire these together with CLI)
- File archival utility ready for tracking imported source files

## Self-Check: PASSED

All 14 key files verified present. Both task commits (a80bee8, 928b043) verified in git log.

---
*Phase: 01-ledger-foundation-and-import-pipeline*
*Completed: 2026-02-19*
