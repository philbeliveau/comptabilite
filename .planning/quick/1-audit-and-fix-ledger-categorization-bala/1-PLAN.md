---
phase: quick-1
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/1-audit-and-fix-ledger-categorization-bala/AUDIT-REPORT.md
autonomous: true
requirements: [AUDIT-01]
must_haves:
  truths:
    - "Every transaction in pending.beancount, 01.beancount, 02.beancount is audited"
    - "Each issue is categorized by severity (CRITICAL, HIGH, MEDIUM, LOW)"
    - "Each issue includes the current wrong entry and the proposed correct entry"
    - "Double-counting risks are identified with specific line references"
    - "Personal-vs-corporate boundary violations are flagged"
    - "A summary table shows total financial impact of misclassifications"
  artifacts:
    - path: ".planning/quick/1-audit-and-fix-ledger-categorization-bala/AUDIT-REPORT.md"
      provides: "Comprehensive audit of all 159 transactions"
      min_lines: 200
  key_links: []
---

<objective>
Produce a comprehensive audit report of all 159 transactions imported from csv4883.csv, documenting every categorization error, accounting mistake, and structural issue found across ledger/pending.beancount, ledger/2026/01.beancount, and ledger/2026/02.beancount.

Purpose: Enable the user to review all issues at once and approve corrections before any ledger modifications are made.
Output: A single AUDIT-REPORT.md with severity-ranked findings, correct account mappings, and financial impact summary.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@ledger/pending.beancount
@ledger/2026/01.beancount
@ledger/2026/02.beancount
@ledger/comptes.beancount
@ledger/main.beancount
</context>

<tasks>

<task type="auto">
  <name>Task 1: Parse all transactions and cross-reference with known issues</name>
  <files>.planning/quick/1-audit-and-fix-ledger-categorization-bala/AUDIT-REPORT.md</files>
  <action>
Read every transaction in the three beancount files (pending.beancount, 2026/01.beancount, 2026/02.beancount). For each transaction, evaluate:

1. Is the account classification correct given the payee/description?
2. Is the debit/credit direction correct?
3. Are metadata flags (capex, confiance) accurate?
4. Is there a double-counting risk with another transaction?
5. Is this a personal expense incorrectly booked as corporate?

Produce AUDIT-REPORT.md with this structure:

## Header
- Date of audit, scope (csv4883.csv, 159 transactions), files audited

## Executive Summary
- Total transactions audited
- Number of issues by severity
- Estimated financial impact of misclassifications (inflated expenses, missing shareholder loan entries, etc.)

## Issues by Severity

### CRITICAL (breaks accounting integrity)
For each issue:
- **Issue ID**: e.g., CRIT-01
- **Transactions affected**: CSV line numbers, dates, amounts, payees
- **Current entry**: The exact beancount posting as-is
- **Problem**: What is wrong and why
- **Correct entry**: The exact beancount posting it should be
- **Impact**: Dollar amount affected, which accounts are over/understated

Known CRITICAL issues to document:
1. DEPOT DE PAIE classified as Depenses:Salaires:Brut (lines 3,8,14,26,49) -- these are NET PAY deposits, not gross salary expense. Should clear Passifs:Salaires-A-Payer or be flagged as needing full payroll journal entries.
2. IMPOT SOLIDARITE classified as Revenus:Autres (lines 2,16,33,56) -- personal tax credit deposited in corp account = shareholder loan (Passifs:Pret-Actionnaire).
3. PAIEMENT AUTOMATISE credit card payment (line 110) -- both sides post to Passifs:CartesCredit:RBC, netting to zero. Should be Dr CartesCredit:RBC / Cr Actifs:Banque:RBC:Cheques, BUT must check for duplicate with chequing-side entry.
4. TPS CANADA GST refund (line 34) -- classified as Depenses:TPS-Remise credit, should reduce Actifs:TPS-Payee or Passifs:TPS-Percue.

### HIGH (wrong classification with tax impact)
5. SAAQ-IMMATRIC as Vehicule:Assurance (line 47) -- registration, not insurance. Also flag: is vehicle corporate or personal?
6. Mollo Cafe x18 as Repas-Representation (01.beancount, 02.beancount) -- personal coffee, should be Pret-Actionnaire. Total dollar amount to calculate.
7. LS Muni GC as Vehicule:Stationnement (line 79) -- restaurant/bar, should be Pret-Actionnaire.
8. Adelard Belanger as Bureau:Fournitures (lines 75,105) -- grocery vendor, should be Pret-Actionnaire.
9. Restaurant Grinder $323.64 as Repas-Representation (line 151) -- Feb 13 Valentine's dinner, likely personal.
10. VIREMENT ENVOYE $1,775 x3 with capex:"oui" flag (lines 12,30,53) -- rent is opex, capex flag is wrong.

### MEDIUM (questionable but defensible)
11. HYDRO-QUEBEC as Bureau:Entretien -- acceptable but imprecise (utilities vs maintenance).
12. Amazon $31.68 as Bureau:Abonnements-Logiciels (line 115) -- unknown purchase, needs receipt review.
13. REQ annual registration fee as Impots:Quebec (line 65) -- should be Honoraires-Professionnels:Autres or government fees.
14. Other cafes (Bloom, 49th Parallel, Stash) -- likely personal unless business purpose documented.

### LOW (metadata/cosmetic)
15. Spurious capex:"oui" flags on non-capital items (DEPOT DE PAIE line 3, VIREMENT RECU line 6).
16. Missing transaction check: verify CSV line 22 (Dec 17 VIREMENT RECU $16.00) is present.

## Double-Counting Analysis
- Map all credit card payment transactions from both chequing and Visa perspectives
- Confirm whether any are actually double-counted or just broken entries

## Shareholder Loan Summary
- List all transactions that should be Pret-Actionnaire (personal expenses in corp account)
- Calculate total shareholder loan balance impact

## Chart of Accounts Gaps
- Note any accounts that should exist but don't (e.g., Depenses:Vehicule:Immatriculation, Depenses:Bureau:Electricite, Depenses:Frais-Gouvernement)

## Recommended Next Steps
- Numbered list of correction batches for user approval
  </action>
  <verify>
1. File exists at .planning/quick/1-audit-and-fix-ledger-categorization-bala/AUDIT-REPORT.md
2. File contains all 16+ known issues documented above
3. Each issue has: ID, affected lines, current entry, problem description, correct entry, dollar impact
4. Executive summary has total counts and financial impact estimate
5. Double-counting section analyzes credit card payment pairs
6. Shareholder loan section totals all personal expenses
  </verify>
  <done>
AUDIT-REPORT.md exists with every known categorization issue documented, severity-ranked, with current-vs-correct entries and financial impact. The user can review the report and approve correction batches without needing to re-examine individual transactions.
  </done>
</task>

</tasks>

<verification>
- AUDIT-REPORT.md covers all 159 transactions (or explicitly notes any missing)
- Every issue from the planning context analysis is represented
- Financial impact is quantified (total misclassified dollars by category)
- No corrections are applied to the ledger files -- this is audit only
</verification>

<success_criteria>
- Complete audit report exists documenting 16+ issues across 4 severity levels
- Each issue has actionable correction details (exact beancount entries)
- User can approve/reject each correction independently
- Total financial impact of misclassifications is quantified
</success_criteria>

<output>
After completion, create `.planning/quick/1-audit-and-fix-ledger-categorization-bala/1-SUMMARY.md`
</output>
