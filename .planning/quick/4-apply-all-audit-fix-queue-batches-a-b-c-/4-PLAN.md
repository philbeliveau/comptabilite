---
phase: quick-4
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/mcp/tools/ledger.py
  - src/compteqc/quebec/paie/impot_federal.py
  - src/compteqc/quebec/paie/impot_quebec.py
  - src/compteqc/quebec/rates.py
  - src/compteqc/categorisation/pipeline.py
  - src/compteqc/mcp/tools/categorisation.py
  - rules/categorisation.yaml
  - src/compteqc/categorisation/feedback.py
  - src/compteqc/categorisation/llm.py
  - src/compteqc/categorisation/ml.py
  - src/compteqc/cli/importer.py
  - rules/taxes.yaml
  - src/compteqc/quebec/pret_actionnaire/suivi.py
autonomous: true
requirements: []
---

<objective>
Apply all audit fix queue items from Batches A, B, C, and D (mechanical items only).

Purpose: Fix code bugs, categorization pipeline issues, and architecture gaps identified by the 5-agent parallel audit. These fixes prevent future misclassifications, correct tax calculations, and wire the existing tax decomposition into the import pipeline.

Output: All code fixes applied, tests passing, categorization pipeline hardened against known failure modes.
</objective>

<execution_context>
@.planning/quick/AUDIT-FIX-QUEUE.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/AUDIT-FIX-QUEUE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Batch A -- Fix code bugs (balance sheet, payroll tax, auto-approve threshold)</name>
  <files>
    src/compteqc/mcp/tools/ledger.py
    src/compteqc/quebec/paie/impot_federal.py
    src/compteqc/quebec/paie/impot_quebec.py
    src/compteqc/quebec/rates.py
    src/compteqc/categorisation/pipeline.py
    src/compteqc/mcp/tools/categorisation.py
  </files>
  <action>
    **A1 CRITICAL -- Balance sheet abs() bug:**
    In `src/compteqc/mcp/tools/ledger.py` line 193, change:
    `total_capitaux = sum(abs(v) for v in capitaux.values()) + resultat_net`
    to:
    `total_capitaux = sum(-v for v in capitaux.values()) + resultat_net`
    Equity accounts have credit (negative) balances in beancount. `-v` correctly flips them positive. `abs()` breaks contra-equity accounts like Dividendes-Declares which are debits (positive values that should reduce equity, not increase it).

    **A2 MEDIUM -- Canada Employment Amount:**
    In `src/compteqc/quebec/paie/impot_federal.py` line 20, change:
    `CREDIT_EMPLOI_CANADA = Decimal("1428")`
    to:
    `CREDIT_EMPLOI_CANADA = Decimal("1501")`
    (T4127 122nd edition Table 8.2 for 2026)

    **A3 MEDIUM -- Missing Quebec "deduction pour travailleur":**
    In `src/compteqc/quebec/paie/impot_quebec.py`, add the $1,450 deduction before the tax calculation at step 4.
    After the `revenu_annuel` calculation (line 52) and before step 2, add:
    ```python
    # Deduction pour travailleur (6% of employment income, max $1,450)
    DEDUCTION_TRAVAILLEUR = Decimal("1450")
    deduction_travailleur = min(revenu_annuel * Decimal("0.06"), DEDUCTION_TRAVAILLEUR)
    revenu_imposable = revenu_annuel - deduction_travailleur
    ```
    Then use `revenu_imposable` instead of `revenu_annuel` in the bracket lookup (line 58) and tax calculation (line 73). Remove the TODO comment about this omission. Update the module docstring to mention this deduction.

    **A4 LOW -- Federal K constants:**
    In `src/compteqc/quebec/rates.py`:
    - Line 143: `constante_k=Decimal("10237")` -> `constante_k=Decimal("10241")`
    - Line 148: `constante_k=Decimal("15680")` -> `constante_k=Decimal("15685")`
    - Line 153: `constante_k=Decimal("26019")` -> `constante_k=Decimal("26024")`

    **A5 HIGH -- Auto-approve threshold inconsistency:**
    In `src/compteqc/mcp/tools/categorisation.py` line 113, change:
    `resultat.confiance >= 0.95`
    to:
    `resultat.confiance > 0.95`
    (Harmonize with pipeline.py line 185 which already uses strict `>`)
    Also update the comment on line 110 to say `confiance > 0.95` instead of `>= 0.95`.
  </action>
  <verify>
    Run `cd /Users/philippebeliveau/Desktop/Notebook/comptabilite && python -m pytest tests/ -x -q` -- all tests pass.
    Grep to confirm no remaining `abs(v) for v in capitaux` in ledger.py.
    Grep to confirm both pipeline.py and categorisation.py use `> 0.95` (not `>=`).
  </verify>
  <done>
    Balance sheet equation correct (no abs on equity), federal employment credit at $1,501, Quebec deduction pour travailleur applied, K constants corrected, auto-approve threshold consistent across pipeline and MCP tool.
  </done>
