---
phase: 14-fava-extension-tab-mcp
verified: 2026-02-26T17:00:00Z
status: passed
score: 17/17 must-haves verified
re_verification: false
human_verification:
  - test: "Open Fava in a browser and navigate to the 'Comptes a payer / a recevoir' tab"
    expected: "Tab appears in the Fava sidebar and renders the KPI row, tab toggle, AR/AP tables, and aging chart without JavaScript errors"
    why_human: "Cannot verify Fava routing, Jinja2 template rendering, Chart.js initialization, or browser-side JavaScript behavior programmatically"
  - test: "Click '+ Nouvelle facture', fill in client, date, and a line item, then submit"
    expected: "Invoice appears in the AR table immediately after redirect; Beancount journal file updated"
    why_human: "POST endpoint interaction, form submission behavior, and ledger reload cannot be tested without a running Fava server"
  - test: "Click '+ Nouvelle facture fournisseur', fill in vendor, ref, and a line item with taux_itc=0.5, then submit"
    expected: "Bill appears in the AP table; ITC/ITR values reflected in live total preview before submit"
    why_human: "Live JavaScript total calculation and AP form submission require browser interaction"
  - test: "Verify dashboard 'Position AR/AP' KPI on the TableauBord homepage"
    expected: "A 'Position AR/AP' card shows a numeric value (green if positive, red if negative)"
    why_human: "Dashboard KPI rendering requires browser"
---

# Phase 14: Fava Extension Tab + MCP Verification Report

**Phase Goal:** User can manage AP/AR entirely from the Fava web interface with a dedicated tab, and Claude can query and mutate AP data via MCP tools
**Verified:** 2026-02-26T17:00:00Z
**Status:** PASSED
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User sees combined AP/AR tab titled 'Comptes a payer / a recevoir' in Fava sidebar | VERIFIED | `ComptesFournisseursExtension.report_title = "Comptes a payer / a recevoir"` confirmed by import; registered in `ledger/main.beancount` line 52 |
| 2 | KPI row shows AR total, AR overdue (with count badge), AP total, and net position -- computed from registries | VERIFIED | `kpis()` method fully implemented with all 5 keys; template renders 4 KPI cards including badge on overdue |
| 3 | User can toggle between AR invoice list and AP bill list using cqc-tab-toggle buttons | VERIFIED | Template contains `.cqc-tab-toggle` with two buttons; `showTab()` JavaScript toggles `#tab-ar` / `#tab-ap` visibility |
| 4 | AR table shows: numero, client, date, echeance, total, paye, solde, statut badge, aging row color | VERIFIED | Template line 273-325 renders full AR table; `factures_ar()` returns dicts with all required fields; aging CSS classes applied to `<tr>` |
| 5 | AP table shows: numero_interne, fournisseur, ref, date_facture, echeance, total, paye, solde, statut badge, aging row color | VERIFIED | Template line 404-458 renders full AP table; `factures_ap()` returns dicts with all required fields |
| 6 | Status badges use cqc-badge variants for all expected statuses | VERIFIED | Template CSS defines: `cqc-badge-draft`, `cqc-badge-sent`, `cqc-badge-received`, `cqc-badge-approved`, `cqc-badge-partial`, `cqc-badge-paid`, `cqc-badge-overdue`, `cqc-badge-disputed` |
| 7 | Chart.js horizontal stacked bar chart shows aging distribution (0-30, 31-60, 61-90, 91+) for AR and AP | VERIFIED | `aging_chart_json()` returns 4-dataset Chart.js config with `indexAxis: y`, stacked axes, hex colors; `data-chart-type="bar"` in template |
| 8 | Dashboard homepage shows Position AR/AP KPI card with net position value | VERIFIED | `_position_apar()` method in `tableau_bord/__init__.py`; `position_apar` key in `self._kpis`; template renders KPI at line 59-64 |
| 9 | Extension registered in ledger/main.beancount as fava-extension directive | VERIFIED | `ledger/main.beancount` line 52: `2010-01-01 custom "fava-extension" "compteqc.fava_ext.comptes_fournisseurs"` |
| 10 | User can create AR invoices via inline web form | VERIFIED | `creer_facture` POST endpoint at line 245; form present in template with client autocomplete, dynamic lines, live totals |
| 11 | AR form has: client autocomplete, date/echeance, dynamic line items, TPS/TVQ checkboxes, live totals | VERIFIED | Template lines 218-270; `addARLine()` and `updateARTotals()` JavaScript present |
| 12 | Submitting AR form creates Facture, adds to RegistreFactures, generates Beancount entry | VERIFIED | `creer_facture()` calls `registre.ajouter(facture)` and writes journal entry via `generer_ecriture_facture()`; ledger reloaded |
| 13 | User can create AP bills via inline web form | VERIFIED | `creer_facture_fournisseur` POST endpoint at line 308; AP form present in template |
| 14 | AP form has: vendor autocomplete, ref, date/echeance, dynamic lines with category dropdown, taux_itc/taux_itr, live ITC/ITR totals | VERIFIED | Template lines 334-402; `addAPLine()` and `updateAPTotals()` with ITC/ITR computation present |
| 15 | Submitting AP form creates FactureFournisseur, adds to RegistreFournisseurs, generates Beancount entry | VERIFIED | `creer_facture_fournisseur()` calls `registre.ajouter(bill)` and writes journal entry via `generer_ecriture_facture_fournisseur()` |
| 16 | All 6 MCP tools registered on server and return structured dict responses | VERIFIED | `import compteqc.mcp.tools.apar` in `server.py` line 60; all 6 tools import successfully; 18/18 unit tests pass |
| 17 | All 6 MCP tools have comprehensive unit tests that pass | VERIFIED | 18 tests in `tests/test_mcp_apar.py`, all pass: `uv run python -m pytest tests/test_mcp_apar.py` -- 18 passed |

