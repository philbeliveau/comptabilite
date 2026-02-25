---
status: complete
phase: 01-ledger-foundation-and-import-pipeline
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md]
started: 2026-02-19T13:15:00Z
updated: 2026-02-19T13:25:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Import real RBC CSV (mixed Cheques + Visa)
expected: `cqc importer fichier testing-documents/csv4883.csv` imports 159 transactions (61 cheques + 98 visa) from the combined file. Auto-detects mixed format. bean-check passes. Git commit created. Two tables show unclassified transactions with correct dates, amounts, beneficiaries.
result: pass

### 2. Deduplication on re-import
expected: Running the same import command a second time reports "Aucune nouvelle transaction" for both accounts. Zero duplicates enter the ledger.
result: pass

### 3. Account balances after import
expected: `cqc soldes` shows three accounts with non-zero balances: Actifs:Banque:RBC:Cheques, Passifs:CartesCredit:RBC, and Depenses:Non-Classe. The amounts reflect real bank activity.
result: pass

### 4. Balance sheet equation
expected: `cqc rapport bilan` displays Actifs, Passifs, and Capitaux propres. The accounting equation is verified: Actifs = Passifs + Capitaux propres. Message confirms "Equation comptable verifiee".
result: pass

### 5. Unclassified transaction review
expected: `cqc revue` lists all 159 transactions as non-classified (since no categorization rules exist yet). Shows date, amount, beneficiary, and narration for each. Beneficiary names are cleaned up (Title Case, no trailing reference numbers).
result: pass

### 6. Transaction data accuracy spot-check
expected: Spot-check a few real transactions against the CSV: Hydro-Quebec payments should be -81.14 CAD, Claude.AI subscription should be -321.93 CAD on Visa, Depot De Paie amounts match source. No amounts are wrong or missing.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
