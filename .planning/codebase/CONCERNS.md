# Codebase Concerns

**Analysis Date:** 2026-02-25

---

## Tech Debt

**Hardcoded absolute path in ledger:**
- Issue: One document directive in `ledger/main.beancount` (line 34) contains a hardcoded absolute path `/Users/philippebeliveau/Desktop/Notebook/comptabilite/ledger/documents/2026/02/2026-01-31.anthropic-pbc.15.pdf`. This breaks on any other machine or if the project is moved.
- Files: `ledger/main.beancount`
- Impact: Fava document link is non-portable; breaks ledger loading on any other environment.
- Fix approach: Replace with a relative path like `documents/2026/02/2026-01-31.anthropic-pbc.15.pdf`. The `ecrire_directive` in `src/compteqc/documents/beancount_link.py` already writes absolute paths — that function should write relative paths instead.

**Opening balance is missing (commented out):**
- Issue: `ledger/main.beancount` lines 12-16 show the `pad` and `balance` opening-balance directives are commented out with placeholder `XXXXX.XX`. The ledger has no verified starting balance.
- Files: `ledger/main.beancount`
- Impact: All balance sheet figures and account balances are unreliable. The CPA package cannot be correct without an accurate opening balance. Any balance verification against bank statements will fail.
- Fix approach: Obtain the actual bank balance on the first transaction date (2025-11-04) and uncomment the directives with the real value.

**sklearn/numpy are implicit dependencies not declared in pyproject.toml:**
- Issue: `src/compteqc/categorisation/ml.py` imports `numpy` and `sklearn` (scikit-learn) at module level, but neither package appears in `pyproject.toml` dependencies.
- Files: `src/compteqc/categorisation/ml.py`, `pyproject.toml`
- Impact: A fresh `uv sync` will not install these packages. The ML tier of the categorisation pipeline will crash at runtime with an `ImportError`. Tests that import `PredicteurML` will also fail in a clean environment.
- Fix approach: Add `numpy>=1.26` and `scikit-learn>=1.4` to `[project.dependencies]` in `pyproject.toml`.

**`_ajuster_jour_ouvrable` is a private function imported cross-module:**
- Issue: `src/compteqc/echeances/remises.py` imports the private function `_ajuster_jour_ouvrable` directly from `src/compteqc/echeances/calendrier.py`. Importing private symbols across module boundaries is fragile.
- Files: `src/compteqc/echeances/remises.py`, `src/compteqc/echeances/calendrier.py`
- Impact: Any internal refactor of `calendrier.py` will silently break `remises.py`.
- Fix approach: Make `_ajuster_jour_ouvrable` a public function (`ajuster_jour_ouvrable`) or move it to a shared utility module.

**`beancount_link.ecrire_directive` writes to files named `YYYY-M.beancount`, not `YYYY/MM.beancount`:**
- Issue: `src/compteqc/documents/beancount_link.py` line 51 constructs the path as `ledger_dir / f"{annee}-{mois:02d}.beancount"` (flat naming). The actual ledger structure is `ledger/YYYY/MM.beancount` (subdirectory naming, created by `src/compteqc/ledger/fichiers.py`).
- Files: `src/compteqc/documents/beancount_link.py`
- Impact: Document directives written via this function go to non-existent or unincluded files, so they are never loaded by Fava/beancount.
- Fix approach: Use `chemin_fichier_mensuel(annee, mois, ledger_dir)` from `src/compteqc/ledger/fichiers.py` and call `ajouter_include` to ensure the file is included in `main.beancount`.

**ML model is not persisted between runs:**
- Issue: `src/compteqc/categorisation/ml.py` trains the SVC model in memory per CLI invocation. There is no `save`/`load` (e.g., `joblib.dump`/`joblib.load`). Every import run re-trains from scratch.
- Files: `src/compteqc/categorisation/ml.py`
- Impact: As the approved-transaction history grows, training time increases linearly. The ML tier provides no benefit unless the model is loaded from a previous training run. Currently, the model is retrained from zero on every `cqc import` call.
- Fix approach: Add `sauvegarder(chemin: Path)` and `charger(chemin: Path)` methods using `joblib`. Persist to `data/ml_model/predicteur.joblib` and retrain only when new approved transactions are available.

