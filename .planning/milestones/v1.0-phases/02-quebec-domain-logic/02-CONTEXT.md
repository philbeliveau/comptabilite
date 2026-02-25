# Phase 2: Quebec Domain Logic - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Payroll engine with all Quebec/federal deductions, GST/QST tracking with ITC/ITR, CCA schedules for capital assets, and shareholder loan monitoring with s.15(2) deadline alerts. This phase builds on the working ledger and import pipeline from Phase 1. Creating reports, AI categorization, and web UI are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Payroll workflow
- On-demand CLI trigger (e.g. `compteqc payroll run 5000`) — no schedule, user initiates each run
- Consistent salary amount expected (same gross each time, occasional adjustments)
- Full breakdown output by default: gross, every deduction line (QPP, RQAP, EI, federal tax, Quebec tax), every employer contribution (FSS, CNESST, etc.), net pay
- YTD totals must stop contributions at annual maximums (QPP, EI, RQAP)

### Payroll corrections
- Claude's Discretion: choose the correction approach that's cleanest for CPA review (reversal + new entry vs adjustment delta)

### GST/QST tax treatment on expenses
- Auto-calculate GST (5%) and QST (9.975%) from transaction total by default
- Tax treatment rules: category default (taxable/exempt/zero-rated) + vendor-level override
- Vendor override wins when it exists; new vendors default to "taxable" until confirmed
- GST and QST always tracked separately (never combined 14.975% rate)

### GST/QST filing periods
- Filing frequency is configurable (annual or quarterly) — system asks or reads from config
- Summaries generated per filing period: GST collected, QST collected, ITCs, ITRs, net remittance
- Monthly drill-down available within each period

### GST/QST on revenue
- Per-client tax treatment rules (not "always charge both")
- Quebec clients: GST + QST
- Out-of-province Canadian clients: GST only
- International clients: no GST/QST
- Per-product-type rules also supported (for Enact vs consulting)

### CCA & asset registration
- Auto-flag transactions over configurable threshold (default $500) as potential CAPEX
- System proposes CCA class, user confirms or overrides
- Manual CLI registration also available for assets not in bank feed (personal contributions, financed purchases)

### CCA depreciation
- Claude's Discretion: choose safest approach for CPA review (auto-generate with review vs auto-post)
- Half-year rule applied automatically on new acquisitions
- Declining balance by CCA class

### CCA pool tracking
- Pool-level UCC tracking per CCA class (mirrors CRA approach)
- Individual assets listed for reference but CCA calculated at pool level

### Asset disposal
- Both paths: CLI command for explicit disposal + auto-detect from sale transactions in bank feed
- System calculates recapture or terminal loss and posts entries

### Shareholder loan triggers
- Auto-detect potential personal transactions (grocery, personal subscriptions, non-business restaurants) and flag for confirmation
- User confirms: "business", "personal/loan", or "ignore"
- Explicitly categorized personal expenses always hit shareholder loan automatically
- System never silently posts ambiguous items to shareholder loan

### Shareholder loan alerts (s.15(2))
- Graduated escalation: alert at 9 months, 11 months, and 30 days before inclusion date
- No spammy monthly alerts — clear escalating sequence only

### Shareholder loan repayment
- Both methods supported: personal deposits to corp account + salary offset
- Personal deposits tagged as loan repayment reduce balance
- Salary offset: option to apply $X from paycheque against shareholder loan
- Clear audit trail on every repayment regardless of method

### Shareholder loan direction
- Bidirectional tracking on a single net balance
- Positive = shareholder owes corp, negative = corp owes shareholder
- Full detail of each movement preserved (distinguish reimbursements vs loans vs equity injections)
- Direction clearly visible at any time via query

</decisions>

<specifics>
## Specific Ideas

- Payroll should feel like a single CLI command with full transparency — "I run it, I see everything, it posts"
- Tax treatment layering: category is the base assumption, vendor is the exception — this mirrors how a CPA would think about it
- Shareholder loan is the highest-risk area legally (s.15(2)) — the system should be conservative and never silently classify ambiguous items
- CPA should be able to see the full shareholder loan continuity schedule with every movement explained

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-quebec-domain-logic*
*Context gathered: 2026-02-19*
