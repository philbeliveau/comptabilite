# Roadmap: CompteQC

## Milestones

- **v1.0 MVP** -- Phases 1-5 (shipped 2026-02-25)
- **v1.1 Production UI/UX** -- Phases 6-10 (in progress)
- **v1.2 AP/AR & Financial Operations** -- Phases 11-15 (planned)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-5) -- SHIPPED 2026-02-25</summary>

- [x] Phase 1: Ledger Foundation and Import Pipeline (3/3 plans)
- [x] Phase 2: Quebec Domain Logic (5/5 plans)
- [x] Phase 3: AI Categorization and Review Workflow (3/3 plans)
- [x] Phase 4: MCP Server and Web Dashboard (5/5 plans)
- [x] Phase 5: Reporting, CPA Export, and Document Management (5/5 plans)

</details>

<details>
<summary>v1.1 Production UI/UX (Phases 6-10)</summary>

- [ ] **Phase 6: Design System Foundation** - Chart.js infrastructure, CSS variable migration, animation guards, typography refinement
- [ ] **Phase 7: Dashboard Homepage** - KPI cards, revenue trend chart, expense breakdown chart, recent transactions
- [ ] **Phase 8: Table and Extension Polish** - Hover states, approval queue redesign, page transitions, sidebar badge
- [ ] **Phase 9: Receipt Upload UX** - AJAX endpoint, progress bar, file previews, drag-and-drop animation
- [ ] **Phase 10: Cross-Cutting Polish and Validation** - Typography audit, spacing consistency, cross-browser testing, accessibility verification

</details>

### v1.2 AP/AR & Financial Operations

**Milestone Goal:** Implement a complete accounts payable and accounts receivable system -- track vendor bills, manage customer invoices, automate payment matching, and surface aging reports -- so the solo consultant's cash position is always clear and CPA-ready.

- [x] **Phase 11: AP Foundation** - Data model, YAML registry, Beancount journal entries for bill recording and payment (completed 2026-02-26)
- [ ] **Phase 12: Aging, AR Enhancements & CLI** - Aging buckets, partial payments, invoice status derivation, all CLI commands
- [ ] **Phase 13: Recurring Invoices & Auto-matching** - Recurring invoice templates and bank transaction matching logic
- [ ] **Phase 14: Fava Extension Tab & MCP** - Combined AP/AR web UI with charts and inline forms, plus MCP server tools
- [ ] **Phase 15: Receipt-to-AP Pipeline & Auto-matching UX** - Receipt upload to AP creation flow, bank transaction linking

## Phase Details

<details>
<summary>v1.1 Phase Details (Phases 6-10)</summary>

### Phase 6: Design System Foundation
**Goal**: Every UI component has a stable, performant foundation -- Chart.js loads and cleans up safely on SPA navigation, CSS theming uses Fava's variable system instead of brute-force overrides, and animations respect user preferences
**Depends on**: Phase 5 (v1.0 complete)
**Requirements**: DSYS-01, DSYS-02, DSYS-03, DSYS-04
**Success Criteria** (what must be TRUE):
  1. Chart.js loads on first navigation to any chart-enabled page and does not leak instances on repeated SPA navigations (no canvas accumulation after 10+ page switches)
  2. CSS theming overrides Fava styles through custom property reassignment, not `!important` escalation -- existing `!important` count reduced by at least 80%
  3. All animations and transitions are suppressed when the user has `prefers-reduced-motion: reduce` enabled in their OS settings
  4. Money amounts across all extensions render with tabular-nums (columns align visually) and the Inter font loads without FOUT
**Plans**: 2 plans

Plans:
- [ ] 06-01-PLAN.md — Chart.js CDN loader, chart registry with destroy-on-load, renderCharts() engine, KPI animation, page transitions, prefers-reduced-motion guards
- [ ] 06-02-PLAN.md — CSS variable migration (!important audit), typography scale, tabular-nums for money columns

