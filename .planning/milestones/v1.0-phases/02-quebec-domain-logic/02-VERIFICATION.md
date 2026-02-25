---
phase: 02-quebec-domain-logic
verified: 2026-02-19T15:30:00Z
status: human_needed
score: 5/5 success criteria verified
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "Shareholder loan ledger-reading bridge: obtenir_etat_pret(entries, fin_exercice) added to suivi.py (commit f1e565a). Reads Passifs:Pret-Actionnaire postings from Beancount entries, maps to MouvementPret, delegates to calculer_etat_pret(). 5 new tests added (TestObtenirEtatPret class). Total tests for this module: 17."
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Validate Quebec income tax formula completeness"
    expected: "Quebec income tax per-period withholding matches Revenu Quebec WebRAS calculator output for the same inputs (gross $5,000 bi-weekly, 26 periods, 2026)"
    why_human: "impot_quebec.py has a TODO comment acknowledging MEDIUM confidence on deduction-for-workers (~$1,450) and other potential deductions not implemented. Cannot verify formula completeness against official calculator programmatically."
---

# Phase 2: Quebec Domain Logic Verification Report

**Phase Goal:** User can run payroll with all Quebec deductions calculated correctly, GST/QST is tracked separately on all transactions with ITC/ITR, capital assets are tracked with CCA schedules, and shareholder loan balances are monitored with deadline alerts
**Verified:** 2026-02-19T15:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (commit f1e565a)

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can run payroll via CLI and system produces correct journal entries with all contributions and taxes | VERIFIED | `cqc paie lancer 5000 --dry-run` produces a 21-posting balanced Beancount transaction with QPP base/supp1/supp2, RQAP, EI, FSS, CNESST, labour standards, federal (with 16.5% abatement) and Quebec income tax |
| 2 | Every business expense transaction has GST and QST tracked separately with net remittance summary by filing period | VERIFIED | `calcul.py` extracts TPS/TVQ independently with plug-value rounding; `sommaire.py` produces SommairePeriode by period; rules engine in `traitement.py` handles exempt/zero-rated; 18 tests pass |
| 3 | Capital assets over $500 tracked by CCA class with half-year rule, declining balance, and year-end Beancount transactions | VERIFIED | `dpa/calcul.py` implements PoolDPA with half-year rule on net additions; `journal.py` generates `!`-flagged Beancount transactions; 15 tests pass including recapture and terminal loss |
| 4 | Shareholder loan account tracks all personal-vs-business transactions and alerts at 9/11 months and 30 days before s.15(2) inclusion date | VERIFIED | `obtenir_etat_pret(entries, fin_exercice)` in `suivi.py` reads Beancount entries, filters to `Passifs:Pret-Actionnaire`, derives MouvementPret list, and calls `calculer_etat_pret()`. Alert calculations correct. 17 tests pass (12 prior + 5 new for bridge function). |
| 5 | All payroll and tax rates are config-driven in rates.py and YTD totals stop contributions at annual maximums | VERIFIED | `rates.py` has all 2026 rates as frozen Decimal dataclasses; `cotisations.py` enforces annual caps via cumul_annuel parameter; `ytd.py` reads payroll sub-accounts from ledger; 75 tests pass |

**Score:** 5/5 truths verified

---

### Required Artifacts

