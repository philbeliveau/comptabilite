---
phase: 13-recurring-invoices-auto-matching
verified: 2026-02-26T17:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 13: Recurring Invoices & Auto-Matching Verification Report

**Phase Goal:** Recurring invoice templates for retainer clients; auto-matching of bank transactions to AR/AP entries during import
**Verified:** 2026-02-26T17:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can create a recurring invoice template specifying client, amount, frequency (mensuel/bimensuel/trimestriel/annuel), and next generation date | VERIFIED | `ModeleFactureRecurrente` model in `recurrent.py` L24-41; `template-add` CLI command in `facture.py` L389-458; `test_modele_creation` + `test_frequences_valides` + `test_cli_template_add` all pass |
| 2 | Running `cqc facture generate-recurring` creates invoices from all due templates, assigns sequential FAC-YYYY-NNN numbers, and advances each template's next date | VERIFIED | `generer_factures_recurrentes()` in `recurrent.py` L128-181; `generate_recurring` CLI command in `facture.py` L495-569; `test_generer_factures_recurrentes_due` + `test_cli_generate_recurring` pass |
| 3 | Templates persist in YAML and survive application restarts | VERIFIED | `RegistreRecurrents._sauvegarder()` / `_charger()` in `recurrent.py` L51-72; `test_registre_persistence` passes; default path `ledger/factures/modeles-recurrents.yaml` |
| 4 | Generated invoices appear in the RegistreFactures and have correct Beancount journal entries appended | VERIFIED | `registre_factures.ajouter(facture)` at `recurrent.py` L171; `_appendice_beancount(ecriture)` called per invoice in `facture.py` L565-567; `test_cli_generate_recurring` asserts both registry entry and beancount file content |
| 5 | When importing bank transactions, the system suggests matches between deposits and open AR invoices based on amount and description similarity | VERIFIED | `suggerer_rapprochement_ar()` in `rapprochement.py` L116-167; called inside `_afficher_rapprochements()` in `importer.py` L460-463; `test_ar_exact_amount_match`, `test_ar_amount_match_with_client_name`, `test_import_shows_ar_suggestions` all pass |
| 6 | When importing bank transactions, the system suggests matches between withdrawals and open AP bills based on amount and vendor name | VERIFIED | `suggerer_rapprochement_ap()` in `rapprochement.py` L170-226; called inside `_afficher_rapprochements()` in `importer.py` L474-479; `test_ap_exact_amount_match`, `test_ap_amount_match_with_vendor_name` pass |
| 7 | Match suggestions include a confidence score (0.0-1.0) so the user can assess quality | VERIFIED | `SuggestionRapprochement.confiance: float` field in `rapprochement.py` L38; scoring formula: 0.7 (amount within $0.02) + up to 0.3 (name similarity); displayed as `{s.confiance:.0%}` in Rich table in `importer.py` L500 |
| 8 | Exact amount matches with vendor/client name similarity score above 0.6 produce high-confidence suggestions | VERIFIED | `_calculer_score()` in `rapprochement.py` L52-91 implements this formula exactly; `test_ar_amount_match_with_client_name` asserts `confiance >= 0.9`, `test_ap_amount_match_with_vendor_name` asserts `confiance >= 0.9` |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Provided | Status | Details |
|----------|----------|--------|---------|
| `src/compteqc/factures/recurrent.py` | `ModeleFactureRecurrente`, `RegistreRecurrents`, `generer_factures_recurrentes` | VERIFIED | 181 lines; all three exports present; substantive YAML persistence and generation logic |
| `src/compteqc/cli/facture.py` | CLI commands `template-add`, `template-list`, `generate-recurring` | VERIFIED | All three commands registered on `facture_app`; confirmed via `cqc facture --help` |
| `tests/test_recurrent.py` | Unit tests for recurring model, registry, generation, and CLI | VERIFIED | 308 lines (min_lines: 80 satisfied); 17 tests, all pass |
| `src/compteqc/rapprochement.py` | `suggerer_rapprochement_ar()`, `suggerer_rapprochement_ap()`, `SuggestionRapprochement` | VERIFIED | 226 lines; all three exports present and substantive |
| `src/compteqc/cli/importer.py` | Integration of match suggestions into import pipeline | VERIFIED | `_afficher_rapprochements()` and `_beancount_vers_transactions()` implemented; called at import completion (L682-690) |
| `tests/test_rapprochement.py` | Unit tests for matching logic, confidence scoring, and edge cases | VERIFIED | 353 lines (min_lines: 100 satisfied); 18 tests, all pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `recurrent.py` | `factures/modeles.py` | `from compteqc.factures.modeles import Facture, InvoiceStatus, LigneFacture` | WIRED | `recurrent.py` L18; all three symbols used in generation logic |
| `recurrent.py` | `factures/registre.py` | uses `RegistreFactures` to add generated invoices | WIRED | `recurrent.py` L19; `registre_factures.ajouter(facture)` at L171; `registre_factures.prochain_numero()` at L158 |
| `cli/facture.py` | `factures/recurrent.py` | `from compteqc.factures.recurrent import` | WIRED | `facture.py` L21-25; `RegistreRecurrents` used in `_get_registre_recurrents()` L72-77; `generer_factures_recurrentes` called at L543 |
| `rapprochement.py` | `factures/registre.py` | reads `RegistreFactures` for open AR invoices | WIRED | `RegistreFactures` imported inside `_afficher_rapprochements()` in `importer.py` L453; not directly in `rapprochement.py` (function receives list, caller provides registry — by design) |
| `rapprochement.py` | `models/transaction.py` | accepts `TransactionNormalisee` for matching | WIRED | `rapprochement.py` L16 imports; L117 and L171 use as parameter type |
| `cli/importer.py` | `rapprochement.py` | `from compteqc.rapprochement import` | WIRED | `importer.py` L18 top-level import; `suggerer_rapprochement_ar` called at L461; `suggerer_rapprochement_ap` called at L478 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RECM-01 | 13-01 | User can create recurring invoice templates with frequency and auto-generation date | SATISFIED | `ModeleFactureRecurrente` + `RegistreRecurrents` + `template-add` CLI command; template persisted in YAML; 4 frequencies supported |
| RECM-02 | 13-01 | System generates invoices from templates on schedule or via `cqc facture generate-recurring` | SATISFIED | `generer_factures_recurrentes()` + `generate-recurring` CLI; sequential FAC-YYYY-NNN numbers; template date advances; Beancount entries appended |
| RECM-03 | 13-02 | System auto-matches bank deposits against outstanding AR invoices by amount and description | SATISFIED | `suggerer_rapprochement_ar()` with $0.02 tolerance + SequenceMatcher similarity; integrated into import pipeline; 8 AR tests pass |
| RECM-04 | 13-02 | System auto-matches bank withdrawals against outstanding AP bills by amount and vendor | SATISFIED | `suggerer_rapprochement_ap()` with same scoring model; uses real `FactureFournisseur` (Phase 11 shipped); 5 AP tests pass |

