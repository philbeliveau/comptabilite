# Phase 5: Reporting, CPA Export, and Document Management - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce a complete year-end CPA package (trial balance, P&L, balance sheet, payroll/CCA/GST-QST/shareholder-loan schedules), generate branded consulting invoices with payment tracking, ingest receipts/invoices with AI extraction and transaction matching, and surface filing deadline alerts with a year-end verification checklist. This is the output layer that converges all prior phases into deliverables for the CPA and operational tools for the consultant.

</domain>

<decisions>
## Implementation Decisions

### CPA package format and delivery
- CPA format preference unknown — consult CPA before finalizing; system should generate both CSV (machine-readable) and PDF (human-readable) so whichever the CPA prefers is available
- GIFI-mapped Schedule 100 export should include pre-validation (accounting equation balance, no negative revenue, asset/liability sanity checks) before generation
- Dual-format strategy: PDF for all reports (human review), CSV for key data exports (trial balance, GIFI mapping, payroll schedule) that CPA tools can import

### Claude's Discretion — CPA package
- Single ZIP folder vs individual files delivery format
- Exact report layout and PDF styling
- Which reports get CSV in addition to PDF (beyond the key three: trial balance, GIFI, payroll)

### Invoice workflow
- Currently invoicing manually from Word/Google Docs — this replaces that with a CLI/system-generated approach
- Low volume: 1-2 clients per month — keep workflow simple
- Branded template required: company logo, colors, specific styling (not generic/plain)
- GST/QST numbers and correct tax breakdown on every invoice (legal requirement)
- Payment tracking is manual: user marks invoices as paid when deposit is seen in bank — no auto-matching needed
- Invoice statuses: draft, sent, paid, overdue
- Invoices link to accounts receivable entries in the ledger

### Receipt and document ingestion
- Mix of physical receipts (photographed) and digital PDFs from email
- Upload via both CLI (`cqc receipt upload`) and web dashboard (drag-and-drop in Fava UI)
- AI extraction via Claude Vision: vendor, date, amount, GST/QST breakdown
- Extracted data feeds into transaction matching

### Claude's Discretion — Receipts
- Receipt-to-transaction matching strategy (auto-propose with confirmation vs manual selection — use confidence scoring from Phase 3 to decide)
- Storage approach: git-tracked `documents/` folder vs separate storage with reference IDs
- Handling of low-quality images or unreadable receipts

### Filing deadline alerts and year-end checklist
- Alerts surface as dashboard banners in the Fava web UI (primary channel)
- Key deadlines tracked: GST/QST quarterly, T4/RL-1 (Feb 28), T2/CO-17 (6 months after fiscal year-end)
- s.15(2) shareholder loan deadlines should be unified into the same dashboard alert system (single view of all deadlines)

### Claude's Discretion — Alerts and checklist
- Alert lead times per deadline type (standard urgency-based approach)
- Year-end checklist strictness: warn-but-allow vs block-on-failure for CPA package generation
- Whether to also show deadline reminders in CLI output

</decisions>

<specifics>
## Specific Ideas

- Invoice template must be branded (logo + company colors) — not a generic plain template
- CPA hasn't been consulted on preferred format yet — build both CSV and PDF to cover both possibilities
- Receipt workflow should feel lightweight for a solo consultant (1-2 clients, low transaction volume)
- Year-end checklist items from roadmap: shareholder loan balance, CCA schedule, GST/QST reconciliation

</specifics>

<deferred>
## Deferred Ideas

- **Fava dashboard alert banners** — Deadline alerts in Fava web UI banners deferred to Phase 4 (Fava extensions). Phase 5 implements alert logic + CLI surface; Phase 4 adds the Fava rendering layer.
- **Fava drag-and-drop receipt upload** — Web-based receipt upload via Fava UI deferred to Phase 4 (Fava extensions). Phase 5 implements CLI upload + extraction logic; Phase 4 adds the web upload endpoint.

</deferred>

---

*Phase: 05-reporting-cpa-export-and-document-management*
*Context gathered: 2026-02-19*