**Plan 02-01: Rates and Contributions**

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/compteqc/quebec/rates.py` | All 2026 rates as frozen Decimal dataclasses | VERIFIED | 201 lines; TauxAnnuels, TauxQPP, TauxRQAP, TauxAE, TauxFSS, bracket tuples; obtenir_taux(); no float literals |
| `src/compteqc/quebec/paie/cotisations.py` | Pure calculation functions for all 7 contribution types | VERIFIED | 240 lines; calculer_qpp_base_employe, supp1, supp2, RQAP, AE, FSS, CNESST, normes; cap enforcement |
| `src/compteqc/quebec/paie/ytd.py` | YTD accumulation from ledger for contribution cap enforcement | VERIFIED | 112 lines; obtenir_cumuls_annuels() reads ledger; calculer_cumuls_depuis_transactions() for testability |
| `tests/test_cotisations.py` | Comprehensive tests (min 100 lines) | VERIFIED | 32 tests; QPP all tiers, RQAP, AE, FSS, CNESST, normes; cap scenarios |

**Plan 02-02: Payroll Engine**

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/compteqc/quebec/paie/impot_federal.py` | Federal tax per T4127 with Quebec abatement | VERIFIED | 85 lines; calculer_impot_federal_periode(); T4127 formula; K1/K2Q/K4 credits; 16.5% abatement |
| `src/compteqc/quebec/paie/impot_quebec.py` | Quebec tax per TP-1015.F-V | VERIFIED | 77 lines; calculer_impot_quebec_periode(); bracket lookup; K1 and E credits; TODO for deduction-for-workers |
| `src/compteqc/quebec/paie/moteur.py` | Payroll engine orchestrating all calculations | VERIFIED | 201 lines; calculer_paie(); ResultatPaie frozen dataclass with all fields |
| `src/compteqc/quebec/paie/journal.py` | Beancount transaction generation | VERIFIED | 156 lines; generer_transaction_paie(); 21 postings; salary_offset support; balanced to zero |
| `src/compteqc/cli/paie.py` | CLI command for running payroll | VERIFIED | 219 lines; lancer() command; Rich table; dry-run; salary-offset; auto-detect period |

**Plan 02-03: GST/QST**

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/compteqc/quebec/taxes/calcul.py` | Tax extraction with separate GST/QST rounding | VERIFIED | 101 lines; extraire_taxes(); plug-value rounding; appliquer_taxes(); routing by treatment |
| `src/compteqc/quebec/taxes/traitement.py` | Tax treatment rule engine | VERIFIED | 235 lines; charger_regles_taxes(); determiner_traitement_depense(); determiner_traitement_revenu(); Pydantic models |
| `src/compteqc/quebec/taxes/sommaire.py` | Filing period summaries and reconciliation | VERIFIED | 208 lines; generer_sommaire_periode(); generer_sommaires_annuels(); verifier_concordance_tps_tvq() |
| `rules/taxes.yaml` | YAML configuration for tax treatment rules | VERIFIED | categories, vendeurs, clients sections; AWS out-of-province pattern; bank/insurance exemptions |
| `tests/test_taxes.py` | Tests for tax math, treatment, summaries, reconciliation (min 80 lines) | VERIFIED | 18 tests covering all required scenarios |

**Plan 02-04 / 02-05: CCA and Shareholder Loan**

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/compteqc/quebec/dpa/calcul.py` | Pool-level CCA with half-year rule and declining balance | VERIFIED | 145 lines; PoolDPA dataclass; calculer_dpa() with half-year; recapture; terminal loss; construire_pools() |
| `src/compteqc/quebec/dpa/registre.py` | Asset registry and pool-level UCC tracking | VERIFIED | Actif Pydantic model; RegistreActifs; YAML persistence; float rejection |
| `src/compteqc/quebec/dpa/journal.py` | CCA Beancount transaction generation | VERIFIED | generer_transactions_dpa(); `!` flag; recapture transactions; metadata with classe/taux/UCC |
| `src/compteqc/quebec/pret_actionnaire/alertes.py` | s.15(2) deadline calculation and graduated alerts | VERIFIED | 140 lines; calculer_dates_alerte(); obtenir_alertes_actives(); relativedelta arithmetic; fiscal-year-end based |
| `src/compteqc/quebec/pret_actionnaire/detection.py` | Circular loan pattern detection | VERIFIED | 71 lines; detecter_circularite(); 30-day window; 20% tolerance |
| `src/compteqc/quebec/pret_actionnaire/suivi.py` | Shareholder loan tracking from ledger | VERIFIED | calculer_etat_pret() for pure FIFO tracking. obtenir_etat_pret(entries, fin_exercice) reads Beancount entries, filters Passifs:Pret-Actionnaire postings, maps to MouvementPret, delegates to calculer_etat_pret(). beancount.core.data imported at line 15. Gap from previous verification is closed. |
| `data/actifs.yaml` | Persistent asset registry | VERIFIED | File exists with actifs: [] initial state |
| `tests/test_dpa.py` | CCA tests (min 80 lines) | VERIFIED | 15 tests; class 50 first/second year; half-year; recapture; terminal loss; YAML round-trip; `!` flag |
| `tests/test_pret_actionnaire.py` | Shareholder loan tests (min 60 lines) | VERIFIED | 17 tests (12 prior + 5 new TestObtenirEtatPret class); deadline dates; bidirectional balance; alert levels with freezegun; circularity detection; ledger-reading bridge |