### Phase 7: Dashboard Homepage
**Goal**: User opens CompteQC and immediately sees a financial snapshot -- KPI cards with animated numbers, a revenue trend line, an expense breakdown donut, and recent transaction activity
**Depends on**: Phase 6
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04
**Success Criteria** (what must be TRUE):
  1. User sees five KPI cards (Revenue YTD, Expenses YTD, Net Income, Tax Owing, Pending Approvals) with values that animate from zero to the correct amount on page load
  2. User sees a line chart showing monthly revenue for the current fiscal year, with data points matching the ledger totals
  3. User sees a doughnut chart breaking down expenses by category (top categories plus "Autres"), with segments matching ledger data
  4. User sees the last 10 transactions with date, description, amount, and status badge -- each row links to the source entry
  5. Dashboard loads within 2 seconds on a cold navigation and Chart.js canvases resize correctly when the browser window changes size
**Plans**: 2 plans

Plans:
- [ ] 07-01-PLAN.md — TableauBordExtension Python backend (KPI computation, monthly revenue series, expense categories, recent transactions, JSON helpers)
- [ ] 07-02-PLAN.md — Dashboard HTML template (KPI cards with data-value, chart containers with data-chart, transactions table) and main.beancount registration

### Phase 8: Table and Extension Polish
**Goal**: Every extension table looks production-grade with consistent styling, the approval queue is fast to scan and operate, and navigation between extensions feels smooth
**Depends on**: Phase 7
**Requirements**: TBLX-01, TBLX-02, TBLX-03, TBLX-04
**Success Criteria** (what must be TRUE):
  1. All 8 extension tables have visible hover states on rows, consistent cell padding, and distinct header styling that creates clear visual hierarchy
  2. Approval queue shows redesigned confidence badges with color-coded urgency, supports keyboard shortcuts (approve/reject without mouse), and presents a scannable layout where high-confidence items are visually distinct from low-confidence ones
  3. Navigating between extensions triggers a subtle entrance animation (fade + slide) that masks the SPA content swap
  4. Sidebar "Approbation" link shows a count badge with the number of pending approvals, updating on each page load
**Plans**: 2 plans

Plans:
- [ ] 08-01-PLAN.md — Table hover fix, header hierarchy, consistent padding, inline style cleanup, page transitions
- [ ] 08-02-PLAN.md — Approval queue confidence bars, keyboard shortcuts, sidebar pending count badge

### Phase 9: Receipt Upload UX
**Goal**: Uploading receipts feels modern and responsive -- drag a file, see it upload with a progress bar, and get a thumbnail preview confirming what was received
**Depends on**: Phase 8
**Requirements**: RCPT-01, RCPT-02, RCPT-03, RCPT-04
**Success Criteria** (what must be TRUE):
  1. Upload endpoint accepts files via AJAX and returns JSON (status, filename, extracted data) without triggering a full-page reload
  2. User sees an animated progress bar with percentage during file upload that reflects actual upload progress (not fake/indeterminate)
  3. After upload completes, user sees a thumbnail preview of the uploaded file -- image files show a scaled thumbnail, PDF files show a document icon with filename
  4. Drag-and-drop zone has animated border on dragover, a glow effect on hover, and supports dropping multiple files in a single action
**Plans**: 2 plans

Plans:
- [ ] 09-01-PLAN.md — Convert upload endpoint to AJAX/JSON responses and implement XHR upload with real progress bar
- [ ] 09-02-PLAN.md — File preview thumbnails, animated drag-and-drop border/glow, and multi-file sequential upload

### Phase 10: Cross-Cutting Polish and Validation
**Goal**: The entire UI feels like one cohesive product -- consistent typography, spacing, shadows, and behavior across all pages, verified across browsers and accessibility standards
**Depends on**: Phase 9
**Requirements**: None (cross-cutting quality gate validating all prior phases)
**Success Criteria** (what must be TRUE):
  1. Typography scale is consistent across all extensions -- headings, body text, and money amounts use the same sizes, weights, and spacing everywhere
  2. All interactive elements (buttons, links, badges, chart segments) work correctly in Safari, Chrome, and Firefox on macOS
  3. Keyboard-only navigation reaches every interactive element across all extensions without traps, and screen readers announce meaningful labels
  4. No visual regressions from v1.0 functionality -- all existing features (import, categorize, payroll, reports, export) remain fully operational
**Plans**: 2 plans

Plans:
- [ ] 10-01-PLAN.md — Typography token migration, font-weight normalization, cross-browser CSS fixes (Firefox scrollbar, focus-visible, backdrop-filter)
- [ ] 10-02-PLAN.md — Accessibility remediation (ARIA across all templates, sidebar badge aria-live) and cross-browser/regression verification checkpoint

</details>

