# Requirements: CompteQC v1.1 Production UI/UX

**Defined:** 2026-02-25
**Core Value:** Every dollar that flows through the corporation is correctly categorized, traceable to source documents, and ready for CPA review -- without manual data entry.

## v1.1 Requirements

Requirements for production UI/UX milestone. Each maps to roadmap phases.

### Design System (DSYS)

- [x] **DSYS-01**: CSS variable migration -- replace `!important` overrides with Fava CSS custom property theming
- [x] **DSYS-02**: Chart.js CDN loader with chart registry for SPA lifecycle (create/destroy on navigation)
- [x] **DSYS-03**: Animation safety nets -- `prefers-reduced-motion` guard and `requestAnimationFrame` wrapper
- [x] **DSYS-04**: Typography refinement -- tabular nums for amounts, tighter font-size scale, refined Inter weights

### Dashboard (DASH)

- [x] **DASH-01**: User sees KPI cards on dashboard homepage (Revenue YTD, Expenses YTD, Net Income, Tax Owing, Pending Approvals) with count-up animation
- [x] **DASH-02**: User sees monthly revenue trend as a Chart.js line chart on dashboard
- [x] **DASH-03**: User sees expense category breakdown as a Chart.js doughnut chart on dashboard
- [x] **DASH-04**: User sees last 10 transactions with status badges on dashboard

### Tables & Extensions (TBLX)

- [x] **TBLX-01**: All 8 extension tables have hover states, consistent padding, and visual header hierarchy
- [x] **TBLX-02**: Approval queue has redesigned confidence badges, keyboard shortcuts (approve/reject), and scannable layout
- [x] **TBLX-03**: Page entrance animations (fade + slide) on extension navigation
- [x] **TBLX-04**: Sidebar shows pending approval count badge on Approbation link

### Receipt Upload (RCPT)

- [x] **RCPT-01**: Upload endpoint converted from raw HTML to AJAX/JSON response
- [x] **RCPT-02**: User sees animated progress bar during file upload with percentage
- [x] **RCPT-03**: User sees file thumbnail preview after upload completes (PDF first page, image thumbnail)
- [x] **RCPT-04**: Drag-and-drop zone has animated border, hover glow, and multi-file support

## Future Requirements

Deferred to v1.2+. Tracked but not in current roadmap.

### Data Visualization Enhancements

- **VIZ-01**: Cash flow waterfall chart (monthly inflows vs outflows)
- **VIZ-02**: YoY comparison overlays on revenue/expense charts
- **VIZ-03**: Interactive drill-down from chart segments to transaction lists

### Advanced UX

- **UX-01**: Customizable dashboard card layout (drag-and-drop reorder)
- **UX-02**: Dark mode toggle
- **UX-03**: Keyboard shortcut system across all extensions
- **UX-04**: Batch receipt upload with AI auto-matching to transactions

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Custom frontend (React/Next.js) | Staying within Fava for v1.1 -- lower risk, builds on what works |
| Mobile-responsive redesign | Desktop-first solo tool; mobile adds significant complexity |
| Dark mode | Nice-to-have, not core to production polish -- defer to v1.2 |
| AI-generated chart commentary | LLMs hallucinate numbers; charts must show exact data only |
| Real-time data refresh / WebSocket | Fava is request-based; real-time adds architectural complexity |
| Customizable dashboard layout | Solo user -- fixed layout is simpler and sufficient |
| Animation library (GSAP, Framer) | Pure CSS + CountUp.js covers all needed animations |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DSYS-01 | Phase 6 | Complete |
| DSYS-02 | Phase 6 | Complete |
| DSYS-03 | Phase 6 | Complete |
| DSYS-04 | Phase 6 | Complete |
| DASH-01 | Phase 7 | Complete |
| DASH-02 | Phase 7 | Complete |
| DASH-03 | Phase 7 | Complete |
| DASH-04 | Phase 7 | Complete |
| TBLX-01 | Phase 8 | Complete |
| TBLX-02 | Phase 8 | Complete |
| TBLX-03 | Phase 8 | Complete |
| TBLX-04 | Phase 8 | Complete |
| RCPT-01 | Phase 9 | Complete |
| RCPT-02 | Phase 9 | Complete |
| RCPT-03 | Phase 9 | Complete |
| RCPT-04 | Phase 9 | Complete |

**Coverage:**
- v1.1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0

---
*Requirements defined: 2026-02-25*
*Last updated: 2026-02-25 after roadmap creation*