---

### Key Link Verification

**Plan 02-01 Links**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cotisations.py` | `rates.py` | obtenir_taux() | WIRED | All 7 functions import TauxQPP/TauxRQAP/TauxAE/TauxFSS types from rates.py |
| `cotisations.py` | `ytd.py` | cumul_annuel parameter | WIRED | cumul_annuel passed as argument to every contribution function for cap enforcement |

**Plan 02-02 Links**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `moteur.py` | `cotisations.py` | calls all contribution functions | WIRED | Imports and calls calculer_qpp_base_employe, supp1, supp2, rqap, ae, fss, cnesst, normes |
| `moteur.py` | `impot_federal.py` | calculer_impot_federal_periode | WIRED | Explicit import and call at line 161 |
| `journal.py` | `beancount.core.data` | data.Transaction, create_simple_posting | WIRED | Uses data.Transaction constructor and _ajouter_posting() helper calling create_simple_posting |
| `cli/paie.py` | `moteur.py` | calculer_paie | WIRED | Imports and calls calculer_paie() at line 81 |

**Plan 02-03 Links**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `traitement.py` | `rules/taxes.yaml` | yaml.safe_load via charger_regles_taxes | WIRED | charger_regles_taxes() reads yaml file; test_charger_regles_from_real_file passes |
| `calcul.py` | `rates.py` | taux_tps / taux_tvq | ACCEPTABLE | calcul.py takes taux_tps, taux_tvq as parameters (not direct import). Connection to rates.py is via the caller passing rates. Acceptable architecture. |
| `sommaire.py` | `beancount` | loader.load_file, Passifs:TPS, Actifs:TPS | WIRED | sommaire.py imports from beancount.core.data; queries COMPTE_TPS_PERCUE, COMPTE_TVQ_PERCUE, etc. |

**Plan 02-04 / 02-05 Links**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `dpa/calcul.py` | `dpa/registre.py` | RegistreActifs, PoolDPA | WIRED | construire_pools() takes list[Actif] from registre; PoolDPA and Actif imported |
| `dpa/journal.py` | `beancount.core.data` | data.Transaction, create_simple_posting | WIRED | Creates data.Transaction with postings using amount.Amount and data.Posting |
| `pret_actionnaire/alertes.py` | `datetime` via relativedelta | relativedelta | WIRED | `from dateutil.relativedelta import relativedelta` at line 22; used for all month arithmetic |
| `pret_actionnaire/suivi.py` | `beancount.core.data` | data.Transaction, posting.account | WIRED | `from beancount.core import data` at line 15; obtenir_etat_pret() iterates entries, checks isinstance(entry, data.Transaction), filters by posting.account == COMPTE_PRET_ACTIONNAIRE |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PAY-01 | 02-02 | User can run payroll for a given gross salary amount and pay period | SATISFIED | `cqc paie lancer 5000` works; test_calcul_complet_5000_brut passes |
| PAY-02 | 02-01 | QPP base (5.3%), additional 1 (1.0%), additional 2 (4.0%) with correct maximums | SATISFIED | cotisations.py; 8 QPP tests pass |
| PAY-03 | 02-01 | RQAP employer (0.602%) and employee (0.430%) | SATISFIED | calculer_rqap_employe/employeur; 3 RQAP tests pass |
| PAY-04 | 02-01 | EI at Quebec rate (employer 1.82%, employee 1.30%) with MIE cap | SATISFIED | calculer_ae_employe/employeur; 4 AE tests pass |
| PAY-05 | 02-01 | FSS (1.65% for payroll under $1M) | SATISFIED | calculer_fss(); 2 FSS tests pass |
| PAY-06 | 02-01 | CNESST based on assigned classification rate | SATISFIED | calculer_cnesst(); configurable via cnesst_taux |
| PAY-07 | 02-01 | Labour standards (0.06%) | SATISFIED | calculer_normes_travail(); 3 tests pass |
| PAY-08 | 02-02 | Federal income tax with Quebec 16.5% abatement | SATISFIED | impot_federal.py; T4127 formula; abatement_quebec = 0.165 applied |
| PAY-09 | 02-02 | Quebec provincial income tax using TP-1015.F-V | SATISFIED (with caveat) | impot_quebec.py; TP-1015.F-V bracket structure; TODO on deduction-for-workers (see Human Verification) |
| PAY-10 | 02-01 | YTD tracking stops contributions at annual maximums | SATISFIED | ytd.py reads ledger; all contribution functions enforce cap via cumul_annuel |
| PAY-11 | 02-02 | Payroll generates complete journal entries | SATISFIED | journal.py; 21 postings; balanced to zero; test_transaction_equilibree passes |
| PAY-12 | 02-01 | All payroll rates config-driven in rates.py | SATISFIED | rates.py; TAUX_2026; obtenir_taux(); no hardcoded rates in calculation functions |
| TAX-01 | 02-03 | GST collected (5%) and QST collected (9.975%) tracked separately on revenue | SATISFIED | COMPTE_TPS_PERCUE / COMPTE_TVQ_PERCUE in sommaire.py |
| TAX-02 | 02-03 | GST paid and QST paid on expenses for ITC/ITR claims | SATISFIED | COMPTE_TPS_PAYEE / COMPTE_TVQ_PAYEE tracked in generer_sommaire_periode |
| TAX-03 | 02-03 | GST and QST calculated separately, each rounded independently | SATISFIED | extraire_taxes() rounds TPS and TVQ independently; plug-value ensures exact total |
| TAX-04 | 02-03 | Net GST/QST remittance summary by filing period | SATISFIED | generer_sommaire_periode() / generer_sommaires_annuels() with annuel/trimestriel |
| TAX-05 | 02-03 | Handles GST/QST-exempt items | SATISFIED | extraire_taxes_selon_traitement() returns (total, 0, 0) for exempt/zero |
| TAX-06 | 02-03 | Reconciliation check ensures GST and QST from identical transaction sets | SATISFIED | verifier_concordance_tps_tvq(); test_concordance_mismatch passes |
| CCA-01 | 02-04 | Capital assets tracked by CCA class (8, 10, 12, 50, 54) | SATISFIED | CLASSES_DPA in classes.py; construire_pools() groups by classe |
| CCA-02 | 02-04 | Half-year rule automatically applied for new acquisitions | SATISFIED | calculer_dpa(): if additions_nettes > 0 uses 0.5 multiplier; test_dpa_classe_50_premiere_annee passes |
| CCA-03 | 02-04 | Declining balance depreciation per class at correct rates | SATISFIED | base * taux (0.55 for class 50, 0.20 for class 8, etc.) |
| CCA-04 | 02-04 | UCC schedule maintained per class | SATISFIED | ucc_ouverture, ucc_fermeture properties on PoolDPA; construire_pools() tracks per class |
| CCA-05 | 02-04 | Handles disposals and recapture/terminal loss | SATISFIED | recapture property; perte_finale(); test_recapture and test_perte_finale pass |
| CCA-06 | 02-04 | CCA entries generated as Beancount transactions for year-end | SATISFIED | generer_transactions_dpa(); `!` flag; metadata; test_journal_dpa_flag_review passes |
| LOAN-01 | 02-04/02-05 | Shareholder loan account (1800) tracks all personal-vs-business transactions | SATISFIED | obtenir_etat_pret(entries, fin_exercice) reads Passifs:Pret-Actionnaire from live ledger. FIFO tracking in calculer_etat_pret() confirmed. 5 tests in TestObtenirEtatPret pass (fiscal-year filter, account filter, empty entries, narration mapping). |
| LOAN-02 | 02-04 | System computes repayment deadline (fiscal year-end + 1 year) per s.15(2) | SATISFIED | calculer_dates_alerte(): fin_exercice_annee + relativedelta(years=1); correctly uses fiscal year-end not loan date |
| LOAN-03 | 02-04 | Alerts at 9 months, 11 months, and 30 days before inclusion date | SATISFIED | alerte_9_mois, alerte_11_mois, alerte_30_jours in AlertePret; obtenir_alertes_actives(); 5 alert tests pass |
| LOAN-04 | 02-04 | System flags circular loan-repayment-reborrow patterns | SATISFIED | detecter_circularite(); 30-day window; 20% tolerance; 3 circularity tests pass |
| CLI-04 | 02-02 | User can run payroll via CLI command | SATISFIED | `cqc paie lancer <montant>` registered in app.py via app.add_typer(paie_app); confirmed working with dry-run test |

**Orphaned requirements check:** No requirements mapped to Phase 2 in REQUIREMENTS.md that are missing from plan coverage.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/compteqc/quebec/paie/impot_quebec.py` | 12 | TODO: Valider contre le calculateur WebRAS de Revenu Quebec — "deduction pour travailleur" ~$1,450 not implemented | Warning | Quebec income tax withholding may be slightly higher than actual (over-withholds, not under-withholds). No blocking issue; bracket structure is correct. |

