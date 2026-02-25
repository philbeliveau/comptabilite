---
phase: quick-8
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/cli/importer.py
  - src/compteqc/categorisation/pipeline.py
  - src/compteqc/categorisation/pending.py
  - tests/test_pipeline.py
  - tests/test_cli.py
autonomous: true
requirements: [QUICK-8]

must_haves:
  truths:
    - "CLI accepts --source-type corporate|personal flag (default: corporate)"
    - "Personal source transactions skip categorization/ML/LLM/CAPEX and route directly to Passifs:Pret-Actionnaire"
    - "Corporate source transactions follow normal pipeline unchanged"
    - "Personal transactions land in monthly ledger files directly (not pending), with flag * and source_type=personal metadata"
  artifacts:
    - path: "src/compteqc/cli/importer.py"
      provides: "--source-type CLI flag plumbing"
      contains: "source_type"
    - path: "src/compteqc/categorisation/pipeline.py"
      provides: "Personal short-circuit logic"
      contains: "source_type"
  key_links:
    - from: "src/compteqc/cli/importer.py"
      to: "src/compteqc/categorisation/pipeline.py"
      via: "source_type param passed through _appliquer_pipeline_et_router"
      pattern: "source_type.*personal"
---

<objective>
Add --source-type corporate|personal flag to the import CLI so personal bank account CSVs
route all transactions directly to Passifs:Pret-Actionnaire, skipping the entire categorization
pipeline (rules, ML, LLM, CAPEX). Only inter-account transfers matter from personal accounts.

Purpose: Personal bank CSVs need no classification -- everything is a shareholder loan entry.
Corporate imports continue through the normal 3-tier pipeline unchanged.

Output: Modified CLI, pipeline, and tests.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/compteqc/cli/importer.py
@src/compteqc/categorisation/pipeline.py
@src/compteqc/categorisation/pending.py
@src/compteqc/ingestion/rbc_cheques.py
@src/compteqc/ingestion/rbc_carte.py
@tests/test_pipeline.py
@tests/test_cli.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add --source-type flag to CLI and wire personal short-circuit through pipeline</name>
  <files>
    src/compteqc/cli/importer.py
    src/compteqc/categorisation/pipeline.py
  </files>
  <action>
1. In `cli/importer.py`, add a `--source-type` / `-s` Typer Option to the `fichier` command:
   - Type: `str` with default `"corporate"`
   - Help text: `"Type de source : corporate (normal) ou personal (tout -> Pret-Actionnaire)"`
   - Validate early: if value not in ("corporate", "personal"), print error and `raise typer.Exit(1)`

2. In `cli/importer.py`, modify `_appliquer_pipeline_et_router` to accept a `source_type: str = "corporate"` parameter:
   - If `source_type == "personal"`:
     - Skip ALL pipeline logic (no categoriser() call, no CAPEX)
     - Replace the second posting account (Depenses:Non-Classe) with "Passifs:Pret-Actionnaire"
     - Build a ResultatPipeline with: compte="Passifs:Pret-Actionnaire", confiance=1.0, source="personal", regle=None, est_capex=False, classe_dpa=None, revue_obligatoire=False, suggestions=None
     - Set meta["categorisation"] = "personal"
     - Set meta["source_type"] = "personal"
     - Set txn flag to "*" (auto-approved, no human review needed)
     - Return (txn_modified, "direct", resultat)
   - If `source_type == "corporate"`: existing logic unchanged

3. In `cli/importer.py`, pass `source_type` from `fichier()` through `_importer_avec()` (add parameter) down to `_appliquer_pipeline_et_router()`.

4. In `cli/importer.py`, when `source_type == "personal"`, skip creating the pipeline entirely in `_importer_avec()`. The `_creer_pipeline()` call is unnecessary -- guard it with `if source_type != "personal"`. For personal, pass `pipeline=None` conceptually (the short-circuit in `_appliquer_pipeline_et_router` handles it before pipeline is used).

5. In `pipeline.py`, add `source` field value "personal" to the ResultatPipeline docstring for completeness (source: str comment line).

6. In the summary table printed by `fichier()`, when source_type is personal, print a line: "Source: personnel (tout -> Pret-Actionnaire)" before the table.
  </action>
  <verify>
    Run `cd /Users/philippebeliveau/Desktop/Notebook/comptabilite && python -c "from compteqc.cli.importer import fichier; print('import ok')"` to confirm no import errors.
    Run `python -m compteqc.cli.app importer fichier --help` and confirm --source-type appears.
  </verify>
  <done>
    --source-type flag visible in CLI help. Personal source_type short-circuits pipeline and routes to Passifs:Pret-Actionnaire with flag "*" and source="personal". Corporate path unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add tests for personal source-type pipeline short-circuit</name>
  <files>
    tests/test_pipeline.py
    tests/test_cli.py
  </files>
  <action>
1. In `tests/test_pipeline.py`, add tests:
   - `test_personal_source_type_skips_pipeline`: Create a mock transaction with Depenses:Non-Classe posting. Call `_appliquer_pipeline_et_router(txn, pipeline=None, source_type="personal")`. Assert:
     - Returned destination == "direct"
     - Returned resultat.compte == "Passifs:Pret-Actionnaire"
     - Returned resultat.source == "personal"
     - Returned resultat.confiance == 1.0
     - Returned resultat.est_capex == False
     - Transaction posting account changed from Non-Classe to Passifs:Pret-Actionnaire
     - Transaction flag == "*"
     - Transaction meta has source_type="personal"

   - `test_corporate_source_type_uses_normal_pipeline`: Verify that calling with source_type="corporate" still calls pipeline.categoriser() (use a mock pipeline).

2. In `tests/test_cli.py`, add test:
   - `test_source_type_option_validation`: Use Typer CliRunner to invoke `fichier` with `--source-type invalid` and assert exit code 1 with error message.
   - `test_source_type_default_is_corporate`: Verify the default by checking the Typer parameter default (or by examining the function signature).

Import `_appliquer_pipeline_et_router` from `compteqc.cli.importer` for direct unit testing.
  </action>
  <verify>
    Run `cd /Users/philippebeliveau/Desktop/Notebook/comptabilite && python -m pytest tests/test_pipeline.py tests/test_cli.py -v -x --tb=short 2>&1 | tail -30` and confirm all new tests pass.
    Run full suite: `python -m pytest tests/ -x --tb=short` to verify no regressions.
  </verify>
  <done>
    All new tests pass. Full test suite green. Personal short-circuit tested at unit level. CLI validation tested.
  </done>
</task>

</tasks>

<verification>
- `cqc importer fichier --help` shows `--source-type` option
- `cqc importer fichier some.csv --source-type personal` routes all transactions to Passifs:Pret-Actionnaire
- `cqc importer fichier some.csv` (no flag) uses normal corporate pipeline
- `python -m pytest tests/ -x` all green
</verification>

<success_criteria>
- Personal source transactions bypass rules/ML/LLM/CAPEX entirely
- Personal transactions go directly to monthly files (not pending) with flag "*"
- Corporate imports are completely unchanged
- All existing and new tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/8-add-source-type-corporate-personal-flag-/8-SUMMARY.md`
</output>