### Phase 11: AP Foundation
**Goal**: User can create vendor bills, persist them in a registry, and generate correct Beancount journal entries for both bill recording and payment -- establishing the accounts payable data layer
**Depends on**: Phase 10 (v1.1 complete)
**Requirements**: APFN-01, APFN-02, APFN-03, APFN-04, APFN-05
**Success Criteria** (what must be TRUE):
  1. `Passifs:ComptesFournisseurs` (GIFI 2010) exists in the chart of accounts and Beancount validates without errors
  2. User can create a vendor bill with multiple line items, each assigned to a specific expense account, with GST/QST flags generating ITC/ITR entries
  3. Recording a bill produces a balanced Beancount transaction (debit expense accounts + tax receivable, credit AP) that appears in the ledger
  4. Paying a bill produces a balanced Beancount transaction (debit AP, credit bank/credit card) and the bill status updates to paid
  5. Vendor bills persist in YAML with sequential FOUR-YYYY-NNN numbering and survive application restarts
**Plans**: 2 plans

Plans:
- [ ] 11-01-PLAN.md -- Chart of accounts AP account, FactureFournisseur models, BillStatus enum, RegistreFournisseurs YAML registry, tests
- [ ] 11-02-PLAN.md -- Journal entry generators for bill recording and payment, partial ITC/ITR, tests

### Phase 12: Aging, AR Enhancements & CLI
**Goal**: User can track invoice and bill aging, handle partial payments on AR invoices, and operate the full AP/AR system from the command line
**Depends on**: Phase 11
**Requirements**: AREN-01, AREN-02, AREN-03, AREN-04, AGNG-01, AGNG-02, AGNG-03, AGNG-04, CLAP-01, CLAP-02, CLAP-03
**Success Criteria** (what must be TRUE):
  1. User can record a partial payment on an invoice and see the running balance decrease accordingly, with invoice status automatically transitioning through draft/sent/partial/paid/overdue
  2. User can run `cqc aging ar` and `cqc aging ap` to see invoices and bills grouped into 0-30, 30-60, 60-90, and 90+ day buckets with subtotals
  3. User can run `cqc aging summary` to see a combined AR/AP position with net cash impact (what is owed to us minus what we owe)
  4. User can create bills (`cqc fournisseur add`), list them with status filters (`cqc fournisseur list`), and record full or partial payments (`cqc fournisseur pay`) entirely from the CLI
  5. Revenue account is configurable per invoice line item, allowing training revenue and consulting revenue to post to different accounts
**Plans**: 2 plans

Plans:
- [ ] 12-01-PLAN.md -- AR model enhancements (partial payments, status derivation, configurable revenue) + aging calculation module (AR/AP/combined)
- [ ] 12-02-PLAN.md -- CLI commands: fournisseur add/list/voir/pay, aging ar/ap/summary, facture lister PARTIAL filter

### Phase 13: Recurring Invoices & Auto-matching
**Goal**: User can set up recurring invoice templates that auto-generate on schedule, and the system intelligently matches bank transactions to outstanding invoices and bills
**Depends on**: Phase 12
**Requirements**: RECM-01, RECM-02, RECM-03, RECM-04
**Success Criteria** (what must be TRUE):
  1. User can create a recurring invoice template specifying client, amount, frequency (monthly/biweekly), and next generation date
  2. Running `cqc facture generate-recurring` creates invoices from all due templates, advancing each template's next date
  3. When importing bank transactions, the system suggests matches between deposits and open AR invoices based on amount and description similarity
  4. When importing bank transactions, the system suggests matches between withdrawals and open AP bills based on amount and vendor name
**Plans**: 2 plans

Plans:
- [ ] 13-01-PLAN.md -- Recurring invoice templates: ModeleFactureRecurrente model, YAML registry, generation logic, CLI commands (template-add, template-list, generate-recurring)
- [ ] 13-02-PLAN.md -- Auto-matching engine: bank deposit matching against AR invoices, withdrawal matching against AP bills, confidence scoring, import pipeline integration