No stub implementations, empty returns, or placeholder patterns found in any phase 2 module. No new anti-patterns introduced by gap-closure commit.

---

### Human Verification Required

#### 1. Quebec Income Tax Formula Completeness

**Test:** Take the `cqc paie lancer 5000 --dry-run` output showing Quebec tax withholding (~$873/period). Enter equivalent inputs in Revenu Quebec's WebRAS calculator (salaire $5,000 bi-weekly, 26 periods, personal credit $18,952, 2026).
**Expected:** WebRAS and the system should agree within $10-20/period, or the system's value should be conservatively higher (over-withholds rather than under-withholds, which is safe — the deduction-for-workers reduces withholding by ~$56/period if implemented).
**Why human:** The Quebec "deduction for workers" (~$1,450 annually) is flagged with MEDIUM confidence in the code comments. Cannot verify formula completeness against official calculator programmatically. This carried over from initial verification; no change in status.

---

### Re-Verification: Gap Closure Summary

**Gap closed: LOAN-01 — Shareholder loan ledger-reading bridge**

Commit `f1e565a` added `obtenir_etat_pret(entries: list, fin_exercice: datetime.date) -> EtatPret` to `src/compteqc/quebec/pret_actionnaire/suivi.py` (lines 90-135). The function:

- Imports `from beancount.core import data` (line 15)
- Iterates Beancount entries, skipping non-Transaction types
- Filters by `entry.date.year == fin_exercice.year` for fiscal year scoping
- Filters postings by `posting.account == COMPTE_PRET_ACTIONNAIRE` ("Passifs:Pret-Actionnaire")
- Maps positive postings to type "avance", negative to "remboursement"
- Delegates to `calculer_etat_pret(mouvements)` for FIFO balance computation

Five new tests in `TestObtenirEtatPret` verify: mixed avances/remboursements, fiscal-year filtering, non-pret-actionnaire account exclusion, empty entries, and narration-as-description mapping.

**Regression check:** All 146 phase 2 tests pass (`uv run pytest tests/test_rates.py tests/test_cotisations.py tests/test_impot.py tests/test_paie_integration.py tests/test_taxes.py tests/test_dpa.py tests/test_pret_actionnaire.py`). No regressions.

---

### Test Suite Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/test_rates.py` | 43 | All passing |
| `tests/test_cotisations.py` | 32 | All passing |
| `tests/test_impot.py` | 10 | All passing |
| `tests/test_paie_integration.py` | 11 | All passing |
| `tests/test_taxes.py` | 18 | All passing |
| `tests/test_dpa.py` | 15 | All passing |
| `tests/test_pret_actionnaire.py` | 17 | All passing |
| **Total Phase 2** | **146** | **All passing** |

Note: 7 failures in `tests/test_cli.py` belong to Phase 1 (importer, soldes, rapports CLI tests that use real ledger fixture data) — not Phase 2 scope.

---

_Verified: 2026-02-19T15:30:00Z_
_Verifier: Claude (gsd-verifier)_
