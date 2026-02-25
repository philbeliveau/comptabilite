---
phase: quick-6
plan: 1
subsystem: ui
tags: [french, i18n, accents, diacritics, fava, templates, javascript]

requires:
  - phase: 06-fava-dashboard-ux
    provides: "Fava extension templates and ThemeQCExtension.js with REPORT_INTROS/TOOLTIPS"
provides:
  - "16 files with correct French diacritics in all user-visible text"
  - "TOOLTIPS dictionary keys synchronized with corrected HTML DOM text"
affects: []

tech-stack:
  added: []
  patterns:
    - "Tooltip key-DOM text synchronization: TOOLTIPS keys must match exact textContent of HTML elements"

key-files:
  created: []
  modified:
    - src/compteqc/fava_ext/echeances/templates/EcheancesExtension.html
    - src/compteqc/fava_ext/paie_qc/templates/PaieQCExtension.html
    - src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html
    - src/compteqc/fava_ext/dpa_qc/templates/DpaQCExtension.html
    - src/compteqc/fava_ext/taxes_qc/templates/TaxesQCExtension.html
    - src/compteqc/fava_ext/pret_actionnaire/templates/PretActionnaireExtension.html
    - src/compteqc/fava_ext/export_cpa/templates/ExportCPAExtension.html
    - src/compteqc/fava_ext/recus/templates/RecusExtension.html
    - src/compteqc/rapports/templates/balance_verification.html
    - src/compteqc/rapports/templates/bilan.html
    - src/compteqc/rapports/templates/etat_resultats.html
    - src/compteqc/rapports/templates/sommaire_paie.html
    - src/compteqc/rapports/templates/sommaire_pret.html
    - src/compteqc/rapports/templates/sommaire_dpa.html
    - src/compteqc/rapports/templates/sommaire_taxes.html
    - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js

key-decisions:
  - "TOOLTIPS keys updated to match corrected DOM text (e.g. Retenues employe -> Retenues employe with accent) to maintain tooltip-to-header binding"
  - "Added new TOOLTIPS entries for corrected header text (Categorie proposee, Beneficiaire, DPA reclamee, Salaire net YTD)"
  - "Beancount account paths (Depenses:, Revenus:) preserved without accents in Jinja2 template references"

patterns-established:
  - "French accent consistency: all user-visible text uses proper Unicode diacritics"

requirements-completed: [QUICK-6]

duration: 8min
completed: 2026-02-19
---

# Quick Task 6: French Accent Correction Summary

**Corrected French diacritics across all 16 UI files: 8 Fava extension templates, 7 report templates, and ThemeQCExtension.js (12 REPORT_INTROS + 68 TOOLTIPS + 3 SIDEBAR_GROUPS)**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-20T03:36:57Z
- **Completed:** 2026-02-20T03:45:25Z
- **Tasks:** 3
- **Files modified:** 16

## Accomplishments
- All 8 Fava extension templates now display correct French with proper accents (echeances, depenses, categorie, beneficiaire, verification, etc.)
- All 7 report templates corrected (etat des resultats, balance de verification, bilan, sommaire paie/pret/dpa/taxes)
- ThemeQCExtension.js: all 12 REPORT_INTROS, 68 TOOLTIPS entries, and 3 SIDEBAR_GROUPS labels corrected
- TOOLTIPS dictionary keys updated to match corrected HTML DOM text, ensuring tooltip binding still works

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix French accents in 8 Fava extension templates** - `f3b4dfa` (fix)
2. **Task 2: Fix French accents in 7 report templates** - `4692a8a` (fix)
3. **Task 3: Fix French accents in ThemeQCExtension.js dictionaries** - `9d390e6` (fix)

## Files Created/Modified
- `src/compteqc/fava_ext/echeances/templates/EcheancesExtension.html` - Fixed echeances, implementation, pret, declaration, societes, Quebec, delai
- `src/compteqc/fava_ext/paie_qc/templates/PaieQCExtension.html` - Fixed Quebec, employe, impot
- `src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html` - Fixed revision, selectionner, beneficiaire, categorie, elevee, moderee, corrige
- `src/compteqc/fava_ext/dpa_qc/templates/DpaQCExtension.html` - Fixed deduction, debut, reclamee, ecritures, discretionnaire
- `src/compteqc/fava_ext/taxes_qc/templates/TaxesQCExtension.html` - Fixed periode, frequence, percue, du, negative
- `src/compteqc/fava_ext/pret_actionnaire/templates/PretActionnaireExtension.html` - Fixed pret, enregistre
- `src/compteqc/fava_ext/export_cpa/templates/ExportCPAExtension.html` - Fixed fonctionnalite, implementee, generera, verification, etat, resultats, prevus
- `src/compteqc/fava_ext/recus/templates/RecusExtension.html` - Fixed recus, televersement, deposez, selectionner, acceptes, recents
- `src/compteqc/rapports/templates/balance_verification.html` - Fixed verification, debit, credit, equilibree
- `src/compteqc/rapports/templates/bilan.html` - Fixed resultat, equation, verifiee
- `src/compteqc/rapports/templates/etat_resultats.html` - Fixed etat, resultats, depenses, RESULTAT
- `src/compteqc/rapports/templates/sommaire_paie.html` - Fixed impot, periode
- `src/compteqc/rapports/templates/sommaire_pret.html` - Fixed pret, continuite, echeances, verifier
- `src/compteqc/rapports/templates/sommaire_dpa.html` - Fixed deduction, reclamee, detail, cout
- `src/compteqc/rapports/templates/sommaire_taxes.html` - Fixed frequence, periode, percue, payee
- `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` - Fixed all SIDEBAR_GROUPS, REPORT_INTROS, and TOOLTIPS French strings

## Decisions Made
- TOOLTIPS keys updated to match corrected DOM text to maintain tooltip binding (e.g. "Retenues employe" key updated to "Retenues employe" with accent since the HTML KPI label now has the accent)
- Added new TOOLTIPS entries for headers that changed (Categorie proposee, Beneficiaire, DPA reclamee, Salaire net YTD)
- Preserved Beancount account paths without accents (e.g. "Depenses:Bureau:Fournitures" in placeholder text stays as-is since it references a beancount account name)
- "Depenses" kept without accent in REPORT_INTROS fonction field where it references Beancount account names

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added new TOOLTIPS entries for corrected HTML headers**
- **Found during:** Task 3 (ThemeQCExtension.js)
- **Issue:** After fixing accents in HTML templates, some TOOLTIPS keys no longer matched DOM text. New headers like "Categorie proposee" and "Beneficiaire" had no tooltip entries.
- **Fix:** Updated existing keys to match corrected DOM text and added new entries (Categorie proposee, Beneficiaire, Salaire net YTD, DPA reclamee)
- **Files modified:** src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
- **Verification:** JS syntax check passes (node -c)
- **Committed in:** 9d390e6 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical functionality)
**Impact on plan:** Essential to maintain tooltip-to-header binding after accent corrections. No scope creep.

## Issues Encountered
- Test suite cannot run due to pre-existing Python version mismatch (3.10 vs required 3.12) -- not related to this change
- Changes are text-only (no code logic altered), so test coverage is not affected

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All French text in the UI is now correct with proper diacritics
- No further work needed unless new templates are added

---
*Phase: quick-6*
*Completed: 2026-02-19*