**Feedback-generated auto-rules are not persisted to the active rules file automatically:**
- Issue: `src/compteqc/categorisation/feedback.py` returns a `Regle` object when the correction count threshold is reached, but `ajouter_regle_auto` is a separate function that callers must invoke. The CLI (`reviser.py`) does call it, but the MCP `rejeter` tool does not call `enregistrer_correction` or `ajouter_regle_auto` at all.
- Files: `src/compteqc/mcp/tools/approbation.py`, `src/compteqc/categorisation/feedback.py`
- Impact: Corrections made via MCP/Claude do not feed the learning loop. Rule auto-generation only works through the CLI `reviser` workflow.
- Fix approach: Wire `enregistrer_correction` + `ajouter_regle_auto` into the `rejeter` MCP tool when `compte_corrige` is provided.

---

## Known Bugs

**137 pending transactions are accumulating without being reviewed:**
- Symptoms: `ledger/pending.beancount` has 137 `#pending` transactions, including several "Depot De Paie" entries and "Vir Courriel" entries with dubious classification. Some salary transactions are routed to `Passifs:Salaires-A-Payer` which is wrong (should go through the payroll module).
- Files: `ledger/pending.beancount`
- Trigger: Arises when `cqc import` was run with low-confidence LLM results; items were queued but never reviewed.
- Workaround: Run `cqc reviser liste` and process the queue, or use the Approbation Fava extension.

**Upload endpoint saves to flat `documents/` dir before `telecharger_recu` moves it to the dated subdirectory:**
- Symptoms: In `src/compteqc/fava_ext/recus/__init__.py` lines 102-103, the uploaded file is first saved to `documents/<original_filename>`, then `telecharger_recu` copies it again to `documents/YYYY/MM/`. The original copy in `documents/` is never deleted.
- Files: `src/compteqc/fava_ext/recus/__init__.py`, `src/compteqc/documents/upload.py`
- Trigger: Every receipt upload via the Fava UI.
- Workaround: Manually delete orphaned files in `ledger/documents/` that are not under a `YYYY/MM/` subdirectory.

**`_corriger_pending` in MCP approbation only updates postings starting with `Depenses:`:**
- Symptoms: `src/compteqc/mcp/tools/approbation.py` line 227 — `if posting.account.startswith("Depenses:")`. Revenue corrections (`Revenus:`) or liability corrections (`Passifs:`) are silently ignored.
- Files: `src/compteqc/mcp/tools/approbation.py`
- Trigger: Use `rejeter` with a `compte_corrige` that targets a non-expense account.
- Workaround: Manually edit `pending.beancount` for non-expense account corrections.

---

## Security Considerations

**API keys loaded via `load_dotenv()` at module import time:**
- Risk: `src/compteqc/categorisation/llm.py` and `src/compteqc/documents/extraction.py` both call `load_dotenv()` at module level. If `.env` is present but malformed, or if the module is imported in a test context, secrets may be loaded unexpectedly.
- Files: `src/compteqc/categorisation/llm.py` (line 25), `src/compteqc/documents/extraction.py` (line 15)
- Current mitigation: `.env` is in `.gitignore`. API clients are lazy-initialized.
- Recommendations: Move `load_dotenv()` to the CLI entrypoint (`src/compteqc/cli/app.py`) only. Tests should never depend on `.env` being present.

**LLM log file at `data/llm_log/categorisations.jsonl` contains transaction payee/narration data:**
- Risk: The JSONL log includes real payee names and transaction amounts for every LLM classification. It is in `.gitignore` locally, but if `data/` is ever synced or backed up carelessly, sensitive financial data is exposed.
- Files: `src/compteqc/categorisation/llm.py` (line 320), `data/llm_log/`
- Current mitigation: `.gitignore` excludes `data/llm_log/`.
- Recommendations: Document that `data/` must not be committed or synced to shared cloud storage without encryption.

**MCP server has no authentication layer:**
- Risk: The MCP server (`src/compteqc/mcp/server.py`) communicates via stdio. If the stdio transport is ever exposed as HTTP/SSE (e.g., for remote access), there is no auth token or API key validation.
- Files: `src/compteqc/mcp/server.py`
- Current mitigation: stdio transport only; local use.
- Recommendations: Before adding any network transport, implement bearer token validation.

---

## Performance Bottlenecks

