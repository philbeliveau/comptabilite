# Project: AI-Assisted Accounting Stack for a Solo IT Consultant in Quebec

## 1. Context about me and my business

- I am a **solo incorporated IT consultant** based in **Quebec, Canada**.
- Annual revenue is approximately **$230,000** CAD.
- I do **knowledge work / tech consulting** (no inventory, no physical retail).
- I also have a **software product (Enact)** that may become a second revenue stream.
- I will keep working with a **human CPA** for:
  - T2 + CO‑17 corporate tax returns
  - T1 + TP‑1 personal income tax
  - Salary vs dividends strategy
  - High-level tax planning and risk management

The goal is **not** to replace the accountant, but to massively reduce the bookkeeping and data-prep load, and make the CPA’s work faster and cleaner.

---

## 2. High-level goal of this project

Design and implement a **developer-friendly accounting system** that:

1. **Automates as much bookkeeping as possible** for my corporation:
   - Importing and normalizing transactions (bank, credit card, payment processors).
   - Classifying income and expenses according to a Quebec/Canada-appropriate chart of accounts.
   - Handling payroll math and journal entries for paying myself a salary.
   - Tracking GST/QST, CCA, and shareholder loans.

2. Produces, at year end, a **clean, comprehensive package** for my CPA:
   - Trial balance and general ledger.
   - Income statement and balance sheet.
   - Detailed schedules (payroll, CCA, GST/QST, shareholder loan, etc.).
   - Access to original documents (invoices, receipts, bank statements) linked to entries.

The target outcome: **my CPA can review everything in under one hour** and focus on validation and optimization instead of cleanup.

We are still **exploring options and architecture choices**. Nothing is locked in yet.

---

## 3. Key constraints and requirements

### 3.1 Jurisdiction and tax context

- Corporation is a **CCPC** in **Quebec**.
- Must respect:
  - Federal rules (CRA, Income Tax Act).
  - Quebec rules (Revenu Québec, CNESST, RRQ, RQAP).
- Important local specifics:
  - **Quebec SBD (small business deduction) 5,500‑hour rule**: as a solo consultant I likely do *not* qualify for the reduced Quebec small business corporate rate.
  - **GST (5%) + QST (9.975%)** with input tax credits/refunds.
  - **Payroll contributions**: QPP/RRQ, RQAP, EI (Quebec rate), FSS, CNESST, labour standards.
  - **CCA** classes (notably class 50 for computers, class 8 for furniture).
  - **Shareholder loan rules** (section 15(2) ITA) to avoid accidental taxable benefits.

The system must help avoid common traps (personal services business risk, shareholder loans, misclassified expenses, etc.), or at least surface them clearly.

### 3.2 What the system should NOT do

- It should **not** attempt to generate or file:
  - T2 corporate return
  - CO‑17
  - T1 / TP‑1
  - T4 / Relevé 1
  - GST/QST returns
- It should **not** pretend to be a tax expert or provide legal/tax opinions.
- It should **not** silently “invent” accounting categories or numbers.

Instead, it should **prepare the data and calculations** so the CPA or external software can handle the actual filing.

---

## 4. Functional goals (what I want this system to do)

### 4.1 Data ingestion

- Import **bank and credit card transactions** (CSV, OFX, etc.).
- Import **payment processor data** (Stripe, Wise, PayPal, etc.) where relevant.
- Ingest **receipts and invoices** (PDFs, scans, images).
- Normalize all this into a **common transaction model**:
  - date, amount, currency
  - vendor/payee
  - description/memo
  - tax amounts (GST, QST, other)

We can reuse or extend existing tools (e.g. TaxHacker-style receipt parsing, Beancount/HLedger importers, PyLedger APIs).

### 4.2 Classification and bookkeeping

- Automatically **classify transactions** into an opinionated chart of accounts tailored to:
  - a Quebec-incorporated IT consultant,
  - with both consulting revenue and a software product.
