---
phase: 03-ai-categorization-and-review-workflow
verified: 2026-02-19T14:10:00Z
status: passed
score: 19/19 must-haves verified
re_verification: false
---

# Phase 3: AI Categorization and Review Workflow — Verification Report

**Phase Goal:** Transactions that the rule engine cannot categorize are handled by ML prediction and LLM classification with confidence scoring, and all AI-categorized transactions go through a human review workflow before reaching the official ledger.

**Verified:** 2026-02-19T14:10:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Pipeline cascades through rules -> ML -> LLM tiers, each processing only uncategorized remainder | VERIFIED | `pipeline.py` lines 77-127: tier 1 returns early on rule match; tiers 2-3 only run when previous fails |
| 2 | ML tier provides probability-based confidence scores via SVC(probability=True) | VERIFIED | `ml.py` line 81: `SVC(kernel="linear", probability=True)`; line 108: `predict_proba` used for confidence |
| 3 | ML tier is gracefully skipped when no training data exists (cold start) | VERIFIED | `ml.py` lines 55-73: `est_entraine` stays False if <20 samples or <2 accounts; pipeline checks `est_entraine` before calling |
| 4 | Every pipeline result carries a confidence score and source tag (regle/ml/llm/non-classe) | VERIFIED | `ResultatPipeline` dataclass has `confiance: float` and `source: str`; all code paths assign one of the four valid source values |
| 5 | Transactions below 80% confidence are marked for mandatory review | VERIFIED | `pipeline.py` line 113-116: `revue = (confiance < SEUIL_REVUE_OPTIONNELLE or suggestions is not None)` |
| 6 | Transactions 80-95% go to pending queue, above 95% are auto-approved | VERIFIED | `pipeline.py` `determiner_destination()` lines 172-189: explicit threshold routing to "direct", "pending", "revue" |
| 7 | Transactions >$500 or matching known vendor patterns are flagged as potential CAPEX with suggested CCA class | VERIFIED | `capex.py`: `DetecteurCAPEX.verifier()` checks amount >= seuil (500) OR vendor pattern match; `_suggerer_classe()` returns class 50/8/10/12 |
| 8 | Tier disagreement (ML and LLM suggest different accounts) forces mandatory review | VERIFIED | `pipeline.py` lines 154-164: when ML and LLM disagree, `suggestions` dict is populated; `revue_obligatoire` is set True when `suggestions is not None` |
| 9 | Claude LLM categorizes transactions constrained to the closed chart of accounts list | VERIFIED | `llm.py` lines 126-136: LLM response validated against `_comptes_valides`; invalid accounts fallback to Non-Classe |
| 10 | LLM receives rich context: transaction, chart of accounts, vendor history, similar transactions | VERIFIED | `llm.py` `_construire_prompt()` lines 167-203: includes transaction details, full accounts list, optional vendor history, optional similar transactions |
| 11 | LLM proposes account classification only — GST/QST never computed by LLM | VERIFIED | System prompt (`_PROMPT_SYSTEME` line 54): "Ne mentionne JAMAIS la TPS/TVQ/GST/QST ni aucun calcul de taxe" |
| 12 | LLM categorizations are stored as JSONL with prompt, response, timestamp, and model for drift detection | VERIFIED | `llm.py` `_enregistrer_log()` lines 205-242: writes timestamp, prompt_hash, modele, compte, confiance, raisonnement, est_capex, tokens_utilises to JSONL |
| 13 | AI-categorized transactions go to pending.beancount with #pending tag | VERIFIED | `pending.py` `_preparer_pending()` lines 70-126: adds "pending" to tags, sets flag="!", adds source_ia/confiance/compte_propose metadata |
| 14 | Import CLI command runs the full pipeline (rules -> ML -> LLM) at import time | VERIFIED | `importer.py`: `_creer_pipeline()` creates all three tiers; `_importer_avec()` calls pipeline for each transaction; routing to direct/pending/revue |
| 15 | If ANTHROPIC_API_KEY is missing, LLM tier is skipped with a warning (graceful degradation) | VERIFIED | `importer.py` lines 156-164: `llm.est_disponible` checked before setting `classificateur_llm`; info message printed if key missing |
| 16 | Auto-approved transactions (>95% confidence) go directly to monthly files with audit metadata | VERIFIED | `importer.py` lines 247-258: transactions with "direct" destination get `categorisation` and `confiance` metadata written to monthly files |
| 17 | User can review pending transactions in a Rich table showing account, confidence, source, vendor history, and CAPEX flags | VERIFIED | `reviser.py` `liste()` command: Rich table with #, Date, Montant, Beneficiaire, Compte propose, Conf. (color-coded), Source, Drapeaux (CAPEX/!) |
| 18 | User can approve, reject, or recategorize individual or batched pending transactions via CLI | VERIFIED | `reviser.py`: `approuver`, `rejeter`, `recategoriser` commands wired to `approuver_transactions`, `rejeter_transactions`, and inline recategorization logic |
| 19 | Approved transactions move from pending.beancount to monthly ledger files with #pending tag removed | VERIFIED | `pending.py` `approuver_transactions()` + `_finaliser_approbation()`: removes "pending" tag, changes flag to "*", writes to `chemin_fichier_mensuel`, rewrites pending with remaining |
| 20 | User corrections are tracked and after 2 identical corrections (same vendor -> same account), a new rule is auto-generated in categorisation.yaml | VERIFIED | `feedback.py` `enregistrer_correction()`: counts per vendor->account; at count >= 2 returns a `Regle`; `ajouter_regle_auto()` writes to YAML |
| 21 | Mandatory review items (<80%) are visually distinct from optional review items (80-95%) | VERIFIED | `reviser.py` lines 210-218: obligatoires displayed first, separator row "---" inserted between groups, confidence color-coded (red/yellow/green) |
| 22 | Corrections accept optional notes for later analysis | VERIFIED | `reviser.py` `recategoriser` has `--note` option; `enregistrer_correction()` accepts and stores `note` in historique JSON |