### Phase 14: Fava Extension Tab & MCP
**Goal**: User can manage AP/AR entirely from the Fava web interface with a dedicated tab, and Claude can query and mutate AP data via MCP tools
**Depends on**: Phase 13
**Requirements**: FVAP-01, FVAP-02, FVAP-03, FVAP-04, FVAP-05, FVAP-06, MCAP-01, MCAP-02, MCAP-03, MCAP-04
**Success Criteria** (what must be TRUE):
  1. User sees a combined AP/AR tab in Fava with a KPI row showing AR total, AR overdue, AP total, and net position -- all values matching ledger data
  2. User can toggle between AR invoice list and AP bill list, with status badges (color-coded) and aging-based row coloring (green/yellow/red)
  3. User sees a Chart.js horizontal stacked bar chart showing aging distribution across buckets for both AR and AP
  4. User can create new AR invoices and AP bills via inline web forms without leaving the Fava interface
  5. Dashboard homepage displays a net AR/AP position KPI card alongside existing financial KPIs
  6. Claude can list AP bills, create new bills, record payments, and generate aging reports via MCP tools (`ap_list`, `ap_add`, `ap_pay`, `ar_aging`, `ap_aging`, `apar_summary`)
**Plans**: 3 plans

Plans:
- [ ] 14-01-PLAN.md -- Fava extension backend (ComptesFournisseursExtension), KPI row, AR/AP list tables with badges/aging colors, Chart.js aging chart, dashboard KPI, registration
- [ ] 14-02-PLAN.md -- Inline AR invoice creation form and AP bill creation form with POST endpoints, dynamic line items, live tax calculation
- [ ] 14-03-PLAN.md -- MCP tools: ap_list, ap_add, ap_pay, ar_aging, ap_aging, apar_summary with tests

### Phase 15: Receipt-to-AP Pipeline & Auto-matching UX
**Goal**: Uploading a receipt can flow directly into AP bill creation, and bank transactions in the approval queue show match suggestions for linking to open AR/AP entries
**Depends on**: Phase 14
**Requirements**: RCAP-01, RCAP-02, RCAP-03, RCAP-04
**Success Criteria** (what must be TRUE):
  1. After uploading a receipt and AI extraction completes, user sees a "Creer une facture fournisseur?" prompt with extracted data summary
  2. Clicking the prompt navigates to the AP bill form pre-filled with vendor name, amount, line items, dates, and tax flags from the receipt
  3. Bank transactions in the approval queue display match suggestions when they correspond to open AR invoices or AP bills, showing confidence and matched entry details
  4. User can link a bank transaction to an AR invoice or AP bill with a single "Lier" button click, which records the payment and updates the entry status
**Plans**: 2 plans

Plans:
- [ ] 15-01-PLAN.md -- Receipt-to-AP creation prompt: enhance upload endpoint with tax breakdown, add "Creer facture fournisseur" button to RecusExtension with query parameter pre-fill
- [ ] 15-02-PLAN.md -- Approval queue auto-matching UX: enrich pending transactions with AR/AP match suggestions, match suggestion rows with "Lier" button, lier_apar endpoint

## Progress

**Execution Order:**
v1.2 phases execute in numeric order: 11 -> 12 -> 13 -> 14 -> 15

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Ledger Foundation and Import Pipeline | v1.0 | 3/3 | Complete | 2026-02-18 |
| 2. Quebec Domain Logic | v1.0 | 5/5 | Complete | 2026-02-19 |
| 3. AI Categorization and Review Workflow | v1.0 | 3/3 | Complete | 2026-02-19 |
| 4. MCP Server and Web Dashboard | v1.0 | 5/5 | Complete | 2026-02-19 |
| 5. Reporting, CPA Export, and Document Management | v1.0 | 5/5 | Complete | 2026-02-19 |
| 6. Design System Foundation | v1.1 | 0/2 | Not started | - |
| 7. Dashboard Homepage | v1.1 | 0/2 | Planned | - |
| 8. Table and Extension Polish | v1.1 | 0/2 | Not started | - |
| 9. Receipt Upload UX | v1.1 | 0/2 | Not started | - |
| 10. Cross-Cutting Polish and Validation | v1.1 | 2/2 | Complete | 2026-02-25 |
| 11. AP Foundation | 2/2 | Complete    | 2026-02-26 | - |
| 12. Aging, AR Enhancements & CLI | 1/2 | In Progress|  | - |
| 13. Recurring Invoices & Auto-matching | v1.2 | 0/0 | Not started | - |
| 14. Fava Extension Tab & MCP | v1.2 | 0/3 | Planned | - |
| 15. Receipt-to-AP Pipeline & Auto-matching UX | v1.2 | 0/0 | Not started | - |