- Handle:
  - salary payments to myself, with correct journal entries for payroll deductions and employer contributions.
  - dividends (if used) and related equity movements.
  - CCA tracking for capital assets (e.g. Mac Studio, monitors).
  - GST/QST collected vs paid, and net remittance.

Here, I’m open to using:
- rule-based systems,
- ML/LLM-assisted categorization,
- or a hybrid (rules first, LLM for edge cases, human validation).

### 4.3 Review and feedback loop

- I want a workflow where the system proposes entries and **I review/approve**:
  - For example, a web UI or text-based interface listing uncategorized or low-confidence transactions.
  - Ability to correct categorizations; the system should **learn from corrections** over time.
- Everything should be traceable:
  - Each entry links back to source data (CSV row, PDF, etc.).
  - The AI’s reasoning/notes (if used) should be visible for debugging.

### 4.4 Reporting and export for my accountant

By year end (or more often), the system should be able to generate for my CPA:

- Trial balance.
- Income statement and balance sheet.
- Detail of:
  - Payroll (gross pay, source deductions, employer contributions).
  - CCA schedules by asset class.
  - GST/QST summaries by period (collected, ITCs, net payable).
  - Shareholder loan movements.
- Machine-readable exports (CSV or similar) that map cleanly into the CPA’s tools.

The goal is to hand over **one consistent package** that requires minimal CPA cleanup.

---

## 5. Technical direction (still open)

This part is exploratory: I want your help to evaluate tradeoffs.

Some candidate directions:

1. **PyLedger as core ledger + MCP server**
   - Use PyLedger as the double-entry engine and persistence layer.
   - Build Quebec-specific modules (payroll formulas, GST/QST, CCA, shareholder loans).
   - Use MCP so you (Claude) can query/update the ledger safely.

2. **Plain-text accounting (Beancount / HLedger) + MCP**
   - Use Beancount or HLedger for the ledger.
   - Use existing MCP servers (e.g. hledger-mcp) so you can run reports and propose entries.
   - Build importers and Quebec-specific logic around it.

3. **Hybrid**
   - Use a database-backed ledger (PyLedger or custom) but keep the **ability to export** to a plain-text format for transparency and version control.
   - Reuse specialized tools for receipts (like TaxHacker) for document parsing.

I’m open to iterating on architecture; nothing is fixed yet.

---

## 6. How I want you (Claude) to help

Over time, I’d like you to:

1. **Refine the architecture**:
   - Compare options (PyLedger vs HLedger vs Beancount, etc.).
   - Propose a modular design (ingestion, AI layer, ledger, review UI, export).

2. **Design the data model and APIs**:
   - Transaction schema.
   - Chart of accounts structure for Quebec.
   - Representation of payroll, CCA, GST/QST, shareholder loans.

3. **Implement vertical slices**:
   - Example: “Import Desjardins CSV → categorize → post to ledger → show report.”
   - Example: “Parse uploaded invoice PDF → extract fields → suggest posting.”

4. **Integrate legal/tax formulas in a robust way**:
   - Encode the formulas and thresholds from official sources (QPP, RQAP, EI, FSS, CNESST, etc.).
   - Make sure they are encapsulated in clear, testable modules.
   - Keep it easy to update when rates change.

5. **Keep me in the loop on tradeoffs**:
   - When there is ambiguity (e.g. salaries vs dividends, borderline expenses, PSB risk), surface it instead of hiding it.
   - Suggest where human judgment is required and where automation is safe.

---

## 7. Important mindset

- This is a **long-term internal tool** for my own use as a founder/consultant.
- I value:
  - **Correctness and auditability** over “magic”.
  - **Explicitness**: I want to see how numbers are derived.
  - **Extensibility**: architecture that can later expand to handle Enact or multiple entities.
- We’re still **brainstorming and experimenting**:
  - I expect you to challenge assumptions, propose alternatives, and help me converge on a design that balances complexity, robustness, and implementation effort.

You can ask clarifying questions whenever something is underspecified (e.g. exact tech stack, preferred DB, hosting environment). The next step I’d like is for you to propose 1–2 high-level architectures with pros/cons and a suggested “first vertical slice” to implement.
