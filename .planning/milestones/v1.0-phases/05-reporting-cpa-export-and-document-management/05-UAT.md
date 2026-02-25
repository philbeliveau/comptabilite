---
status: complete
phase: 05-reporting-cpa-export-and-document-management
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md, 05-04-SUMMARY.md, 05-05-SUMMARY.md]
started: 2026-02-19T22:00:00Z
updated: 2026-02-19T22:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Generate Trial Balance CSV
expected: Running `cqc rapport balance` produces a trial balance with account names, debit/credit columns, grouped by category. Totals must balance.
result: pass

### 2. Generate Income Statement
expected: Running `cqc rapport resultats` shows revenue, expenses by category, and net income (resultat net).
result: pass

### 3. Generate Balance Sheet
expected: Running `cqc rapport bilan` shows Actifs, Passifs, Capitaux Propres. Accounting equation should hold.
result: issue
reported: "Balance sheet shows Actifs = -1,732.20, Total Passifs + Capitaux = -1,513.20 with AVERTISSEMENT: L'equation comptable ne balance pas! Difference: -219.00 CAD. Likely caused by test data inconsistency (dividendes-declares without matching equity), not a code bug."
severity: minor

### 4. GIFI Export for TaxCycle
expected: GIFI export produces CSV with GIFI codes and aggregated amounts. Tested via CPA package ZIP which includes gifi/gifi_s100.csv and gifi/gifi_s125.csv.
result: pass

### 5. Create Invoice via CLI
expected: `cqc facture creer` creates an invoice with correct GST (5%) and QST (9.975%). $10,000 -> $11,497.50. Sequential FAC-YYYY-NNN number.
result: pass

### 6. Generate Invoice PDF
expected: `cqc facture pdf FAC-YYYY-NNN` generates a PDF file.
result: pass

### 7. List and View Invoices
expected: `cqc facture lister` shows invoices with status. `cqc facture voir` shows details with tax breakdown.
result: pass

### 8. Mark Invoice as Paid
expected: `cqc facture payer` updates status to PAYEE and generates Beancount payment entry.
result: pass

### 9. Run Year-End Checklist
expected: `cqc cpa verifier --annee 2025` shows 6 validation checks with OK/AVERTISSEMENT/ERREUR severity.
result: pass

### 10. Generate CPA Export ZIP
expected: `cqc cpa export --annee 2025` produces organized ZIP with rapports/ (3 statements CSV+PDF), annexes/ (4 schedules CSV+PDF), gifi/ (2 CSVs). 16 files total.
result: pass

### 11. Upload Receipt via CLI
expected: `cqc recu telecharger` accepts a file path and stores it. Requires actual receipt file to fully test.
result: skipped
reason: No test receipt file available; CLI help confirmed command exists with correct interface.

### 12. View Filing Deadline Calendar
expected: `cqc echeances calendrier` shows all filing deadlines derived from fiscal year-end, with weekend adjustment to Monday.
result: pass

### 13. View Active Alerts
expected: `cqc echeances rappels` shows deadlines within 30 days with urgency levels.
result: pass

### 14. View Payroll Remittance Status
expected: `cqc echeances remises` shows owed vs remitted by month.
result: pass

## Summary

total: 14
passed: 12
issues: 1
pending: 0
skipped: 1

## Gaps

- truth: "Balance sheet accounting equation should hold (Actifs = Passifs + Capitaux Propres)"
  status: failed
  reason: "User reported: Balance sheet shows Actifs = -1,732.20, Total Passifs + Capitaux = -1,513.20 with AVERTISSEMENT: L'equation comptable ne balance pas! Difference: -219.00 CAD. Likely caused by test data inconsistency (dividendes-declares without matching equity), not a code bug."
  severity: minor
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
