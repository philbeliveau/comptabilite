---
phase: 12-aging-ar-cli
verified: 2026-02-26T16:30:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Run cqc fournisseur add interactively"
    expected: "Prompts for vendor name, reference, description, amount, expense category, due date, and TPS/TVQ flags; creates bill; prints Beancount journal entry preview"
    why_human: "Interactive prompt flow requires terminal input; cannot verify prompt sequence programmatically"
  - test: "Run cqc aging ar and cqc aging ap in a terminal with data"
    expected: "Rich table with color-coded rows (green=0-30, yellow=31-60, dark_orange=61-90, red=91+) followed by per-bucket summary section"
    why_human: "Color rendering and Rich table layout require visual inspection"
  - test: "Run cqc aging summary with mixed AR/AP data"
    expected: "Formatted position block showing AR total, AP total, net position (green if positive, red if negative), and 30-day cash flow section"
    why_human: "Formatted output layout and color logic require visual inspection"
---

# Phase 12: aging-ar-cli Verification Report

**Phase Goal:** AR enhancements (partial payments, aging), AP CLI, aging reports CLI
**Verified:** 2026-02-26T16:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can record a partial payment on an invoice and the running balance (solde) decreases by the payment amount | VERIFIED | `Facture.montant_paye` field + `solde` property confirmed working; `RegistreFactures.enregistrer_paiement()` adds to existing montant_paye and recomputes status; 6 tests pass in `test_factures_modeles.py` |
| 2 | Invoice status automatically derives to PARTIAL when montant_paye > 0 but < total, PAID when fully paid, OVERDUE when past due and unpaid | VERIFIED | `determiner_statut()` function in `modeles.py` lines 132-165 implements all 5 transitions; 5 dedicated tests in `TestDeterminerStatut` all pass |
| 3 | Each invoice line item can specify a revenue account instead of hardcoded Revenus:Consultation | VERIFIED | `LigneFacture.compte_revenu` field (line 42) defaults to `"Revenus:Consultation"`, accepts any string; `generer_ecriture_facture()` groups by `compte_revenu` using `defaultdict`; 4 tests pass |
| 4 | AR aging report calculates invoices into 0-30, 31-60, 61-90, 91+ day buckets based on date_echeance | VERIFIED | `calculer_vieillissement_ar()` in `vieillissement.py` lines 94-131; all 4 bucket functions verified; 5 AR tests pass |
| 5 | AP aging report calculates vendor bills into 0-30, 31-60, 61-90, 91+ day buckets based on date_echeance | VERIFIED | `calculer_vieillissement_ap()` in `vieillissement.py` lines 134-171; 2 AP tests pass |
| 6 | Combined AP/AR summary shows total AR outstanding, total AP outstanding, and net position (AR - AP) | VERIFIED | `rapport_position_apar()` lines 174-192 computes `position_nette = ar.total_impaye - ap.total_impaye` plus `encaissements_30j`, `paiements_30j`, `flux_net_30j`; 2 position tests pass |
| 7 | User can run `cqc fournisseur add` to create a vendor bill with Beancount journal entry | VERIFIED | `fournisseur.py` command `add` (lines 75-152) imports `generer_ecriture_facture_fournisseur` and calls `_appendice_beancount()`; module loads cleanly |
| 8 | User can run `cqc fournisseur list` with optional --statut filter | VERIFIED | `lister()` command (lines 155-209) passes `BillStatus` filter to `registre.lister()`; Rich table has all 9 required columns |
| 9 | User can run `cqc fournisseur pay NUMERO` for full or partial payment with Beancount entry | VERIFIED | `payer()` command (lines 265-355) handles both full (solde as default) and partial (--montant) payments; validates overpayment; generates Beancount entry via `generer_ecriture_paiement_fournisseur()` |
| 10 | User can run `cqc aging ar` to see AR invoices grouped into aging buckets | VERIFIED | `aging_ar()` command in `aging.py` (lines 93-144) loads `RegistreFactures`, calls `calculer_vieillissement_ar()`, renders Rich table with 9 columns and per-bucket summary |
| 11 | User can run `cqc aging ap` to see AP bills grouped into aging buckets | VERIFIED | `aging_ap()` command (lines 147-205) mirrors AR command with `RegistreFournisseurs` and `calculer_vieillissement_ap()` |
| 12 | User can run `cqc aging summary` to see combined AR/AP position with net cash impact | VERIFIED | `aging_summary()` command (lines 208-266) calls both aging functions and `rapport_position_apar()`; prints formatted block with net position and 30-day cash flow |
| 13 | User can run `cqc facture lister --statut partial` or `--statut overdue` to filter by new status values | VERIFIED | `facture.py` `lister()` command updated: help string includes "partial", `_statut_style` maps `InvoiceStatus.PARTIAL: "cyan"`, Solde column added (line 202-206) |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Level 1 (Exists) | Level 2 (Substantive) | Level 3 (Wired) | Status |
|----------|----------|------------------|-----------------------|-----------------|--------|
| `src/compteqc/factures/modeles.py` | Enhanced Facture with montant_paye, solde, PARTIAL status, LigneFacture.compte_revenu | Yes | Yes — 166 lines, all features present | Imported by journal.py, registre.py, CLI | VERIFIED |
| `src/compteqc/factures/journal.py` | Per-line revenue grouping, generer_ecriture_paiement_partiel() | Yes | Yes — 87 lines; defaultdict grouping on lines 30-33; partial function lines 68-86 | Imported by facture.py CLI | VERIFIED |
| `src/compteqc/factures/registre.py` | enregistrer_paiement() and lister_impayees() methods | Yes | Yes — 122 lines; enregistrer_paiement lines 79-103; lister_impayees lines 105-107 | Imported by aging.py, facture.py CLI | VERIFIED |
| `src/compteqc/vieillissement.py` | AR/AP aging bucket engine with combined summary | Yes | Yes — 192 lines; 3 dataclasses; 5 functions; all 4 buckets initialized in __post_init__ | Imported at module level by aging.py | VERIFIED |
| `src/compteqc/cli/fournisseur.py` | add, list, voir, pay commands | Yes | Yes — 355 lines; all 4 commands implemented with Rich tables, validation, Beancount generation | Registered in app.py line 91 | VERIFIED |
| `src/compteqc/cli/aging.py` | ar, ap, summary commands | Yes | Yes — 267 lines; all 3 commands with Rich tables and per-bucket summaries | Registered in app.py line 92 | VERIFIED |
| `src/compteqc/cli/facture.py` | Enhanced lister with PARTIAL/OVERDUE status support and Solde column | Yes | Yes — PARTIAL in styles dict (line 73), help text updated (line 174), Solde column (line 202) | Already registered in app.py | VERIFIED |
| `src/compteqc/cli/app.py` | Registers fournisseur and aging sub-apps | Yes | Yes — lines 81-82 import both; lines 91-92 add_typer both | Is the root app | VERIFIED |
| `tests/test_factures_modeles.py` | 15 tests for partial payments, status derivation, configurable revenue | Yes | Yes — 16 tests (1 extra for lister_impayees); all 16 pass | Executed by pytest | VERIFIED |
| `tests/test_vieillissement.py` | 16 tests for aging buckets, edge cases, combined summary | Yes | Yes — 16 tests; all 16 pass | Executed by pytest | VERIFIED |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli/fournisseur.py` | `compteqc.fournisseurs.modeles` | top-level import lines 13-17 | WIRED | Imports `BillStatus`, `FactureFournisseur`, `LigneFactureFournisseur` |
| `cli/fournisseur.py` | `compteqc.fournisseurs.registre` | top-level import line 18 | WIRED | `RegistreFournisseurs` imported and used in every command |
| `cli/fournisseur.py` | `compteqc.fournisseurs.journal` | lazy imports inside `ajouter()` and `payer()` | WIRED | `generer_ecriture_facture_fournisseur` and `generer_ecriture_paiement_fournisseur` called and result passed to `_appendice_beancount()` |
| `cli/aging.py` | `compteqc.vieillissement` | top-level import lines 13-19 | WIRED | All 5 public symbols imported; `calculer_vieillissement_ar/ap` called in commands; `rapport_position_apar` called in `aging_summary` |
| `cli/aging.py` | `compteqc.factures.registre.RegistreFactures` | lazy import inside `_get_registre_factures()` | WIRED | Called in both `aging_ar` and `aging_summary` commands |
| `cli/aging.py` | `compteqc.fournisseurs.registre.RegistreFournisseurs` | lazy import inside `_get_registre_fournisseurs()` | WIRED | Called in both `aging_ap` and `aging_summary` commands |
| `cli/app.py` | `cli/fournisseur.py` | `from compteqc.cli.fournisseur import fournisseur_app` line 81 | WIRED | `app.add_typer(fournisseur_app, name="fournisseur", ...)` line 91 |
| `cli/app.py` | `cli/aging.py` | `from compteqc.cli.aging import aging_app` line 82 | WIRED | `app.add_typer(aging_app, name="aging", ...)` line 92 |
| `Facture.solde` | `Facture.total - Facture.montant_paye` | property at line 81-83 | WIRED | `return self.total - self.montant_paye` |
| `determiner_statut()` | `InvoiceStatus` transitions | standalone function lines 132-165 | WIRED | Handles all 5 paths: PAID, OVERDUE (partial+late), PARTIAL, OVERDUE (no payment), DRAFT, SENT |
| `RegistreFactures.enregistrer_paiement()` | `determiner_statut()` | call at line 98 | WIRED | `updated_statut = determiner_statut(updated)` then stored back |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AREN-01 | 12-01 | User can record partial payments on existing invoices with running balance | SATISFIED | `Facture.montant_paye`, `Facture.solde`, `RegistreFactures.enregistrer_paiement()` all implemented and tested |
| AREN-02 | 12-01 | System derives invoice status from payment state | SATISFIED | `determiner_statut()` function; 5 dedicated tests cover all status transitions |
| AREN-03 | 12-02 | User can list unpaid invoices filtered by status | SATISFIED | `cqc facture lister --statut partial/overdue` — `InvoiceStatus(statut.lower())` parsing handles PARTIAL; Solde column added |
| AREN-04 | 12-01 | Revenue account is configurable per invoice line | SATISFIED | `LigneFacture.compte_revenu` field with "Revenus:Consultation" default; `generer_ecriture_facture()` groups by this field |
| AGNG-01 | 12-01 | System calculates aging buckets for AR invoices | SATISFIED | `calculer_vieillissement_ar()` in `vieillissement.py`; 5 AR tests pass |
| AGNG-02 | 12-01 | System calculates aging buckets for AP bills | SATISFIED | `calculer_vieillissement_ap()` in `vieillissement.py`; 2 AP tests pass |
| AGNG-03 | 12-01 | User can view combined AP/AR position summary with net cash impact | SATISFIED | `rapport_position_apar()` returns `PositionAPAR` with `position_nette`, `encaissements_30j`, `paiements_30j`, `flux_net_30j` |
| AGNG-04 | 12-02 | User can run aging reports via CLI | SATISFIED | `cqc aging ar`, `cqc aging ap`, `cqc aging summary` — all 3 commands implemented in `aging.py` and registered in `app.py` |
| CLAP-01 | 12-02 | User can create vendor bills interactively via `cqc fournisseur add` | SATISFIED | `ajouter()` command with interactive prompts for all required fields; generates Beancount entry via `generer_ecriture_facture_fournisseur()` |
| CLAP-02 | 12-02 | User can list vendor bills via `cqc fournisseur list` with status filter | SATISFIED | `lister()` command parses `--statut` option to `BillStatus` and passes to `registre.lister()`; Rich table with 9 columns |
| CLAP-03 | 12-02 | User can record bill payment via `cqc fournisseur pay` (full or partial) | SATISFIED | `payer()` command defaults to full payment (solde) or accepts `--montant` for partial; validates overpayment; generates Beancount entry |

All 11 requirement IDs from plan frontmatters are accounted for. No orphaned requirements found.

### Anti-Patterns Found

No anti-patterns detected across the 8 source files examined. No TODOs, FIXMEs, placeholders, empty returns, or stub handlers found.

### Human Verification Required

#### 1. Interactive Vendor Bill Creation

**Test:** Run `cqc fournisseur add` in a terminal (no flags) and step through the prompts
**Expected:** Sequential prompts for nom du fournisseur, numero de reference, description, montant, categorie de depense; then shows preview with sous-total/TPS/TVQ/total; saves and appends Beancount entry to monthly .beancount file
**Why human:** The interactive prompt sequence and preview formatting require terminal execution

#### 2. Aging Reports Color-Coded Tables

**Test:** With at least 4 invoices across different aging brackets, run `cqc aging ar` and `cqc aging ap`
**Expected:** Rich table with rows colored green (0-30 days), yellow (31-60), dark_orange (61-90), red (91+); followed by per-bucket summary with totals and invoice counts
**Why human:** Rich color rendering cannot be verified in headless output

#### 3. Combined AP/AR Position Summary

**Test:** With some AR invoices and AP bills in different buckets, run `cqc aging summary`
**Expected:** Formatted block showing AR total, AP total, net position (green if >= 0, red if < 0), then 30-day cash flow section with encaissements/paiements/flux net
**Why human:** Conditional color logic on net position sign and formatted layout require visual inspection

### Test Results

32/32 tests pass in the project virtual environment (.venv, Python 3.12.11):

- `tests/test_factures_modeles.py`: 16/16 pass — covers partial payment tracking, status derivation (5 transitions), configurable revenue accounts, per-line journal entries, partial payment journal entries, registry payment recording
- `tests/test_vieillissement.py`: 16/16 pass — covers age calculation, bucket classification, AR aging with empty/single/multiple/partial/paid cases, AP aging, and combined position summary

Note: Tests fail with the system Python (3.10.8) due to `compteqc` not being installed in that environment. They pass correctly with `.venv/bin/python` as intended by the project's `pyproject.toml` configuration.

### Implementation Notes

One deviation was noted between Plan 02 specification and actual implementation in `cli/fournisseur.py`: the `payer()` command uses `registre.mettre_a_jour_statut()` with `montant_paye` and `methode_paiement` parameters instead of a separate `enregistrer_paiement()` method. The SUMMARY.md for Plan 02 documents this as an intentional decision ("Payment recording via mettre_a_jour_statut with montant_paye parameter rather than separate enregistrer_paiement method"). The behavior achieved is functionally identical — partial payments are recorded correctly and status is updated.

---

_Verified: 2026-02-26T16:30:00Z_
_Verifier: Claude (gsd-verifier)_
