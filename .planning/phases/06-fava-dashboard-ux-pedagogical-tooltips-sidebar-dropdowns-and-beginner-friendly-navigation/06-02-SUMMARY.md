---
phase: 06-fava-dashboard-ux-pedagogical-tooltips-sidebar-dropdowns-and-beginner-friendly-navigation
plan: 02
subsystem: ui
tags: [fava, javascript, tooltips, pedagogical, french-ux, accessibility, tabindex]

# Dependency graph
requires:
  - phase: 06-01
    provides: Tooltip CSS foundation ([data-tooltip]::after hover/focus), ThemeQCExtension.js onPageLoad() wiring
provides:
  - TOOLTIPS dictionary with 64 entries covering 6 report domains (Paie, TPS/TVQ, DPA/CCA, Pret actionnaire, Approbation, Native Fava)
  - attachTooltips() function with idempotent cleanup, KPI value label-based lookup, case-insensitive fallback, tabindex="0" for tablet accessibility
  - Full pedagogical tooltip system live on all report pages on every onPageLoad()
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sibling label lookup for KPI values: .cqc-kpi-value traverses to .closest('.cqc-kpi') then .querySelector('.cqc-kpi-label')"
    - "Case-insensitive fallback: exact match first, then toLowerCase() linear scan of TOOLTIPS keys"
    - "Single-line tooltip text with | Source: separator (CSS attr() does not support newlines)"
    - "Idempotent tooltip re-attachment: querySelectorAll('[data-tooltip]') + removeAttribute before each run"

key-files:
  modified:
    - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js

key-decisions:
  - "64 TOOLTIPS entries covering all 6 report domains, exceeding the 40+ plan requirement"
  - "KPI values use parent .cqc-kpi label textContent as lookup key (not the numeric value itself)"
  - "CSS tooltip uses single-line format with ' | Source: ' separator since CSS attr() has no newline support"
  - "Case-insensitive fallback match handles uppercase table headers (e.g., SALAIRE BRUT from CSS text-transform)"
  - "tabindex=0 on every tooltipped element for tablet focus/tap accessibility"
  - "Idempotent cleanup: querySelectorAll('[data-tooltip]') removes all existing attrs before re-attaching on each SPA navigation"

patterns-established:
  - "Domain-sectioned TOOLTIPS dictionary: group entries by report type with comments for maintainability"
  - "Dual-key entries: French canonical + common abbreviation (e.g., 'TPS payee' AND 'CTI') to match any UI variant"

requirements-completed: [UX-03, UX-04, UX-05]

# Metrics
duration: 3min
completed: 2026-02-20
---

# Phase 06 Plan 02: Pedagogical Tooltip Dictionary and Attachment Logic Summary

**64-entry TOOLTIPS dictionary with attachTooltips() covering all 6 report domains (Paie, TPS/TVQ, DPA/CCA, Pret actionnaire, Approbation, Native Fava) with KPI-label lookup, case-insensitive fallback, and tabindex=0 tablet accessibility**

## Performance

- **Duration:** ~3 min (code pre-implemented in prior session, this run: verification and documentation)
- **Started:** 2026-02-20T02:30:00Z
- **Completed:** 2026-02-20T02:33:00Z
- **Tasks:** 1 auto (complete) + 1 human-verify (documented below)
- **Files modified:** 1

## Accomplishments

- TOOLTIPS dictionary with 64 entries, organized by domain: Paie (22), TPS/TVQ (8), DPA/CCA (16), Pret actionnaire (7), Approbation (4), Native Fava (7)
- attachTooltips() function: idempotent cleanup, multi-selector querying, KPI-value sibling label lookup, case-insensitive fallback, tabindex=0 on every matched element
- Source attribution formatted as single-line " | Source: path.to.function()" for CSS attr() compatibility
- All tooltip text in beginner-level French with no unexplained jargon

## Task Commits

Task 1 was committed in a prior session:

1. **Task 1: TOOLTIPS dictionary and attachTooltips() function** - `fe78636` (feat)

**Plan metadata:** (this docs commit)

## Files Created/Modified

- `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` - Added TOOLTIPS dictionary (64 entries, lines 1259-1527), attachTooltips() function (lines 1533-1591), wired into onPageLoad() at line 1634

## Verification Results (Automated)

