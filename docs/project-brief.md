# Project Brief: AI-Assisted Accounting Stack for a Solo IT Consultant in Quebec

## 1. Context

- Solo incorporated IT consultant based in Quebec, Canada.
- Annual revenue is approximately $230,000 CAD.
- Work is knowledge work and tech consulting, with no inventory or physical retail.
- A software product, Enact, may become a second revenue stream.
- A human CPA remains responsible for:
  - T2 and CO-17 corporate tax returns.
  - T1 and TP-1 personal income tax.
  - Salary versus dividends strategy.
  - High-level tax planning and risk management.

The goal is not to replace the accountant. The goal is to reduce bookkeeping and data-prep work so the CPA can review cleaner records faster.

## 2. System Goal

Design and implement a developer-friendly accounting system that automates as much bookkeeping as possible:

- Import and normalize bank, credit card, and payment processor transactions.
- Classify income and expenses with a Quebec/Canada-appropriate chart of accounts.
- Handle payroll math and journal entries for owner salary.
- Track GST/QST, CCA, and shareholder loans.

At year end, the system should generate a CPA package:

- Trial balance and general ledger.
- Income statement and balance sheet.
- Payroll, CCA, GST/QST, and shareholder loan schedules.
- Links to source documents such as invoices, receipts, and bank statements.

Target outcome: the CPA can review everything in under one hour and focus on validation and optimization instead of cleanup.

## 3. Jurisdiction And Constraints

- Corporation is a CCPC in Quebec.
- Relevant authorities include CRA, Revenu Quebec, CNESST, RRQ, and RQAP.
- Important local specifics:
  - Quebec SBD 5,500-hour rule may mean a solo consultant does not qualify for the reduced Quebec small business corporate rate.
  - GST is 5%; QST is 9.975%.
  - Payroll may involve QPP/RRQ, RQAP, EI at the Quebec rate, FSS, CNESST, and labour standards.
  - CCA classes include class 50 for computers and class 8 for furniture.
  - Shareholder loan rules, including ITA section 15(2), need to be surfaced clearly.

The system should help avoid common traps such as personal services business risk, shareholder loan issues, and misclassified expenses, or at least make them visible.

## 4. Non-Goals

The system should not generate or file:

- T2 corporate returns.
- CO-17 returns.
- T1 or TP-1 personal returns.
- T4 or Releve 1 slips.
- GST/QST returns.

The system should not pretend to be a tax expert, provide legal or tax opinions, or silently invent accounting categories or numbers. It should prepare data and calculations for CPA review or external filing software.

## 5. Functional Goals

### Data Ingestion

- Import bank and credit card transactions from CSV, OFX, or similar sources.
- Import payment processor data such as Stripe, Wise, or PayPal where relevant.
- Ingest receipts and invoices from PDFs, scans, and images.
- Normalize all sources into a common transaction model with date, amount, currency, vendor or payee, description, memo, and tax amounts.

### Classification And Bookkeeping

- Automatically classify transactions into an opinionated chart of accounts for a Quebec-incorporated IT consultant with consulting revenue and a possible software product revenue stream.
- Handle owner salary payments, payroll deductions, employer contributions, dividends if used, CCA tracking, and GST/QST collected versus paid.
- Prefer a hybrid approach: rules first, AI assistance for edge cases, and human validation before posting.

### Review Loop

- The system should propose entries for review and approval.
- Corrections should be reusable so the system improves over time.
- Each entry should link back to source data.
- AI reasoning or notes should be visible for debugging when AI is used.

### Reporting And CPA Export

The system should generate:

- Trial balance.
- Income statement.
- Balance sheet.
- Payroll summary.
- CCA schedule by asset class.
- GST/QST summaries by period.
- Shareholder loan movement schedule.
- Machine-readable exports that map cleanly into CPA tools.

## 6. Technical Directions To Evaluate

### PyLedger Core Plus MCP

- Use PyLedger as the double-entry engine and persistence layer.
- Build Quebec-specific modules for payroll, GST/QST, CCA, and shareholder loans.
- Use MCP so Codex can query and update the ledger through safe tools.

### Plain-Text Accounting Plus MCP

- Use Beancount or HLedger as the ledger.
- Use MCP tooling so agents can run reports and propose entries.
- Build importers and Quebec-specific logic around the ledger.

### Hybrid

- Use a database-backed ledger or custom persistence where useful.
- Keep export to plain-text accounting for transparency and version control.
- Reuse specialized tools for receipt and invoice parsing.

The current repository is already oriented around Beancount, Fava, Python, and MCP, so new architecture work should treat that as the present implementation baseline.

## 7. Implementation Mindset

- Correctness and auditability matter more than magic.
- Numbers and formulas should be explicit and traceable.
- Architecture should stay extensible enough to support Enact or multiple entities later.
- Ambiguity should be surfaced instead of hidden, especially around salary versus dividends, borderline expenses, PSB risk, and tax treatments requiring CPA judgment.
