---
phase: 14-fava-extension-tab-mcp
plan: 02
subsystem: ui
tags: [fava, jinja2, ap, ar, forms, post-endpoint, dynamic-lines, itc-itr]

requires:
  - phase: 14-fava-extension-tab-mcp
    plan: 01
    provides: "ComptesFournisseursExtension with expense_accounts(), client_names(), vendor_names() helpers"
  - phase: 11-ap-foundation
    provides: "FactureFournisseur model, RegistreFournisseurs, journal generator"
provides:
  - "creer_facture POST endpoint for AR invoice creation from web form"
  - "creer_facture_fournisseur POST endpoint for AP bill creation from web form"
  - "Inline AR form with client autocomplete, dynamic line items, live TPS/TVQ totals"
  - "Inline AP form with vendor autocomplete, expense category dropdown, taux_itc/taux_itr, live ITC/ITR totals"
  - "URL query parameter pre-fill hook for receipt-to-AP pipeline"
affects: [14-03, 15-receipt-to-ap]

tech-stack:
  added: []
  patterns: ["extension_endpoint POST with form parsing", "indexed dynamic form fields (name_0, name_1)", "URL prefill query params for cross-extension integration"]

key-files:
  created: []
  modified:
    - "src/compteqc/fava_ext/comptes_fournisseurs/__init__.py"
    - "src/compteqc/fava_ext/comptes_fournisseurs/templates/ComptesFournisseursExtension.html"

key-decisions:
  - "Form action URLs use /g.beancount_file_slug/extension/name/endpoint pattern (consistent with ApprobationExtension)"
  - "Dynamic line items use indexed form fields (description_0, description_1...) with while loop parsing"
  - "AP form includes taux_itc/taux_itr per-line for partial ITC/ITR eligibility (meals at 50%)"
  - "URL query parameter prefill hook (?prefill=1&fournisseur=X&montant=Y) for Phase 15 receipt-to-AP pipeline"

patterns-established:
  - "Indexed dynamic form fields: name_{idx} pattern for variable-length line items"
  - "Live totals JavaScript: updateARTotals/updateAPTotals with event delegation"
  - "toggleForm(id): reusable show/hide for inline card expansion"

requirements-completed: [FVAP-04, FVAP-05]

duration: 3min
completed: 2026-02-26
---

# Phase 14 Plan 02: AR/AP Inline Creation Forms Summary

**Inline AR invoice and AP bill creation forms with dynamic line items, live TPS/TVQ/ITC/ITR calculation, autocomplete, and POST endpoints that create registre entries and Beancount journal entries**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T16:35:26Z
- **Completed:** 2026-02-26T16:38:58Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- AR invoice creation form with client autocomplete, date/echeance, dynamic line items, TPS/TVQ checkboxes, live totals
- AP bill creation form with vendor autocomplete, expense category dropdown, taux_itc/taux_itr, live ITC/ITR calculation
- Two POST endpoints (creer_facture, creer_facture_fournisseur) that create registry entries and append Beancount journal entries
- URL query parameter pre-fill hook ready for Phase 15 receipt-to-AP pipeline

## Task Commits

Each task was committed atomically:

1. **Task 1: Add AR invoice creation form and POST endpoint** - `88cfd07` (feat)
2. **Task 2: Add AP bill creation form and POST endpoint** - `38f1636` (feat)

## Files Created/Modified
- `src/compteqc/fava_ext/comptes_fournisseurs/__init__.py` - Added creer_facture and creer_facture_fournisseur POST endpoints, today_str/echeance_default_str helpers, AP model imports
- `src/compteqc/fava_ext/comptes_fournisseurs/templates/ComptesFournisseursExtension.html` - Added AR and AP inline forms, form CSS, JavaScript for dynamic lines, live totals, and URL prefill

## Decisions Made
- Form action URLs use `/g.beancount_file_slug/extension/name/endpoint` pattern (consistent with existing ApprobationExtension and RecusExtension)
- Dynamic line items parsed via indexed form fields with while loop (description_0, description_1...)
- AP form includes per-line taux_itc/taux_itr fields for partial ITC/ITR eligibility
- URL query parameter prefill hook for stateless cross-extension form pre-population

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AR/AP creation forms fully functional in the Fava web interface
- URL prefill hook ready for Phase 15 receipt-to-AP pipeline integration
- Both forms use the toggleForm inline expansion pattern

---
*Phase: 14-fava-extension-tab-mcp*
*Completed: 2026-02-26*