No orphaned requirements — all 4 RECM IDs are claimed in plan frontmatter and verified.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `rapprochement.py` | 133, 187 | `return []` | Info | These are correct early-exit guards (`if transaction.montant <= 0: return []` and `if transaction.montant >= 0: return []`) — not stub returns. Function bodies that follow are fully implemented. |

No blocker or warning anti-patterns found. The two `return []` instances are intentional direction-guards (deposits-only for AR, withdrawals-only for AP), both tested by `test_ar_negative_amount_ignored` and `test_ap_positive_amount_ignored`.

---

### Human Verification Required

The following items cannot be verified programmatically:

#### 1. Import Pipeline End-to-End Display

**Test:** Run `cqc importer fichier <real-bank-csv>` against a real or realistic RBC CSV file that contains a deposit matching an existing invoice in the registry.
**Expected:** After the import summary table, a "Rapprochements AR suggeres" Rich table appears listing the matching invoice with a confidence percentage.
**Why human:** Requires a real CSV file with matching ledger state; output is terminal Rich rendering, not easily captured in unit tests.

#### 2. Dry-Run Mode User Experience

**Test:** Create a template, then run `cqc facture generate-recurring --dry-run`.
**Expected:** Table of what would be generated is shown; no files written; `cqc facture lister` confirms no new invoices exist.
**Why human:** Verifies the interplay of terminal output and absence of side effects under a real shell session.

---

### Commit Verification

All 4 commits documented in SUMMARY files exist in git log:

| Commit | Description |
|--------|-------------|
| `4517dcc` | feat(13-01): add recurring invoice model, registry, and generation logic |
| `3e881fd` | feat(13-01): add recurring template CLI commands and integration tests |
| `f8e458b` | feat(13-02): add auto-matching engine for AR/AP bank reconciliation |
| `ec8bf2d` | feat(13-02): integrate auto-matching suggestions into import pipeline |

---

### Test Results

```
tests/test_recurrent.py: 17 passed
tests/test_rapprochement.py: 18 passed
Total: 35 passed in 1.27s
```

All tests pass cleanly with no warnings or skips.

---

## Summary

Phase 13 goal is fully achieved. Both plan objectives are implemented and verified:

**Plan 01 (Recurring Templates):** `ModeleFactureRecurrente` model with YAML-backed `RegistreRecurrents` and frequency-based date advancement via `python-dateutil`. CLI commands `template-add`, `template-list`, and `generate-recurring` (with `--dry-run`) are registered and functional. Generated invoices receive sequential FAC-YYYY-NNN numbers and Beancount journal entries are appended automatically.

**Plan 02 (Auto-Matching):** `rapprochement.py` implements a Protocol-based matching engine with a shared `_calculer_score()` helper: 0.7 confidence for amount match within $0.02 tolerance, plus up to 0.3 for name similarity via `SequenceMatcher`. AR matching processes positive transactions against open `Facture` entries; AP matching processes negative transactions against open `FactureFournisseur` entries (Phase 11 fully available). The import pipeline (`importer.py`) displays suggestion tables in Rich after every successful bank file import, with a guard clause for missing registries.

---

_Verified: 2026-02-26T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
