# Phase 4: MCP Server and Web Dashboard - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Claude integration via MCP tools for querying, categorizing, approving transactions, and running payroll. Fava-based web UI with standard ledger views plus custom Quebec-specific extensions (payroll, GST/QST, CCA, shareholder loan). Both interfaces share the same pending transaction approval queue.

</domain>

<decisions>
## Implementation Decisions

### MCP tool design
- Full scope: Claude can query, propose entries/categorizations, approve/reject pending transactions, and run payroll — complete workflow without leaving Claude
- Tool granularity: Claude's discretion — pick the right balance of broad vs specific tools based on what works best
- Tool output includes proposed entry + short reasoning explanation (e.g. "Matched vendor X to Fournitures informatiques based on previous pattern") — not minimal, not full trace
- Payroll via MCP: Claude can trigger payroll computation for a given gross salary and generate all journal entries

### Approval workflow
- Batch approve by default — select multiple transactions and approve/reject as a group for speed
- Correction flow on reject: Claude's discretion on best UX (re-queue vs inline edit)
- Approval available in both interfaces — MCP (via Claude conversation) and Fava web UI, same underlying queue
- Auto-approve above confidence threshold for transactions that pass; only lower-confidence items need manual review

### Dashboard layout and views
- All four Quebec-specific views as custom Fava extensions:
  - **Payroll dashboard**: YTD employee deductions and employer contributions (QPP, RQAP, EI, FSS, CNESST, labour standards), which maximums are reached, next payroll breakdown estimate
  - **GST/QST tracker**: collected vs ITCs/ITRs by filing period, net remittance due, aligned with actual filing periods (annual/quarterly)
  - **CCA schedule**: UCC per class (8, 10, 12, 50, 54), additions/disposals, CCA claimed this year, UCC carry-forward
  - **Shareholder loan status**: current net balance (corp owes me vs I owe corp), movement history, countdown to s.15(2) deadline
- AI confidence/source tag display: Claude's discretion on visual treatment
- Pending approval queue placement (separate page vs journal integration): Claude's discretion
- Network access: Claude's discretion on sensible defaults for self-hosted tool

### Safety and permissions
- Read-only mode: Claude's discretion on implementation (startup flag vs per-session toggle)
- Dollar-amount guardrail: transactions over $2,000 always require explicit human confirmation, even if high-confidence
- Audit trail for MCP mutations: Claude's discretion (git history may suffice)
- Payroll confirmation: Claude's discretion on whether recurring same-amount payroll needs explicit confirmation

### Claude's Discretion
- MCP tool granularity (few broad vs many specific tools)
- Correction flow UX on rejected transactions
- AI confidence/source tag visual treatment in dashboard
- Pending queue as separate Fava page vs journal integration
- Dashboard network access defaults
- Read-only mode implementation
- Audit trail approach (dedicated log vs git history)
- Payroll run confirmation requirements for recurring amounts

</decisions>

<specifics>
## Specific Ideas

- User wants Quebec views to show real filing periods (annual/quarterly) not just calendar months
- CCA classes specifically called out: 8, 10, 12, 50, 54
- Shareholder loan view must include s.15(2) deadline countdown — this is a compliance-critical feature
- MCP tool reasoning should explain categorization logic (pattern matching, vendor history) not just the result
- $2,000 is the explicit amount cap for auto-approval

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-mcp-server-and-web-dashboard*
*Context gathered: 2026-02-19*