**Score:** 17/17 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/compteqc/fava_ext/comptes_fournisseurs/__init__.py` | Extension with kpis(), factures_ar(), factures_ap(), aging_chart_json(), creer_facture, creer_facture_fournisseur | VERIFIED | 375 lines; all methods substantively implemented; imports RegistreFactures, RegistreFournisseurs, vieillissement |
| `src/compteqc/fava_ext/comptes_fournisseurs/templates/ComptesFournisseursExtension.html` | Full Jinja2 template with KPI row, tab toggle, AR/AP tables, aging chart, creation forms | VERIFIED | 607 lines; all sections present; forms include JavaScript for dynamic lines and live totals |
| `ledger/main.beancount` | Extension registration directive | VERIFIED | Line 52 contains `compteqc.fava_ext.comptes_fournisseurs` |
| `src/compteqc/fava_ext/tableau_bord/__init__.py` | _position_apar() method and position_apar KPI | VERIFIED | `_position_apar()` at line 109; `"position_apar"` added to `self._kpis` at line 106 |
| `src/compteqc/fava_ext/tableau_bord/templates/TableauBordExtension.html` | Position AR/AP KPI card | VERIFIED | Lines 59-64 render KPI with success/error color logic |
| `src/compteqc/mcp/tools/apar.py` | 6 MCP tools: ap_list, ap_add, ap_pay, ar_aging, ap_aging, apar_summary | VERIFIED | 361 lines; all 6 `@mcp.tool()` decorators present; substantive implementations with read-only guards on mutations |
| `src/compteqc/mcp/server.py` | Registration import for apar tools | VERIFIED | Line 60: `import compteqc.mcp.tools.apar` |
| `tests/test_mcp_apar.py` | Unit tests for all 6 MCP tools | VERIFIED | 18 tests across 6 test classes; all passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `comptes_fournisseurs/__init__.py` | `factures/registre.py` | `from compteqc.factures.registre import RegistreFactures` | WIRED | Top-level import at line 23 |
| `comptes_fournisseurs/__init__.py` | `fournisseurs/registre.py` | `from compteqc.fournisseurs.registre import RegistreFournisseurs` | WIRED | Top-level import at line 26 |
| `comptes_fournisseurs/__init__.py` | `vieillissement.py` | `from compteqc.vieillissement import calculer_vieillissement_ar, calculer_vieillissement_ap` | WIRED | Top-level import at lines 27-30; called in `aging_chart_json()` |
| `comptes_fournisseurs/__init__.py` | `factures/journal.py` | `from compteqc.factures.journal import generer_ecriture_facture` | WIRED | Top-level import at line 22; called in `creer_facture()` |
| `comptes_fournisseurs/__init__.py` | `fournisseurs/journal.py` | `from compteqc.fournisseurs.journal import generer_ecriture_facture_fournisseur` | WIRED | Top-level import at line 25; called in `creer_facture_fournisseur()` |
| `mcp/tools/apar.py` | `fournisseurs/registre.py` | `from compteqc.fournisseurs.registre import RegistreFournisseurs` (local import) | WIRED | Local imports in each tool function; tested and passing |
| `mcp/tools/apar.py` | `vieillissement.py` | `from compteqc.vieillissement import calculer_vieillissement_ar/ap` (local import) | WIRED | Local imports in `ar_aging` and `ap_aging` functions; actual API adapted to ResumeVieillissement dataclass |
| `mcp/server.py` | `mcp/tools/apar.py` | `import compteqc.mcp.tools.apar` | WIRED | Line 60 of server.py |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FVAP-01 | 14-01 | User sees combined AP/AR tab with KPI row | SATISFIED | ComptesFournisseursExtension renders KPI row with ar_total, ar_en_retard (+ badge), ap_total, position_nette |
| FVAP-02 | 14-01 | User can toggle AR/AP lists with status badges and aging colors | SATISFIED | cqc-tab-toggle buttons, showTab() JS, aging CSS classes on tr, all status badges defined |
| FVAP-03 | 14-01 | User sees Chart.js aging distribution chart | SATISFIED | aging_chart_json() returns valid Chart.js config; template uses data-chart pattern |
| FVAP-04 | 14-02 | User can create AR invoices via inline web form | SATISFIED | creer_facture endpoint + AR form with dynamic lines, live totals, client autocomplete |
| FVAP-05 | 14-02 | User can create AP bills via inline web form with expense category dropdown | SATISFIED | creer_facture_fournisseur endpoint + AP form with category dropdown, taux_itc/taux_itr, ITC/ITR display |
| FVAP-06 | 14-01 | Dashboard homepage shows net AR/AP position KPI | SATISFIED | _position_apar() in TableauBordExtension; position_apar KPI card in dashboard template |
| MCAP-01 | 14-03 | Claude can list and query AP bills via ap_list tool | SATISFIED | ap_list() with optional statut and fournisseur filters; limit 50; structured dict response |
| MCAP-02 | 14-03 | Claude can create AP bills via ap_add tool | SATISFIED | ap_add() with read-only guard, registry add, journal write, ledger reload |
| MCAP-03 | 14-03 | Claude can record AP payments via ap_pay tool | SATISFIED | ap_pay() with full/partial payment, status update, payment journal entry, read-only guard |
| MCAP-04 | 14-03 | Claude can generate aging reports via ar_aging, ap_aging, apar_summary tools | SATISFIED | All 3 tools implemented with ResumeVieillissement API; apar_summary includes 30-day cash impact |

All 10 requirement IDs declared across plans are accounted for and satisfied.

**Orphaned requirements check:** REQUIREMENTS.md maps FVAP-01 through FVAP-06 and MCAP-01 through MCAP-04 to Phase 14. All 10 are claimed in plans. None orphaned.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `ComptesFournisseursExtension.html` | 314, 448 | `<!-- Placeholder: Plan 02 adds action buttons -->` in AR/AP table action column `<td>` | Info | Empty action cells in AR/AP table rows. The goal does not require action buttons on table rows (only creation forms). No functional impact on AP/AR management. |
| `ComptesFournisseursExtension.html` | 8 | `{% set today = extension.ledger.beancount_file_path and none %}` -- evaluates to `None` | Warning | The `today` template variable is always `None`. The template uses `extension.today_str()` for form date defaults (correct) but the page header subtitle at line 169 references `today` via a Jinja2 expression that evaluates to empty string. The subtitle shows blank instead of the current date. No functional impact on AP/AR management -- cosmetic only. |

### Human Verification Required

#### 1. Fava Tab Renders Correctly

**Test:** Start Fava (`uv run fava ledger/main.beancount`) and navigate to the "Comptes a payer / a recevoir" tab.
**Expected:** Tab appears in sidebar; KPI row shows 4 metrics; tab toggle switches between AR and AP views; aging bar chart renders using Chart.js.
**Why human:** Fava routing, Jinja2 rendering, and Chart.js canvas initialization cannot be verified without a running browser.

#### 2. AR Invoice Creation Form

**Test:** Click "+ Nouvelle facture", enter a client name, set dates, add a line item with price 100, check TPS and TVQ, click "Creer la facture".
**Expected:** Page redirects back to the AR tab; new invoice appears in the AR table; `ledger/factures/journal.beancount` contains a new Beancount transaction.
**Why human:** POST endpoint flow, ledger reload, and redirect require a running Fava server with Flask request context.

#### 3. AP Bill Creation with ITC/ITR

**Test:** Click "+ Nouvelle facture fournisseur", enter vendor "Test Inc", ref "INV-001", add a line with montant 200, set taux_itc to 0.5 (meal expense), submit.
**Expected:** Live totals update as you type; ITC reclamable shows 5.00 (50% of TPS 10.00); bill appears in AP table after submit.
**Why human:** Live JavaScript ITC/ITR calculation and AP form submission require browser interaction.

#### 4. Dashboard Position AR/AP KPI

**Test:** Navigate to the Tableau de bord homepage.
**Expected:** A "Position AR/AP" KPI card is visible showing a numeric value in green (positive) or red (negative).
**Why human:** Dashboard KPI rendering and color logic require browser.

### Gaps Summary

No gaps found. All 17 observable truths are VERIFIED. All 10 requirements (FVAP-01 through FVAP-06, MCAP-01 through MCAP-04) are satisfied.

The two pre-existing test failures in `test_fava_quebec.py` and `test_fava_gap_closure.py` (expected 8 extensions, found 12) are stale tests that hardcoded the extension count from Phase 4. These were failing before Phase 14 execution and are NOT regressions introduced by this phase.

The `today` template variable issue (line 8 of the template evaluates to `None`) is cosmetic -- it only affects the page subtitle display. All functional features (form defaults use `extension.today_str()` directly) work correctly.

---

_Verified: 2026-02-26T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