**Receipt matching iterates all ledger entries on every upload:**
- Problem: `src/compteqc/documents/matching.py` `proposer_correspondances()` does a linear scan of all `entries` for every receipt upload via the Fava endpoint.
- Files: `src/compteqc/documents/matching.py`, `src/compteqc/fava_ext/recus/__init__.py`
- Cause: No index or pre-filtering by date range. As the ledger grows to thousands of entries, every upload scans everything.
- Improvement path: Pre-filter `entries` to a ±7-day window around `donnees.date` before scoring. This reduces candidates from O(N) to O(small constant).

**`calculer_soldes` in `src/compteqc/mcp/services.py` does a full ledger scan on every call:**
- Problem: All MCP tools that call `calculer_soldes` trigger a full linear pass over all entries. Multiple tools call it independently without caching.
- Files: `src/compteqc/mcp/services.py`
- Cause: No memoization or incremental update. After a `ctx.reload()`, all previously computed balances are discarded.
- Improvement path: Cache `calculer_soldes` result on `AppContext` and invalidate only on `reload()`.

**`_charger_recents` in `RecusExtension` does `rglob("*")` on every ledger load:**
- Problem: `src/compteqc/fava_ext/recus/__init__.py` line 57 calls `documents_dir.rglob("*")` in `after_load_file()`, which runs on every Fava page load.
- Files: `src/compteqc/fava_ext/recus/__init__.py`
- Cause: No caching; the filesystem is scanned on every refresh.
- Improvement path: Cache the result with an `mtime` check on `documents_dir`, or limit to a single `scandir` on the most recent dated subdirectory.

---

## Fragile Areas

**`pending.beancount` is the only staging file and is mutated in-place:**
- Files: `src/compteqc/categorisation/pending.py`, `src/compteqc/mcp/tools/approbation.py`
- Why fragile: Approval (`approuver_transactions`) reads the entire file, removes entries by index, and re-writes it. A crash between read and write leaves the file in an undefined state. The rollback logic exists but uses `contenu_pending_avant` captured at the start, which can be stale if multiple processes run concurrently (Fava and CLI both access the ledger).
- Safe modification: Always make a backup copy before calling `approuver_transactions`. Never run `cqc import` and `cqc reviser` simultaneously.
- Test coverage: `tests/test_pending.py` covers the happy path but not concurrent-write or partial-write scenarios.

**The `_construire_id` function for pending transaction identification is collision-prone:**
- Files: `src/compteqc/mcp/tools/approbation.py` (line 33)
- Why fragile: The ID is built as `f"{date}|{payee}|{narration[:20]}"`. Two transactions on the same day from the same payee with the same first 20 characters of narration will produce the same ID. This is plausible for recurring transactions (e.g., multiple coffee shop visits on the same day — 5 such entries exist in `ledger/2026/01.beancount` for "Mollo Cafe Montreal Qc").
- Safe modification: Append the montant or a zero-padded sequential index to the ID. Alternatively, use a hash of the full entry.
- Test coverage: No tests for the collision case.

**`ecrire_transactions` in `src/compteqc/ledger/fichiers.py` appends without deduplication:**
- Files: `src/compteqc/ledger/fichiers.py`
- Why fragile: If `cqc import` is run twice on the same CSV, all transactions are appended again to the monthly file, creating duplicates. There is no hash-based deduplication guard at the ledger write layer.
- Safe modification: Check the `hash_sha256` stored in the `.meta.json` archive before writing. The archive system in `normalisation.archiver_fichier` creates these, but there is no enforcement gate that reads them before import.
- Test coverage: Not tested.

**Fava extensions use `self.ledger.all_entries` which is the full loaded list, not filtered by year:**
- Files: `src/compteqc/fava_ext/taxes_qc/__init__.py`, `src/compteqc/fava_ext/dpa_qc/__init__.py`, `src/compteqc/fava_ext/paie_qc/__init__.py`
- Why fragile: Extensions compute annual summaries (payroll, taxes, DPA) by filtering `all_entries` for `datetime.date.today().year`. If transactions from prior years exist in the ledger (e.g., the `ledger/2025/` files), the filter is correct; but if the fiscal year does not match the calendar year, the calculations silently return the wrong year.
- Safe modification: Use a configurable fiscal year parameter rather than `datetime.date.today().year`.

---

## Scaling Limits