All automated checks passed:

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `grep -c "TOOLTIPS"` | >= 3 | 3 | PASS |
| `grep -c "attachTooltips"` | >= 2 | 2 | PASS |
| `grep -c "tabindex"` | >= 1 | 3 | PASS |
| TOOLTIPS entry count | >= 40 | 64 | PASS |
| Paie domain entries | >= 15 | 22 | PASS |
| TPS/TVQ domain entries | >= 6 | 8 | PASS |
| DPA/CCA domain entries | >= 12 | 16 | PASS |
| Pret actionnaire entries | >= 7 | 7 | PASS |
| Approbation entries | >= 4 | 4 | PASS |
| Native Fava entries | >= 6 | 7 | PASS |

## Decisions Made

- 64 TOOLTIPS entries organized in 6 domain sections with clear French comments; dual-key entries (canonical + abbreviation, e.g., "TPS payee" + "CTI") cover both label variants that may appear in the UI
- KPI value tooltip lookup uses parent `.cqc-kpi` container's `.cqc-kpi-label` text, since the value itself is a number with no semantic meaning for dictionary lookup
- CSS attr() does not support newlines, so source attribution uses " | Source: " inline separator instead of a second line
- Case-insensitive fallback scan (toLowerCase comparison) handles th elements that CSS has transformed to uppercase
- tabindex="0" on every data-tooltip element enables focus-triggered tooltip on tablets without mouse hover

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

---

## Task 2: Human Verification Checklist

**This task is a `checkpoint:human-verify`. Execute the steps below and confirm all pass.**

**To start Fava:**
```
cd /Users/philippebeliveau/Desktop/Notebook/comptabilite
uv run fava ledger/main.beancount
```
Then open: http://localhost:5000

---

### Sidebar verification (UX-01)

- [ ] Sidebar shows 4 collapsible French section headers: "Rapports financiers", "Donnees et documents", "Outils", "Extensions Quebec"
- [ ] Click a section header to collapse it -- the links underneath disappear
- [ ] Click again to expand -- the links reappear
- [ ] "Rapports financiers" and "Extensions Quebec" are open by default; "Donnees et documents" and "Outils" are closed by default

### Report headers verification (UX-02, UX-05)

- [ ] Click "Income Statement" -- a blue info block appears at the top of the article, explaining the report in French
- [ ] Click "Balance Sheet" -- its own French header block appears
- [ ] Click "Trial Balance" -- French header block appears
- [ ] Click "Journal" -- French header block appears
- [ ] Navigate to extension reports (Paie Quebec, TPS/TVQ, DPA/CCA, Pret actionnaire, etc.) -- each has its own unique French header block
- [ ] Read the text: is it clear to someone with no accounting background? (No unexplained jargon)

### Tooltips verification (UX-03, UX-04)

- [ ] On the Paie Quebec page, hover over a table column header (e.g., "Salaire brut") -- a dark tooltip appears with a French explanation
- [ ] The tooltip includes a "Source :" attribution at the end (e.g., "| Source : paie.moteur.calculer_paie().salaire_brut")
- [ ] Move the mouse away -- the tooltip disappears
- [ ] Hover over a KPI value (the big number) -- tooltip appears using the KPI label for lookup
- [ ] On the Trial Balance page, hover over a column header ("Account", "Balance", "Change") -- tooltips work on native Fava tables too
- [ ] In Chrome DevTools, toggle responsive/tablet mode and tap a table header -- tooltip shows via focus (tabindex=0)

### Style consistency (UX-04)

- [ ] Tooltips have a dark navy background (#0A1628) and white text
- [ ] Tooltip max-width is respected (long text wraps, does not overflow the viewport)
- [ ] Tooltip appears above the element with consistent styling across all reports
- [ ] The brand strip "Philippe Beliveau - CompteQC" appears below the Fava header bar
- [ ] No black overlap lines appear on any table rows (fix from quick-2 still active)

---

**When all checks pass, the Phase 06 UX overhaul (sidebar, report headers, pedagogical tooltips) is complete.**

## Next Phase Readiness

- All Phase 06 UX requirements (UX-01 through UX-05) implemented and verified (auto) or pending user visual confirmation (Task 2 above)
- No new phases planned -- this is the final phase (Phase 6 of 6)
- System is ready for ongoing bookkeeping use and CPA package generation

---
*Phase: 06-fava-dashboard-ux-pedagogical-tooltips-sidebar-dropdowns-and-beginner-friendly-navigation*
*Completed: 2026-02-20*

## Self-Check: PASSED

- [x] src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js exists
- [x] Commit fe78636 exists in git history (feat(06-02): add TOOLTIPS dictionary)
- [x] TOOLTIPS dictionary has 64 entries (verified via node script)
- [x] attachTooltips() called in onPageLoad() at line 1634
