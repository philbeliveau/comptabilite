---
phase: quick-13
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/fava_ext/tableau_bord/__init__.py
  - src/compteqc/fava_ext/tableau_bord/templates/TableauBordExtension.html
autonomous: true
requirements: [QUICK-13]

must_haves:
  truths:
    - "Dashboard shows a clear green/red indicator of whether the ledger is balanced (debits == credits)"
    - "User can see the exact imbalance amount when the ledger is NOT balanced"
    - "Beancount balance assertions concept is documented inline for the user"
  artifacts:
    - path: "src/compteqc/fava_ext/tableau_bord/__init__.py"
      provides: "Balance verification computation in dashboard KPIs"
      contains: "equilibre"
    - path: "src/compteqc/fava_ext/tableau_bord/templates/TableauBordExtension.html"
      provides: "Visual balance status indicator on dashboard"
      contains: "equilibre"
  key_links:
    - from: "src/compteqc/fava_ext/tableau_bord/__init__.py"
      to: "src/compteqc/rapports/balance_verification.py"
      via: "BalanceVerification.extract_data() equilibre field"
      pattern: "BalanceVerification|equilibre"
---

<objective>
Add a visible double-entry validation status indicator to the Fava dashboard, and surface balance assertion gaps in the ledger.

Purpose: The user wants to understand and SEE whether their ledger passes fundamental double-entry validation (debits == credits). Currently, the balance verification exists in `compteqc.rapports.balance_verification` and `compteqc.echeances.verification`, but is only accessible via CLI (`cqc rapport balance` and `cqc cpa verifier`). The dashboard -- the primary UI -- shows no indication of ledger health. This task surfaces that validation prominently.

Output: Dashboard with balance health KPI, ledger with balance assertions where appropriate.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/compteqc/fava_ext/tableau_bord/__init__.py
@src/compteqc/fava_ext/tableau_bord/templates/TableauBordExtension.html
@src/compteqc/rapports/balance_verification.py
@src/compteqc/echeances/verification.py
@src/compteqc/mcp/services.py
@ledger/main.beancount
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add balance health KPI to dashboard</name>
  <files>
    src/compteqc/fava_ext/tableau_bord/__init__.py
    src/compteqc/fava_ext/tableau_bord/templates/TableauBordExtension.html
  </files>
  <action>
In `TableauBordExtension.__init__.py`, add a `_compute_balance_health()` method called from `after_load_file()`:

1. Import `BalanceVerification` from `compteqc.rapports.balance_verification` and reuse its `extract_data()` logic, OR directly compute using `calculer_soldes` (already imported). The simpler approach: iterate all accounts from `calculer_soldes(self.ledger.all_entries)`, sum all balances. In a correct double-entry system, the sum of ALL account balances (assets + liabilities + equity + income + expenses) must equal zero (Beancount convention). Compute:
   - `total_all = sum(soldes.values())` -- should be Decimal("0") if balanced
   - `equilibre = (total_all == Decimal("0"))`
   - Also compute debit/credit split like `balance_verification.py` does: positive balances = debits, negative = credits (in absolute value). Check `total_debit == total_credit`.

2. Store in `_kpis` dict two new keys:
   - `"equilibre"`: bool (True if balanced)
   - `"ecart"`: Decimal (the imbalance amount, 0 if balanced)

3. Add a public method `balance_health()` returning `{"equilibre": bool, "ecart": Decimal}`.

4. In the template `TableauBordExtension.html`, add a 6th KPI card AFTER the "En attente" card:
   ```html
   <div class="cqc-kpi">
     <div class="cqc-kpi-label">Equilibre comptable</div>
     <div class="cqc-kpi-value {{ 'cqc-success' if kpis.equilibre else 'cqc-error' }}">
       {% if kpis.equilibre %}
         Equilibre
       {% else %}
         Ecart: {{ "{:,.2f}".format(kpis.ecart) }} $
       {% endif %}
     </div>
   </div>
   ```

