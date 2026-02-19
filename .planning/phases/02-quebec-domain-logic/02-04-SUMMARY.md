---
phase: 02-quebec-domain-logic
plan: 04
subsystem: cca-and-shareholder-loan
tags: [cca, dpa, shareholder-loan, pret-actionnaire, s15-2, pydantic, beancount, yaml, freezegun]

requires:
  - phase: 01-ledger-foundation-and-import-pipeline
    provides: "Beancount ledger with French chart of accounts including Depenses:Amortissement, Actifs:Immobilisations, Passifs:Pret-Actionnaire"
provides:
  - "CCA pool-level calculation with half-year rule for 5 classes (8, 10, 12, 50, 54)"
  - "Asset registry with YAML persistence (RegistreActifs, Actif models)"
  - "Beancount CCA transaction generation with '!' review flag"
  - "Shareholder loan bidirectional tracking with FIFO repayment allocation"
  - "s.15(2) deadline alerts at 11 months, 9 months, and 30 days before inclusion"
  - "Circular loan-repayment-reborrow pattern detection"
affects: [05-cpa-export, cli-dpa-commands, cli-pret-actionnaire-commands]

tech-stack:
  added: [python-dateutil, freezegun]
  patterns: [pool-level CCA declining balance, FIFO loan repayment tracking, fiscal-year-based deadline calculation]

key-files:
  created:
    - src/compteqc/quebec/dpa/__init__.py
    - src/compteqc/quebec/dpa/classes.py
    - src/compteqc/quebec/dpa/registre.py
    - src/compteqc/quebec/dpa/calcul.py
    - src/compteqc/quebec/dpa/journal.py
    - src/compteqc/quebec/pret_actionnaire/__init__.py
    - src/compteqc/quebec/pret_actionnaire/suivi.py
    - src/compteqc/quebec/pret_actionnaire/alertes.py
    - src/compteqc/quebec/pret_actionnaire/detection.py
    - data/actifs.yaml
    - tests/test_dpa.py
    - tests/test_pret_actionnaire.py
  modified: []

key-decisions:
  - "CCA transactions use '!' flag (not '*') per discretion recommendation -- CPA should review whether to claim full, partial, or no CCA"
  - "s.15(2) inclusion date computed from fiscal year-end containing the advance, not from the advance date itself"
  - "FIFO repayment allocation for shareholder loan advances -- oldest advances cleared first for deadline tracking"
  - "Circularity detection uses 20% tolerance and 30-day window per s.15(2.6) guidance"

patterns-established:
  - "Pool-level CCA: individual assets tracked for reference, but CCA calculated at pool/class level per CRA rules"
  - "Decimal-only monetary values throughout DPA and loan modules (Pydantic float rejection on Actif model)"
  - "Graduated alert system: multiple urgency levels with specific time offsets from deadline"
  - "YAML persistence for asset registry (simple, version-controllable, human-readable)"

requirements-completed: [CCA-01, CCA-02, CCA-03, CCA-04, CCA-05, CCA-06, LOAN-01, LOAN-02, LOAN-03, LOAN-04]

duration: 5min
completed: 2026-02-19
---

# Phase 2 Plan 4: CCA/DPA and Shareholder Loan Summary

**Pool-level CCA depreciation for 5 asset classes with half-year rule, recapture/terminal loss, and shareholder loan monitoring with s.15(2) fiscal-year-based deadline alerts and circular pattern detection**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T12:49:47Z
- **Completed:** 2026-02-19T12:54:43Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments

- CCA pool-level calculation for classes 8, 10, 12, 50, 54 with correct declining balance rates, half-year rule on net additions, recapture, and terminal loss
- Asset registry with YAML persistence and Pydantic models (float rejection enforced)
- Beancount CCA transaction generation with `!` review flag and full metadata (classe, taux, UCC ouverture/fermeture)
- Shareholder loan bidirectional tracking with FIFO repayment allocation across individual advances
- s.15(2) deadline alerts graduated at 11 months, 9 months, and 30 days before inclusion date (computed from fiscal year-end, not loan date)
- Circular loan-repayment-reborrow pattern detection within 30-day window with 20% amount tolerance

## Task Commits

Each task was committed atomically:

1. **Task 1: Implementer le registre d'actifs, le calcul DPA par pool, et la generation de transactions Beancount** - `817158a` (feat)
2. **Task 2: Implementer le suivi du pret actionnaire avec alertes s.15(2) et detection de circularite** - `a8230bf` (feat)

## Files Created/Modified

- `src/compteqc/quebec/dpa/classes.py` - CCA class definitions (rates and descriptions for classes 8, 10, 12, 50, 54)
- `src/compteqc/quebec/dpa/registre.py` - Asset registry with Pydantic Actif model and YAML persistence
- `src/compteqc/quebec/dpa/calcul.py` - Pool-level CCA calculation with half-year rule, recapture, terminal loss
- `src/compteqc/quebec/dpa/journal.py` - Beancount transaction generation for CCA entries
- `src/compteqc/quebec/pret_actionnaire/suivi.py` - Shareholder loan state tracking with FIFO repayment
- `src/compteqc/quebec/pret_actionnaire/alertes.py` - s.15(2) deadline calculation and graduated alerts
- `src/compteqc/quebec/pret_actionnaire/detection.py` - Circular loan-repayment-reborrow pattern detection
- `data/actifs.yaml` - Empty initial asset registry
- `tests/test_dpa.py` - 15 tests covering CCA calculations, registry, and Beancount entries
- `tests/test_pret_actionnaire.py` - 12 tests covering loan tracking, alerts, and circularity detection

## Decisions Made

- **CCA `!` flag for discretionary review:** CCA is discretionary -- the taxpayer can claim full, partial, or no CCA. All generated transactions are flagged `!` (needs review) so the CPA can adjust the claim.
- **s.15(2) deadline from fiscal year-end:** The inclusion date is calculated as fiscal-year-end + 1 year, not advance-date + 1 year. This avoids Pitfall #4 from research -- a loan on Jan 5, 2026 with Dec 31 FYE has inclusion date Dec 31, 2027 (not Jan 5, 2027).
- **FIFO repayment allocation:** When partial repayments are made, they are applied to the oldest advances first. This matters because each advance has its own s.15(2) deadline.
- **Circularity tolerance at 20%:** s.15(2.6) anti-avoidance targets patterns where a repayment is immediately followed by a similar-amount re-borrowing. The 20% tolerance catches amounts that are close but not identical.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CCA module ready for CLI integration (`cqc dpa ajouter`, `cqc dpa calculer`, `cqc dpa journal`)
- Shareholder loan module ready for CLI integration (`cqc pret-actionnaire statut`, `cqc pret-actionnaire alertes`)
- Both modules produce pure Python data structures or Beancount transactions -- no side effects
- Dependencies `python-dateutil` and `freezegun` (dev) added to pyproject.toml

## Self-Check: PASSED

All 12 key files verified present. Both task commits (817158a, a8230bf) verified in git log. 27 tests passing (15 DPA + 12 pret actionnaire).

---
*Phase: 02-quebec-domain-logic*
*Completed: 2026-02-19*
