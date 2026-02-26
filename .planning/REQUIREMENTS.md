# Requirements: CompteQC

**Defined:** 2026-02-25
**Core Value:** Every dollar that flows through the corporation is correctly categorized, traceable to source documents, and ready for CPA review -- without manual data entry.

## v1.1 Requirements (Complete)

All 16 requirements shipped. See [v1.1-REQUIREMENTS.md](milestones/v1.1-REQUIREMENTS.md) for details.

- [x] DSYS-01 through DSYS-04 (Design System) -- Phase 6
- [x] DASH-01 through DASH-04 (Dashboard) -- Phase 7
- [x] TBLX-01 through TBLX-04 (Tables & Extensions) -- Phase 8
- [x] RCPT-01 through RCPT-04 (Receipt Upload) -- Phase 9

## v1.2 Requirements

Requirements for AP/AR & Financial Operations milestone. Each maps to roadmap phases 11-15.

### AP Foundation (APFN)

- [x] **APFN-01**: `Passifs:ComptesFournisseurs` (GIFI 2010) account added to chart of accounts
- [x] **APFN-02**: User can create a vendor bill with line items, per-line expense category, and GST/QST flags
- [x] **APFN-03**: System generates correct Beancount journal entries for bill recording (debit expense + ITC/ITR, credit AP)
- [x] **APFN-04**: System generates correct Beancount journal entries for bill payment (debit AP, credit bank/credit card)
- [x] **APFN-05**: Vendor bills persist in YAML registry with sequential numbering (FOUR-YYYY-NNN)

### AR Enhancements (AREN)

- [x] **AREN-01**: User can record partial payments on existing invoices with running balance
- [x] **AREN-02**: System derives invoice status from payment state (draft/sent/partial/paid/overdue)
- [x] **AREN-03**: User can list unpaid invoices filtered by status
- [x] **AREN-04**: Revenue account is configurable per invoice line (not hardcoded to Revenus:Consultation)

### Aging Reports (AGNG)

- [x] **AGNG-01**: System calculates aging buckets (0-30, 30-60, 60-90, 90+ days) for AR invoices
- [x] **AGNG-02**: System calculates aging buckets for AP bills
- [x] **AGNG-03**: User can view combined AP/AR position summary with net cash impact
- [x] **AGNG-04**: User can run aging reports via CLI (`cqc aging ar`, `cqc aging ap`, `cqc aging summary`)

### CLI Commands (CLAP)

- [x] **CLAP-01**: User can create vendor bills interactively via `cqc fournisseur add`
- [x] **CLAP-02**: User can list vendor bills via `cqc fournisseur list` with status filter
- [x] **CLAP-03**: User can record bill payment via `cqc fournisseur pay` (full or partial amount)

### Recurring & Matching (RECM)

- [ ] **RECM-01**: User can create recurring invoice templates with frequency and auto-generation date
- [ ] **RECM-02**: System generates invoices from templates on schedule or via `cqc facture generate-recurring`
- [ ] **RECM-03**: System auto-matches bank deposits against outstanding AR invoices by amount and description
- [ ] **RECM-04**: System auto-matches bank withdrawals against outstanding AP bills by amount and vendor

### Fava Extension (FVAP)

- [ ] **FVAP-01**: User sees combined AP/AR tab with KPI row (AR total, AR overdue, AP total, net position)
- [ ] **FVAP-02**: User can toggle between AR invoice list and AP bill list with status badges and aging colors
- [ ] **FVAP-03**: User sees Chart.js horizontal stacked bar chart showing aging distribution
- [ ] **FVAP-04**: User can create AR invoices via inline web form (bringing CLI to web)
- [ ] **FVAP-05**: User can create AP bills via inline web form with expense category dropdown
- [ ] **FVAP-06**: Dashboard homepage shows net AR/AP position KPI

### Receipt-to-AP Pipeline (RCAP)

- [ ] **RCAP-01**: After receipt upload and AI extraction, user sees "Create AP entry?" prompt
- [ ] **RCAP-02**: Clicking the prompt navigates to AP form pre-filled with extracted vendor, amount, dates, taxes
- [ ] **RCAP-03**: Approval queue shows match suggestions for bank transactions that correspond to open AR/AP entries
- [ ] **RCAP-04**: User can link a bank transaction to an AR invoice or AP bill with one click ("Lier" button)

### MCP Server (MCAP)

- [ ] **MCAP-01**: Claude can list and query AP bills via `ap_list` tool
- [ ] **MCAP-02**: Claude can create AP bills via `ap_add` tool
- [ ] **MCAP-03**: Claude can record AP payments via `ap_pay` tool
- [ ] **MCAP-04**: Claude can generate aging reports via `ar_aging`, `ap_aging`, `apar_summary` tools

## Future Requirements

Deferred to v1.3+. Tracked but not in current roadmap.

### Data Visualization Enhancements

- **VIZ-01**: Cash flow waterfall chart (monthly inflows vs outflows)
- **VIZ-02**: YoY comparison overlays on revenue/expense charts
- **VIZ-03**: Interactive drill-down from chart segments to transaction lists

### Advanced UX

- **UX-01**: Customizable dashboard card layout (drag-and-drop reorder)
- **UX-02**: Dark mode toggle
- **UX-03**: Keyboard shortcut system across all extensions

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-currency AP/AR | All business is CAD; add when USD invoices arise |
| Vendor portal / self-service | Solo consultant; no vendor-facing UI needed |
| Purchase orders | No inventory, no PO workflow needed |
| Credit notes / debit memos | Low volume; handle manually if needed |
| Automated payment execution | System tracks what's owed, not how to pay (manual bank payments) |
| AP/AR forecasting / cash flow projection | Phase 1 is tracking actuals; forecasting is future |
| Tax return filing | CPA handles T2, CO-17, GST/QST returns |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| APFN-01 | Phase 11 | Complete |
| APFN-02 | Phase 11 | Complete |
| APFN-03 | Phase 11 | Complete |
| APFN-04 | Phase 11 | Complete |
| APFN-05 | Phase 11 | Complete |
| AREN-01 | Phase 12 | Complete |
| AREN-02 | Phase 12 | Complete |
| AREN-03 | Phase 12 | Complete |
| AREN-04 | Phase 12 | Complete |
| AGNG-01 | Phase 12 | Complete |
| AGNG-02 | Phase 12 | Complete |
| AGNG-03 | Phase 12 | Complete |
| AGNG-04 | Phase 12 | Complete |
| CLAP-01 | Phase 12 | Complete |
| CLAP-02 | Phase 12 | Complete |
| CLAP-03 | Phase 12 | Complete |
| RECM-01 | Phase 13 | Pending |
| RECM-02 | Phase 13 | Pending |
| RECM-03 | Phase 13 | Pending |
| RECM-04 | Phase 13 | Pending |
| FVAP-01 | Phase 14 | Pending |
| FVAP-02 | Phase 14 | Pending |
| FVAP-03 | Phase 14 | Pending |
| FVAP-04 | Phase 14 | Pending |
| FVAP-05 | Phase 14 | Pending |
| FVAP-06 | Phase 14 | Pending |
| MCAP-01 | Phase 14 | Pending |
| MCAP-02 | Phase 14 | Pending |
| MCAP-03 | Phase 14 | Pending |
| MCAP-04 | Phase 14 | Pending |
| RCAP-01 | Phase 15 | Pending |
| RCAP-02 | Phase 15 | Pending |
| RCAP-03 | Phase 15 | Pending |
| RCAP-04 | Phase 15 | Pending |

**Coverage:**
- v1.2 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 after v1.2 milestone definition*