</task>

<task type="auto">
  <name>Task 2: Batch B -- Fix categorization pipeline (rules, feedback, LLM prompt, ML training, tax rules)</name>
  <files>
    rules/categorisation.yaml
    src/compteqc/categorisation/feedback.py
    src/compteqc/categorisation/llm.py
    src/compteqc/categorisation/ml.py
    src/compteqc/cli/importer.py
    rules/taxes.yaml
  </files>
  <action>
    **B1 CRITICAL -- Fix Mollo Cafe rule:**
    In `rules/categorisation.yaml`, change the existing rule:
    ```yaml
    regles:
    - compte: Passifs:Pret-Actionnaire
      condition:
        payee: Mollo\ Cafe\ Montreal
      confiance: 0.95
      nom: auto-mollo-cafe-montreal
    ```
    (Change `Depenses:Repas-Representation` to `Passifs:Pret-Actionnaire`)

    **B2 CRITICAL -- Raise auto-rule generation threshold:**
    In `src/compteqc/categorisation/feedback.py` line 24, change:
    `SEUIL_AUTO_REGLE = 2`
    to:
    `SEUIL_AUTO_REGLE = 5`
    Update the module docstring to say "5 corrections identiques" instead of "SEUIL_AUTO_REGLE corrections identiques".

    **B3 HIGH -- Fix LLM prompt contradictions:**
    In `src/compteqc/categorisation/llm.py`:
    1. Remove lines 102-105 (the "Depot de paie" guidance block that contradicts line 91). The section starting with "Depot de paie / service de paie externe:" through the line ending with "confiance 0.70 (normalement gere par module paie)." -- delete entirely.
    2. After the REGLES STRICTES section (around line 114), add a new section:
    ```
    CORRECTIONS CONNUES (apprises des audits):
    - IMPOT SOLIDARITE GOUV. QUEBEC = credit d'impot personnel, PAS un revenu. Classe comme Passifs:Pret-Actionnaire.
    - DEPOT DE PAIE = gere par module paie, NE PAS classifier. Si vu dans import bancaire, utilise Depenses:Salaires-A-Payer avec confiance 0.60 et revue_obligatoire=true.
    - Adelard Belanger = epicerie/alimentation au marche Atwater, PAS fournitures de bureau. Classe comme Passifs:Pret-Actionnaire (depense personnelle).
    - Gros VIREMENT RECU (>500$) = source incertaine, utilise confiance 0.60 maximum et revue_obligatoire=true.
    ```

    **B4 HIGH -- Expand ML training to include Pret-Actionnaire:**
    In `src/compteqc/cli/importer.py`, function `_extraire_donnees_entrainement` (line 172+):
    Change the filter at line 188-189 from:
    ```python
    if (
        posting.account.startswith("Depenses:")
        and posting.account != "Depenses:Non-Classe"
    ):
    ```
    to:
    ```python
    if (
        (posting.account.startswith("Depenses:") or posting.account == "Passifs:Pret-Actionnaire")
        and posting.account != "Depenses:Non-Classe"
    ):
    ```
    This lets the ML model learn the most common personal expense pattern.

    **B5 MEDIUM -- Add US SaaS vendor tax rules:**
    In `rules/taxes.yaml`, under `vendeurs: > tps_seulement:`, add after the AWS entry:
    ```yaml
        - payee_regex: ".*ANTHROPIC.*"
          raison: "Fournisseur US - AI API"
        - payee_regex: ".*OPENROUTER.*"
          raison: "Fournisseur US - AI API"
        - payee_regex: ".*PERPLEXITY.*"
          raison: "Fournisseur US - AI search"
        - payee_regex: ".*RAILWAY.*"
          raison: "Fournisseur US - Cloud hosting"
        - payee_regex: ".*SPOTIFY.*"
          raison: "Fournisseur hors Quebec - streaming"
        - payee_regex: ".*MICROSOFT.*"
          raison: "Fournisseur hors Quebec - logiciels"
    ```
  </action>
  <verify>
    Run `cd /Users/philippebeliveau/Desktop/Notebook/comptabilite && python -m pytest tests/ -x -q` -- all tests pass.
    Verify `rules/categorisation.yaml` has `Passifs:Pret-Actionnaire` for Mollo Cafe.
    Verify `SEUIL_AUTO_REGLE = 5` in feedback.py.
    Verify no "Depenses:Salaires:Brut" guidance for deposits in llm.py prompt.
    Verify `rules/taxes.yaml` has 7 entries under `tps_seulement` (was 1).
  </verify>
  <done>
    Mollo Cafe rule corrected to personal expense. Auto-rule threshold raised to 5. LLM prompt contradictions removed and known corrections added. ML training includes Pret-Actionnaire. US SaaS vendors flagged for TPS-only treatment.
  </done>
