# Roadmap: CompteQC

## Milestones

- **v1.0 MVP** -- Phases 1-5 (shipped 2026-02-25)
- **v1.1 Production UI/UX** -- Phases 6-10 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-5) -- SHIPPED 2026-02-25</summary>

- [x] Phase 1: Ledger Foundation and Import Pipeline (3/3 plans)
- [x] Phase 2: Quebec Domain Logic (5/5 plans)
- [x] Phase 3: AI Categorization and Review Workflow (3/3 plans)
- [x] Phase 4: MCP Server and Web Dashboard (5/5 plans)
- [x] Phase 5: Reporting, CPA Export, and Document Management (5/5 plans)

</details>

### v1.1 Production UI/UX (In Progress)

**Milestone Goal:** Transform CompteQC from functional to fintech-polished -- competing with QuickBooks on look, feel, and usability while staying within Fava's extension architecture.

- [ ] **Phase 6: Design System Foundation** - Chart.js infrastructure, CSS variable migration, animation guards, typography refinement
- [ ] **Phase 7: Dashboard Homepage** - KPI cards, revenue trend chart, expense breakdown chart, recent transactions
- [ ] **Phase 8: Table and Extension Polish** - Hover states, approval queue redesign, page transitions, sidebar badge
- [ ] **Phase 9: Receipt Upload UX** - AJAX endpoint, progress bar, file previews, drag-and-drop animation
- [ ] **Phase 10: Cross-Cutting Polish and Validation** - Typography audit, spacing consistency, cross-browser testing, accessibility verification

## Phase Details

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
**Plans**: TBD

Plans:
- [ ] 07-01: TableauBordExtension Python backend (KPI computation, monthly data series, chart data JSON)
- [ ] 07-02: Dashboard template and Chart.js rendering (KPI cards, line chart, doughnut chart, recent transactions)

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
**Plans**: TBD

Plans:
- [ ] 09-01: Convert upload endpoint to AJAX/JSON and implement XHR upload with progress tracking
- [ ] 09-02: File preview rendering, drag-and-drop animation, and multi-file support

### Phase 10: Cross-Cutting Polish and Validation
**Goal**: The entire UI feels like one cohesive product -- consistent typography, spacing, shadows, and behavior across all pages, verified across browsers and accessibility standards
**Depends on**: Phase 9
**Requirements**: None (cross-cutting quality gate validating all prior phases)
**Success Criteria** (what must be TRUE):
  1. Typography scale is consistent across all extensions -- headings, body text, and money amounts use the same sizes, weights, and spacing everywhere
  2. All interactive elements (buttons, links, badges, chart segments) work correctly in Safari, Chrome, and Firefox on macOS
  3. Keyboard-only navigation reaches every interactive element across all extensions without traps, and screen readers announce meaningful labels
  4. No visual regressions from v1.0 functionality -- all existing features (import, categorize, payroll, reports, export) remain fully operational
**Plans**: TBD

Plans:
- [ ] 10-01: Typography/spacing audit, cross-browser testing, accessibility verification, and regression check

## Progress

**Execution Order:**
Phases execute in numeric order: 6 -> 7 -> 8 -> 9 -> 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Ledger Foundation and Import Pipeline | v1.0 | 3/3 | Complete | 2026-02-18 |
| 2. Quebec Domain Logic | v1.0 | 5/5 | Complete | 2026-02-19 |
| 3. AI Categorization and Review Workflow | v1.0 | 3/3 | Complete | 2026-02-19 |
| 4. MCP Server and Web Dashboard | v1.0 | 5/5 | Complete | 2026-02-19 |
| 5. Reporting, CPA Export, and Document Management | v1.0 | 5/5 | Complete | 2026-02-19 |
| 6. Design System Foundation | v1.1 | 0/2 | Not started | - |
| 7. Dashboard Homepage | v1.1 | 0/2 | Not started | - |
| 8. Table and Extension Polish | v1.1 | 0/2 | Not started | - |
| 9. Receipt Upload UX | v1.1 | 0/2 | Not started | - |
| 10. Cross-Cutting Polish and Validation | v1.1 | 0/1 | Not started | - |