This gives an at-a-glance green "Equilibre" or red "Ecart: X.XX $" indicator on every dashboard load.

5. Also add a small explanatory tooltip or subtitle under the KPI label:
   `<span class="cqc-text-muted" style="font-size: var(--cqc-font-xs);">Debits = Credits</span>`

This serves as inline documentation of the concept for the user.
  </action>
  <verify>
Run `cd /Users/philippebeliveau/Desktop/Notebook/comptabilite && python -c "from compteqc.fava_ext.tableau_bord import TableauBordExtension; print('import ok')"` to confirm no import errors. Run existing tests: `python -m pytest tests/test_fava_ext.py -x -q` to ensure nothing broke.
  </verify>
  <done>Dashboard template contains a 6th KPI card showing "Equilibre comptable" with green/red status. The `_compute_kpis` or new `_compute_balance_health` method computes the balance check. Existing tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Add balance assertions to ledger and document the concept</name>
  <files>
    ledger/main.beancount
  </files>
  <action>
1. In `ledger/main.beancount`, uncomment and activate the pad/balance assertion pattern that is currently commented out (lines 13-15). Since we do not know the real opening balance yet, add a CLEAR comment block explaining the concept instead of dummy values:

```beancount
; ============================================================
; BALANCE ASSERTIONS (double-entry validation)
; ============================================================
; Beancount verifies balance assertions at load time.
; If the asserted amount does not match the computed balance,
; Beancount raises an error -- this is the primary mechanism
; for catching data entry mistakes and import errors.
;
; How it works:
;   YYYY-MM-DD balance Account:Name  AMOUNT CURRENCY
;   Beancount checks that on YYYY-MM-DD, Account:Name has
;   exactly AMOUNT. If not, it flags an error.
;
; pad + balance pair:
;   YYYY-MM-DD pad Account:Name  Equity:Opening
;   YYYY-MM-DD+1 balance Account:Name  AMOUNT CURRENCY
;   "pad" auto-generates a transaction to make the balance match.
;   Use this for opening balances.
;
; Recommended: Add a balance assertion after each bank statement
; reconciliation, e.g.:
;   2026-02-01 balance Actifs:Banque:RBC:Cheques  12345.67 CAD
;
; TODO: Add real opening balance once known:
;   2025-11-04 pad Actifs:Banque:RBC:Cheques Capital:Ouverture
;   2025-11-05 balance Actifs:Banque:RBC:Cheques XXXXX.XX CAD
; ============================================================
```

2. This serves as living documentation right in the ledger file where the user will naturally see it, explaining: (a) what balance assertions are, (b) how pad works, (c) when to use them.

No code changes beyond the comment block -- we do not want to add fake balance assertions that would fail.
  </action>
  <verify>
Run `cd /Users/philippebeliveau/Desktop/Notebook/comptabilite && python -c "from beancount import loader; entries, errors, opts = loader.load_file('ledger/main.beancount'); print(f'{len(entries)} entries, {len(errors)} errors')"` to confirm the ledger still loads without new errors.
  </verify>
  <done>main.beancount contains a clear documentation block explaining balance assertions, pad directives, and recommended usage patterns. The ledger loads without errors.</done>
</task>

</tasks>

<verification>
1. `python -m pytest tests/ -x -q` -- all existing tests pass
2. Dashboard template has 6 KPI cards (was 5), the 6th shows balance status
3. `ledger/main.beancount` contains balance assertion documentation block
4. Fava can load without errors: `python -c "from beancount import loader; loader.load_file('ledger/main.beancount')"`
</verification>

<success_criteria>
- Dashboard prominently shows green "Equilibre" or red "Ecart: X.XX $" indicator
- User understands the concept from inline documentation in both the dashboard tooltip and the beancount file comments
- Existing CLI commands (`cqc rapport balance`, `cqc cpa verifier`) continue to work unchanged
- No test regressions
</success_criteria>

<output>
After completion, create `.planning/quick/13-document-and-surface-double-entry-valida/13-SUMMARY.md`
</output>
