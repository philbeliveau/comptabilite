---
status: testing
phase: 03-ai-categorization-and-review-workflow
source: 03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md
started: 2026-02-19T21:00:00Z
updated: 2026-02-19T21:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 2
name: CAPEX detection flags high-value transactions
expected: |
  A transaction over $500 (e.g. a computer purchase) is automatically flagged as potential CAPEX with a suggested CCA class (e.g. class 50 for computers). CAPEX transactions are forced to pending regardless of confidence.
awaiting: user response

## Tests

### 1. Import CLI runs full 3-tier pipeline
expected: Running `cqc importer` on an RBC CSV file processes transactions through rules, then ML, then LLM tiers. CLI output shows a tiered summary with counts per source and routing destinations.
result: pass

### 2. CAPEX detection flags high-value transactions
expected: A transaction over $500 (e.g. a computer purchase) is automatically flagged as potential CAPEX with a suggested CCA class (e.g. class 50 for computers). CAPEX transactions are forced to pending regardless of confidence.
result: [pending]

### 3. Graceful degradation without ANTHROPIC_API_KEY
expected: Running the import pipeline without ANTHROPIC_API_KEY set shows an info message about the missing key but does NOT error. Rules and ML tiers still process normally; only the LLM tier is skipped.
result: [pending]

### 4. Pending transactions staged in pending.beancount
expected: After import, AI-categorized transactions with confidence between 80-95% appear in pending.beancount with #pending tag and metadata (source_ia, confiance, compte_propose).
result: [pending]

### 5. Review CLI lists pending transactions
expected: Running `cqc reviser liste` shows a Rich table of pending transactions with columns for date, payee, amount, proposed account, confidence (color-coded), and source. Mandatory reviews (<80%) appear first, separated from optional (80-95%).
result: [pending]

### 6. Approve pending transaction via CLI
expected: Running `cqc reviser approuver <index>` moves the transaction from pending.beancount to the monthly ledger file. The #pending tag is removed and the transaction is committed to git.
result: [pending]

### 7. Recategorize and auto-rule generation
expected: Running `cqc reviser recategoriser <index> <new_account>` changes the transaction's account. After 2 identical corrections for the same vendor, a new YAML rule is auto-generated in the rules file for future categorization.
result: [pending]

### 8. LLM categorization with JSONL audit logging
expected: When ANTHROPIC_API_KEY is set, LLM tier categorizes transactions that rules and ML could not handle. Each LLM call is logged to a JSONL file with timestamp, prompt hash, model, token usage for audit/drift detection.
result: [pending]

## Summary

total: 8
passed: 1
issues: 0
pending: 7
skipped: 0

## Gaps

[none yet]