**Rates module only covers 2026:**
- Current capacity: `src/compteqc/quebec/rates.py` defines only `TAUX_2026`. The registry `TAUX: dict[int, TauxAnnuels]` has a single entry.
- Limit: Any payroll calculation, tax check, or compliance feature that calls `obtenir_taux(2025)` raises `ValueError`. The 2025/11 and 2025/12 ledger files contain payroll transactions that use 2026 rates or fail.
- Scaling path: Add `TAUX_2025` with 2025 QPP/RQAP/AE/FSS rates from official sources (T4127 121st edition). This is a low-effort, high-correctness fix.

---

## Dependencies at Risk

**`fava>=1.30` internal APIs are relied upon directly:**
- Risk: Extensions import `fava.beans.funcs.hash_entry` and use `self.ledger.file.insert_metadata` and `self.ledger.file.insert_entries` — all internal Fava APIs not part of the public extension contract.
- Impact: A Fava minor version bump can break all extension functionality without warning.
- Files: `src/compteqc/fava_ext/recus/__init__.py`
- Migration plan: Pin `fava~=1.30` in `pyproject.toml` and add an integration test that runs against the pinned version. Track Fava changelog for API changes before upgrading.

**`smart-importer>=1.2` is listed as a dependency but not used:**
- Risk: `pyproject.toml` declares `smart-importer>=1.2`, but `src/compteqc/categorisation/ml.py` uses `sklearn` directly (not via smart-importer). The dependency is dead weight.
- Impact: Unnecessary install weight; may cause version conflicts as beancount/beangulp evolve.
- Migration plan: Remove `smart-importer` from `pyproject.toml`.

---

## Missing Critical Features

**No opening balance assertion:**
- Problem: Without a `balance` directive for `Actifs:Banque:RBC:Cheques`, the ledger cannot be independently verified against RBC bank statements. There is no early-warning if a transaction is missing or double-imported.
- Blocks: CPA package accuracy; any meaningful trial balance.

**No deduplication guard at import time:**
- Problem: Re-importing a previously processed CSV silently doubles all transactions in the monthly beancount file.
- Blocks: Data integrity; prevents safe re-runs of `cqc import`.

**GST/QST amounts are not extracted from bank transactions:**
- Problem: The categorisation pipeline classifies transactions to accounts but does not parse or record TPS/TVQ amounts. The taxes module (`src/compteqc/quebec/taxes/`) calculates tax from Beancount postings after the fact, not from actual remittance data on receipts.
- Blocks: Accurate net TPS/TVQ remittance reporting; ITC claims.

---

## Test Coverage Gaps

**No tests for the Fava extension upload/link workflow:**
- What's not tested: The full HTTP round-trip through `RecusExtension.upload()` and `RecusExtension.link()` — file saving, AI extraction, receipt renaming, metadata insertion, and document directive insertion.
- Files: `src/compteqc/fava_ext/recus/__init__.py`
- Risk: Regressions in the receipt-to-transaction linking flow (the most recently developed feature) are not caught by the test suite.
- Priority: High

**No tests for duplicate-import prevention:**
- What's not tested: Running `cqc import` twice on the same file.
- Files: `src/compteqc/ledger/fichiers.py`, `src/compteqc/cli/importer.py`
- Risk: Silent data corruption through duplicated entries.
- Priority: High

**No tests for concurrent ledger writes:**
- What's not tested: Simultaneous access by Fava (web server) and CLI (`cqc reviser`).
- Files: `src/compteqc/categorisation/pending.py`
- Risk: File corruption if Fava serves a request while the CLI is mid-write.
- Priority: Medium

**Tax rate calculations are only tested for 2026:**
- What's not tested: `src/compteqc/quebec/rates.py` has no `TAUX_2025`. Tests in `tests/test_cotisations.py` and `tests/test_impot.py` only use 2026 data.
- Files: `src/compteqc/quebec/rates.py`, `tests/test_cotisations.py`, `tests/test_impot.py`
- Risk: Payroll calculations for November/December 2025 transactions use wrong (2026) rates silently.
- Priority: Medium

**No end-to-end test for the CPA package generation:**
- What's not tested: `cqc cpa package` on a ledger with real-format monthly files.
- Files: `src/compteqc/rapports/cpa_package.py`, `tests/test_cpa_package.py`
- Risk: The integration of all report modules (DPA, paie, taxes, pret) may fail silently when generating the actual ZIP.
- Priority: Medium

---

*Concerns audit: 2026-02-25*