**Score:** 22/22 truths verified (plan-defined must-have truths covered in full)

---

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/compteqc/categorisation/pipeline.py` | VERIFIED | 190 lines, `PipelineCategorisation` + `ResultatPipeline` present; tier cascade, threshold routing, CAPEX check all substantive |
| `src/compteqc/categorisation/ml.py` | VERIFIED | 114 lines, `PredicteurML` with `SVC(probability=True)`, cold start handling, `MIN_TRAINING_SIZE=20`, `predire()` returns `ResultatML` |
| `src/compteqc/categorisation/capex.py` | VERIFIED | 113 lines, `DetecteurCAPEX.verifier()` checks amount + vendor pattern; `_suggerer_classe()` maps keywords to CCA classes 50/8/10/12 |
| `src/compteqc/categorisation/llm.py` | VERIFIED | 243 lines, `ClassificateurLLM` uses `messages.parse()` with Pydantic output; validates against chart of accounts; JSONL logging; graceful degradation |
| `src/compteqc/categorisation/pending.py` | VERIFIED | 318 lines, `ecrire_pending`, `lire_pending`, `approuver_transactions`, `rejeter_transactions` all substantive with rollback logic |
| `src/compteqc/categorisation/feedback.py` | VERIFIED | 183 lines, `enregistrer_correction` with persistent JSON; `ajouter_regle_auto` writes YAML; duplicate detection; atomic saves |
| `src/compteqc/cli/reviser.py` | VERIFIED | 506 lines, `reviser_app` with `liste`, `approuver`, `rejeter`, `recategoriser`, `journal` commands; all wired to pending/feedback modules |
| `data/llm_log/categorisations.jsonl` | INFO | Not yet created — directory created lazily on first real LLM API call. Code creates parent dir at call time (`_enregistrer_log` line 215). Not a gap: runtime-created artifact. |
| `tests/test_pipeline.py` | VERIFIED | 17 ML + pipeline tests, all pass |
| `tests/test_capex.py` | VERIFIED | 12 CAPEX detection tests, all pass |
| `tests/test_llm.py` | VERIFIED | 11 LLM classifier tests (mocked API), all pass |
| `tests/test_pending.py` | VERIFIED | 15 pending staging tests, all pass |
| `tests/test_feedback.py` | VERIFIED | 15 feedback/auto-rule tests, all pass |
| `tests/test_reviser.py` | VERIFIED | 17 review CLI tests, all pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pipeline.py` | `moteur.py` | `self._regles.categoriser()` | WIRED | Line 78: `resultat_regles = self._regles.categoriser(payee, narration, montant)` |
| `pipeline.py` | `ml.py` | `self._ml.predire()` | WIRED | Line 95: `resultat_ml = self._ml.predire(payee, narration, montant)` (guarded by `est_entraine`) |
| `pipeline.py` | `capex.py` | `self._capex.verifier()` | WIRED | Lines 80, 110: called on both rule-matched and AI-categorized paths |
| `llm.py` | `anthropic SDK` | `client.messages.parse()` | WIRED | Line 116: `response = client.messages.parse(model=..., output_format=ResultatClassificationLLM)` |
| `importer.py` | `pipeline.py` | `PipelineCategorisation` replaces old rules-only path | WIRED | `_creer_pipeline()` constructs `PipelineCategorisation`; `_appliquer_pipeline_et_router()` calls `pipeline.categoriser()` + `pipeline.determiner_destination()` |
| `pending.py` | `ledger/fichiers.py` | `ecrire_transactions` + `chemin_fichier_mensuel` | WIRED | Lines 21-22 imports; line 65 `ecrire_transactions(chemin_pending, texte)`; line 200-214 `chemin_fichier_mensuel` + `ecrire_transactions` in approval |
| `reviser.py` | `pending.py` | `lire_pending`, `approuver_transactions`, `rejeter_transactions` | WIRED | Lines 24-26 imports; called at lines 125, 239, 257, 286, 296, 321 |
| `reviser.py` | `feedback.py` | `enregistrer_correction` | WIRED | Line 21 import; line 348 called inside `recategoriser` command |
| `feedback.py` | `categorisation.yaml` (via regles.py) | `yaml.safe_load` + `yaml.dump` on `chemin_regles` | WIRED | `ajouter_regle_auto()` reads via `yaml.safe_load` and writes via `yaml.dump`; called by `reviser.py` line 357 |
| `app.py` | `reviser.py` | `app.add_typer(reviser_app)` | WIRED | Line 77: `from compteqc.cli.reviser import reviser_app`; line 82: `app.add_typer(reviser_app, name="reviser", ...)` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| CAT-02 | 03-01 | smart_importer ML predicts account postings from historical data | SATISFIED | `PredicteurML` (sklearn SVC) trained on approved transactions; predicts account + confidence |
| CAT-03 | 03-02 | Claude LLM categorizes remaining edge cases, constrained to closed chart of accounts list | SATISFIED | `ClassificateurLLM` validates all LLM output against `_comptes_valides`; invalid accounts fall back to Non-Classe |
| CAT-04 | 03-01 | Every categorization has a confidence score and source tag (rule/ml/llm/human) | SATISFIED | `ResultatPipeline.confiance` + `ResultatPipeline.source` always set on every code path |
| CAT-05 | 03-01 | Transactions below 80% confidence are flagged for mandatory human review | SATISFIED | `PipelineCategorisation.categoriser()` sets `revue_obligatoire=True` when `confiance < 0.80` |
| CAT-06 | 03-02 | AI-categorized transactions go to pending.beancount staging file with #pending tag | SATISFIED | `ecrire_pending()` adds "pending" tag and `!` flag to all AI-categorized transactions |
| CAT-07 | 03-03 | User can approve, reject, or recategorize pending transactions | SATISFIED | `cqc reviser approuver/rejeter/recategoriser` commands fully implemented and tested |
| CAT-08 | 03-02, 03-03 | Approved transactions move from pending to monthly ledger files | SATISFIED | `approuver_transactions()` + `_finaliser_approbation()` move to monthly files, remove #pending tag |
| CAT-09 | 03-01 | Transactions >$500 are auto-flagged as potential CAPEX with suggested CCA class | SATISFIED | `DetecteurCAPEX.verifier()`: amount threshold $500 + vendor pattern; `_suggerer_classe()` returns CCA class |
| CAT-10 | 03-03 | User corrections feed back into rule engine (auto-generate rules after N identical corrections) | SATISFIED | `enregistrer_correction()` tracks per vendor->account count; at 2 identical corrections, `ajouter_regle_auto()` writes YAML rule |
| CAT-11 | 03-02 | LLM categorizations stored with prompt/response for drift detection | SATISFIED | `_enregistrer_log()` appends JSONL with timestamp, prompt_hash, model, compte, confiance, tokens_utilises |
| CLI-02 | 03-02 | User can run categorization pipeline via CLI command | SATISFIED | `cqc importer fichier` runs full 3-tier pipeline at import time |
| CLI-03 | 03-03 | User can review and approve pending transactions via CLI | SATISFIED | `cqc reviser liste/approuver/rejeter/recategoriser` fully implemented |