</task>

<task type="auto">
  <name>Task 3: Batch C+D -- Shareholder loan year filter fix, opening balance, and mechanical data corrections</name>
  <files>
    src/compteqc/quebec/pret_actionnaire/suivi.py
    ledger/main.beancount
  </files>
  <action>
    **C2 MEDIUM -- Shareholder loan year filter fix:**
    In `src/compteqc/quebec/pret_actionnaire/suivi.py` line 116, change:
    ```python
    if entry.date.year != annee:
        continue
    ```
    to:
    ```python
    if entry.date.year > annee:
        continue
    ```
    This keeps all transactions from the current year AND prior years, so the running balance includes carry-forward. Transactions after the fiscal year-end are excluded. Add a comment: `# Include prior years for carry-forward balance`.

    **C3 MEDIUM -- Opening balance for bank account:**
    Determine the correct opening balance approach. Read `ledger/main.beancount` to find the first imported transaction date and the bank account name. Then add a pad+balance directive BEFORE the first transaction. Use the pattern:
    ```beancount
    2025-11-04 pad Actifs:Banque:RBC-Cheques Capitaux-Propres:Ouverture
    2025-11-05 balance Actifs:Banque:RBC-Cheques 0 CAD
    ```
    NOTE: The exact balance amount should be 0 CAD as a placeholder -- the user will need to look up the actual Nov 5 bank balance and update. Add a comment: `; TODO: remplacer 0 CAD par le solde reel au 2025-11-05`.

    **D1 -- Missing CSV line 22 (Dec 17 VIREMENT RECU $16.00):**
    Check if this transaction already exists in the ledger files under `ledger/2025/`. If not present, add it to the appropriate monthly file:
    ```beancount
    2025-12-17 * "VIREMENT RECU" "Virement recu"
      Actifs:Banque:RBC-Cheques  16.00 CAD
      Depenses:Non-Classe
    ```

    **D7 -- Delete duplicate CC payment:**
    Search `ledger/2025/` files for duplicate credit card payment entries. The duplicate is: a Visa-side entry for a CC payment that also appears on the chequing side. Find and remove the duplicate (keep the chequing-side entry which is the canonical inter-account transfer).

    **D2-D6 -- Items requiring human review:**
    Do NOT apply these changes. Instead, create a file `.planning/quick/4-apply-all-audit-fix-queue-batches-a-b-c-/HUMAN-REVIEW-NEEDED.md` listing:
    - D2: Amazon $31.68 -- need to know what was purchased to classify correctly
    - D3: 7 restaurant/bar transactions -- need business purpose documentation
    - D4: Belair insurance -- need to confirm auto vs home insurance type
    - D5: Fizz telecom -- need personal vs business usage percentage
    - D6: Full payroll journal entries -- need pay stub details for each DEPOT DE PAIE period

    **C1 (Tax decomposition) is OUT OF SCOPE for this plan** -- it is a larger architecture change that should be planned separately as it involves wiring tax modules into the import pipeline.
  </action>
  <verify>
    Run `cd /Users/philippebeliveau/Desktop/Notebook/comptabilite && python -m pytest tests/ -x -q` -- all tests pass.
    Verify shareholder loan suivi.py no longer filters `!= annee` (uses `> annee`).
    Verify pad/balance directives exist in ledger for bank opening balance.
    Verify HUMAN-REVIEW-NEEDED.md exists with D2-D6 items.
    Run `cd /Users/philippebeliveau/Desktop/Notebook/comptabilite && python -c "from beancount.loader import load_file; e,_,_ = load_file('ledger/main.beancount'); print(f'{len(e)} entries loaded')"` -- ledger loads without errors.
  </verify>
  <done>
    Shareholder loan tracks prior-year carry-forward. Bank opening balance has pad/balance placeholder. Missing CSV line imported. Duplicate CC payment removed. Human review items documented for user action.
  </done>
</task>

</tasks>

<verification>
1. All tests pass: `python -m pytest tests/ -x -q`
2. Ledger loads cleanly: `python -c "from beancount.loader import load_file; load_file('ledger/main.beancount')"`
3. Balance sheet equation holds (verify with MCP bilan tool or CLI)
4. No remaining abs() on equity in ledger.py
5. Auto-approve threshold consistent (> 0.95 in both files)
</verification>

<success_criteria>
- Batch A: All 5 code bugs fixed (A1-A5)
- Batch B: All 5 categorization pipeline issues fixed (B1-B5)
- Batch C: C2 (shareholder loan) and C3 (opening balance) applied; C1 (tax decomposition) deferred to separate plan
- Batch D: D1 and D7 mechanical fixes applied; D2-D6 documented for human review
- All existing tests pass
- Ledger loads without beancount errors
</success_criteria>

<output>
After completion, create `.planning/quick/4-apply-all-audit-fix-queue-batches-a-b-c-/4-SUMMARY.md`
</output>