All 12 requirements satisfied. No orphaned requirements found.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TODOs, FIXMEs, placeholder returns, or empty implementations found in Phase 3 source files.

---

### Test Results

```
87 phase-3 tests: all passed (test_pipeline.py: 17, test_capex.py: 12, test_llm.py: 11,
                               test_pending.py: 15, test_feedback.py: 15, test_reviser.py: 17)
Full suite: 336 passed, 7 failed
```

The 7 failures in `test_cli.py` are pre-existing regressions confirmed to exist before any Phase 3 commits (stale `include "2025/11.beancount"` in `ledger/main.beancount` and test assertion mismatches in report commands). They are NOT caused by Phase 3 work and were already documented in the 03-02 and 03-03 SUMMARYs.

---

### Human Verification Required

#### 1. End-to-End Import with Live LLM

**Test:** Run `cqc importer fichier tests/fixtures/rbc_carte_sample.csv` with `ANTHROPIC_API_KEY` set and a valid ledger.
**Expected:** LLM tier activates for unmatched transactions, produces `pending.beancount` with `#pending` tags, creates `data/llm_log/categorisations.jsonl` with at least one entry.
**Why human:** Requires live Anthropic API key and real ledger state; cannot be verified without network call.

#### 2. Review Workflow UX

**Test:** With a populated `pending.beancount`, run `cqc reviser liste`, verify the Rich table renders correctly in a terminal (not test runner) with color-coded confidence percentages, mandatory items first, separator between groups.
**Expected:** Red for <80% confidence, yellow for 80-95%, green for >95%; mandatory group appears before separator; footer shows correct counts.
**Why human:** Rich table rendering in real terminal may differ from test output; color output requires visual inspection.

#### 3. Auto-Rule Feedback Loop in Practice

**Test:** Use `cqc reviser recategoriser` twice on transactions from the same vendor with the same target account.
**Expected:** Second invocation prints "Nouvelle regle auto-generee pour {vendeur} -> {compte}" and the rule appears in `categorisation.yaml`.
**Why human:** Verifies the end-to-end correction-to-rule flow in a real ledger environment, including that subsequent imports use the new rule.

---

## Phase Goal Assessment

The phase goal is fully achieved. Transactions that the rule engine cannot categorize are processed by a substantive ML tier (sklearn SVC with Platt-scaled confidence) and a substantive LLM tier (Anthropic structured output constrained to the chart of accounts). The confidence-threshold routing (>95% direct, 80-95% pending, <80% mandatory review) is correctly implemented and tested. All AI-categorized transactions stage through `pending.beancount` with `#pending` tags before reaching the official ledger. The human review CLI (`cqc reviser`) provides all required operations: list with color-coded confidence, approve, reject, and recategorize. User corrections feed back into the rule engine with auto-rule generation after 2 identical corrections. All 87 phase-specific tests pass. Lint is clean.

---

_Verified: 2026-02-19T14:10:00Z_
_Verifier: Claude (gsd-verifier)_
