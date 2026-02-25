# Feature Landscape: Production UI/UX for CompteQC v1.1

**Domain:** Accounting dashboard UI/UX (fintech-grade polish for Fava-based app)
**Researched:** 2026-02-25
**Confidence:** MEDIUM (UI patterns well-established across industry; Fava-specific implementation constraints need validation during build)

---

## Context

CompteQC v1.0 is functionally complete: import, categorize, review, payroll, CCA, GST/QST, CPA export all work. The UI uses Fava extensions with a custom Quebec blue theme (`ThemeQCExtension.js` injecting ~1,200 lines of CSS), Jinja2 templates, and vanilla JS. The existing design system includes `cqc-kpi`, `cqc-table`, `cqc-card`, `cqc-badge`, `cqc-btn`, and `cqc-dropzone` component classes.

v1.1 focuses exclusively on making it look and feel like a real fintech product -- competing with QuickBooks/Xero on visual polish while staying within Fava's extension architecture (no custom frontend framework).

---

## Table Stakes

Features users expect from any modern accounting dashboard. Missing = the product feels like a developer prototype, not a real tool.

| Feature | Why Expected | Complexity | Fava Dependency | Notes |
|---------|--------------|------------|-----------------|-------|
| **Dashboard homepage with KPI summary** | QuickBooks, Xero, FreshBooks, Wave all open to a financial snapshot. The landing page IS the product's first impression. The "5-second rule": glance and know your financial state. | Medium | New Fava extension (`TableauBordExtension`) with Python backend to query Beancount balances | Must show: YTD revenue, YTD expenses, net income, cash position (bank balance), pending approvals count. Top of page, above the fold. |
| **KPI cards with semantic coloring** | Every accounting SaaS uses colored metric cards (green=positive, red=negative, amber=warning). Their absence signals prototype-grade tool. | Low | Extend existing `cqc-kpi` classes in ThemeQCExtension | Already partially implemented in TaxesQC and PaieQC. Need consistency: same card dimensions, same label/value/trend layout across ALL extensions. |
| **Revenue trend line chart** | The single most common dashboard visualization across QuickBooks, Xero, and Wave. Monthly revenue over time is the metric every business owner checks first. | Medium | Chart.js line chart injected via JS module (decision already pending in PROJECT.md) | Monthly granularity. 12-month rolling window. Use `--qc-blue` for the line. Area fill with low opacity for visual weight. |
| **Expense breakdown chart** | Donut/pie showing where money goes by category. Present in every competitor dashboard. Answers "what am I spending on?" at a glance. | Medium | Chart.js doughnut chart | Donut preferred over pie (cleaner look, allows center label showing total). Top 6 categories + "Autres" bucket. Use semantic colors from the palette. |
| **Table hover states** | Modern tables highlight rows on hover. Without this, data tables feel dead and static. Every SaaS product does this. | Low | CSS addition to `cqc-table` in ThemeQCExtension | Already have `--qc-transition: 180ms` variable. Add `tbody tr:hover { background: var(--qc-blue-lighter); }`. Trivial but visually impactful. |
| **Consistent spacing and typography hierarchy** | Inconsistent padding, font sizes, or whitespace between extensions breaks the "single product" illusion. Users notice rhythm even subconsciously. | Low | Audit and normalize ThemeQCExtension CSS | Check all 8 extensions use the same spacing tokens. Ensure `cqc-page-header`, `cqc-section-title`, `cqc-card` have identical margins everywhere. |
| **Loading and empty states** | Pages with no data that show nothing (or flash unstyled) feel broken. Every polished app has thoughtful empty states. | Low | Per-extension template updates | Already have `cqc-empty` class. Ensure ALL extensions use it. Add skeleton placeholder for charts while Chart.js loads. |
| **Responsive table containers** | Tables that overflow and break layout on narrower viewports look unprofessional. TaxesQC has 8 columns -- this will break on < 1200px. | Low | CSS `overflow-x: auto` wrapper | Wrap all `cqc-table` in a scrollable container. Don't hide columns -- horizontal scroll is acceptable for data-dense tables. |
| **Confidence badges with visual urgency** | The 3-tier badge system (Elevee/Moderee/Revision) exists but "Revision" items need more visual weight to draw the eye. Urgent items should look urgent. | Low | CSS refinement in ApprobationExtension | Make "Revision" badge use `--qc-error` with subtle pulse or larger size. "Elevee" can be muted. Visual weight should scale inversely with confidence. |

## Differentiators

Features that elevate CompteQC from "functional tool" to "polished fintech product." Not expected by default, but create delight and signal quality.

| Feature | Value Proposition | Complexity | Fava Dependency | Notes |
|---------|-------------------|------------|-----------------|-------|
| **KPI count-up animation** | Numbers animate from 0 to final value on page load (~800ms). Used by Stripe Dashboard, Mercury, and modern fintech apps. Creates immediate sense of dynamism and polish. | Low | JS in ThemeQCExtension or per-extension `<script>` | `requestAnimationFrame` with ease-out curve. Only on initial render. Format with `toLocaleString('fr-CA')` for proper number formatting. Target all `.cqc-kpi-value` elements. |
| **Cash flow bar chart (inflows vs outflows)** | Stacked bar chart showing monthly revenue (green) vs expenses (red). More insightful than separate numbers. QuickBooks Advanced has this; most small-biz tools don't. | Medium | Chart.js stacked bar chart | Monthly bars with positive (revenue) stacked above zero, negative (expenses) below. Optional net line overlay. Provides the "trajectory" view that line charts alone miss. |
| **Upload progress animation + file preview** | Animated progress bar during receipt upload, with image thumbnail or PDF icon preview. Current upload is fire-and-forget with no visual feedback. | Medium | JS enhancement to RecusExtension form handler | Use `FileReader` API for instant image preview. CSS-animated progress bar (even simulated for fast local uploads -- the animation IS the feedback). Show file type icon for non-image files. |
| **Bulk approval with keyboard shortcuts** | Power-user feature: Shift+click for range selection, Enter to approve, Space to toggle rows. Current bulk action is mouse-click-only. | Medium | JS enhancement to ApprobationExtension | Shift+click range select is the key unlock. Also: up/down arrow navigation with visual focus indicator. Power users will process 50 transactions in seconds. |
| **Transaction row expansion (inline detail)** | Click a row to expand and see: AI reasoning, source file link, confidence breakdown, account suggestion rationale. No page navigation needed. | High | JS accordion + template changes in ApprobationExtension | Valuable for the approval workflow -- see why AI chose a category without leaving the queue. Uses `<tr class="detail-row">` inserted after each data row, toggled on click. |
| **Smooth page transitions** | CSS fade-in when switching between Fava extensions. Content slides or fades in rather than hard-cutting. | Low | CSS `@keyframes` in ThemeQCExtension | `animation: fadeIn 200ms ease-out` on main content container. Subtle but makes navigation feel cohesive rather than page-reload-y. |
| **Period selector for dashboard** | Button group (MTD / QTD / YTD / 12M) to switch dashboard timeframe. | Medium | Dashboard extension JS + Python backend date filtering | Requires backend to accept date range params and filter balance queries. Start with YTD as default. MTD useful for monthly monitoring. |
| **Sidebar notification badge** | Red badge with pending approval count on the "Approbation" sidebar link. Draws attention to items needing action without visiting the page. | Low | ThemeQCExtension.js DOM manipulation of Fava sidebar | Inject a `<span class="cqc-badge-nav">N</span>` into the sidebar link. Fetch count via a lightweight API call or embed in page data. |
| **Contextual French tooltips** | Hover over accounting jargon (CTI, RTI, DPA, UCC, etc.) to see a plain-French explanation. Pedagogical feature already planned in PROJECT.md. | Low | CSS-only tooltips using `[data-tooltip]::after` | No JS library needed. Pure CSS hover tooltips. Add `data-tooltip="Credit de taxe sur les intrants..."` to abbreviations. Builds the "teaching tool" identity. |
| **GST/QST period status stepper** | Horizontal progress bar showing which filing periods are complete, current, or upcoming. Visual timeline instead of just a table. | Medium | TaxesQC template enhancement | Stepper UI with checkmarks for filed periods, highlighted current period, grey future. Adds "am I on track?" context that the raw table doesn't provide. |

## Anti-Features

Features to explicitly NOT build. Each adds complexity disproportionate to value for a self-hosted, solo-user accounting tool.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Customizable dashboard layout (drag-to-rearrange widgets)** | Grid-based dashboard builders (Grafana-style) are enormously complex. Solo user has one workflow. The time spent building a widget system exceeds the time spent using it. | Fixed, opinionated layout. One dashboard that works well. Change it in code when needed -- you are the only user. |
| **Dark mode toggle** | Building a proper dark mode for all custom CSS across 8 extensions is significant maintenance burden. Fava has its own partial dark mode that conflicts. The dark sidebar already provides visual contrast. | Keep the Quebec blue light theme. Dark sidebar is enough contrast. |
| **Animated chart transitions on every data change** | Gratuitous animation slows perceived performance and annoys power users doing rapid comparisons. Charts should update instantly when data changes. | Animate only on initial page load. Subsequent data updates (period changes, filters) should render instantly. |
| **Mobile-responsive full redesign** | PROJECT.md says web-first, desktop access. Responsive grid layout across 8 extensions is high effort for a tool used at a desk. | Ensure nothing breaks catastrophically below 1024px. Don't optimize for phone. Scrollable tables are sufficient. |
| **AI-generated dashboard commentary** | PROJECT.md explicitly excludes this. "Revenue is trending up 12% -- great job!" is either obvious or hallucinatory. Numbers speak for themselves. | Show numbers clearly with semantic coloring. Let the human interpret. Tooltips educate, AI doesn't narrate. |
| **Multi-language toggle (EN/FR)** | User is francophone. Building i18n infrastructure (message catalogs, language switching, RTL concerns) for one person is pure waste. | Everything in French. English technical terms in code are fine. |
| **Infinite scroll or virtualized tables** | Data volume is tiny: ~30 transactions/month, ~12 payroll entries/year, ~4 tax periods. Pagination or virtual scroll adds complexity solving a problem that doesn't exist. | Render full tables. Filter by period if needed. |
| **Real-time WebSocket updates** | Solo user. No concurrent editors. No live bank feed. Real-time infrastructure (WebSocket server, reconnection logic, state sync) solves nothing. | Standard page load. Refresh to see updates. |
| **Custom charting library** | Chart.js handles line, bar, doughnut, and area charts. Building custom SVG visualizations or adopting D3.js adds massive complexity for marginal visual improvement. | Chart.js with thoughtful configuration. Use its built-in animations and responsive sizing. |

## Feature Dependencies

```
FOUNDATION LAYER (must complete first):
  Theme CSS audit (spacing, typography, shadows)
    --> Table hover states (CSS)
    --> Consistent card sizing
    --> Badge refinement
    --> All other visual features inherit these styles

DASHBOARD LAYER (highest impact, depends on foundation):
  Dashboard homepage extension (Python + HTML)
    --> KPI cards (revenue, expenses, net income, cash, pending count)
    --> Chart.js setup (CDN or vendored JS)
        --> Revenue trend line chart
        --> Expense breakdown donut chart
        --> Cash flow bar chart (can defer)
    --> KPI count-up animation (JS on top of cards)
    --> Period selector (JS + Python date filtering)

EXTENSION POLISH LAYER (independent of dashboard):
  Receipt upload animation + preview
    --> Depends on: existing RecusExtension dropzone
  Approval queue keyboard shortcuts
    --> Depends on: existing ApprobationExtension table
  Transaction row expansion
    --> Depends on: table hover states + ApprobationExtension
  Sidebar notification badge
    --> Depends on: ThemeQCExtension sidebar DOM access

FINISHING LAYER (after all above):
  Page transitions (CSS animation)
  Contextual French tooltips (data-tooltip attributes)
  GST/QST period stepper (TaxesQC template)
```

## MVP Recommendation

### Priority 1 -- Foundation (everything depends on this)

1. **Theme CSS audit and refinement** -- Normalize spacing, typography scale, shadow usage, and card dimensions across all 8 extensions. This is the invisible work that makes everything else look coherent. Estimated: 1 plan.
2. **Table hover states and row styling** -- Add hover backgrounds, improve column alignment, ensure `.montant` columns right-align consistently. Estimated: part of plan 1.
3. **Loading/empty states audit** -- Verify all extensions handle zero-data gracefully. Estimated: part of plan 1.

### Priority 2 -- Dashboard (highest visible impact)

4. **Dashboard homepage extension** -- New `TableauBordExtension` with Python backend querying Beancount for KPI values. KPI cards row at top. Estimated: 1 plan.
5. **Revenue trend line chart** -- Chart.js line chart, monthly, 12-month rolling. Estimated: part of dashboard plan.
6. **Expense breakdown donut chart** -- Chart.js doughnut, top 6 categories. Estimated: part of dashboard plan.

### Priority 3 -- Micro-interactions (the polish that signals quality)

7. **KPI count-up animation** -- JS `requestAnimationFrame` on `.cqc-kpi-value`. Estimated: small task within a plan.
8. **Page transitions** -- CSS `fadeIn` animation on content load. Estimated: small task.
9. **Sidebar notification badge** -- Pending approval count on nav link. Estimated: small task.

### Priority 4 -- Extension-specific upgrades

10. **Receipt upload animation + file preview** -- Progress bar, image thumbnail, file type icon. Estimated: 1 plan.
11. **Approval queue UX** -- Keyboard shortcuts, range selection, improved visual scanning. Estimated: 1 plan.
12. **Contextual French tooltips** -- `data-tooltip` on accounting jargon across all extensions. Estimated: part of a plan.

### Defer

- **Cash flow waterfall chart** -- Revenue trend + expense donut cover 80% of insight. Add later.
- **Transaction row expansion** -- High complexity. Current detail workflow (view in Fava journal) works. Revisit if approval queue becomes bottleneck.
- **Period selector** -- Start with YTD fixed view. Add switching only after dashboard proves its value.
- **GST/QST period stepper** -- Current table view works. Visual sugar, not a functional improvement.

## Competitor Pattern Reference

### QuickBooks Online
- **Dashboard:** KPI cards at top (income, expenses, profit/loss) with trend arrows. Below: income vs expenses bar chart, expense breakdown pie, recent transactions.
- **Tables:** Clean with subtle alternating row shading, hover highlights, inline action buttons on hover.
- **Navigation:** Left sidebar with icon + text. Active item highlighted with colored left border.
- **Pattern to adopt:** KPI cards as first thing visible. Big number + small label above + trend indicator (arrow + percentage) below. This is the target layout for CompteQC dashboard cards.

### Xero
- **Dashboard:** Cash flow front and center. Outstanding invoices and bills as separate summary sections. Bank account reconciliation status prominent.
- **Tables:** Minimal decoration, generous whitespace. Click-to-expand for row details.
- **Pattern to adopt:** "X transactions to review" as a prominent call-to-action card on the dashboard, linking to the approval queue.

### FreshBooks
- **Dashboard:** Revenue summary (outstanding, overdue, in draft). Profit/loss bar chart. Recent activity sidebar.
- **Pattern to adopt:** Outstanding amounts with status breakdown (not just a total, but how much is overdue vs current). Activity feed concept could work for recent AI categorizations.

### Wave
- **Dashboard:** Simple P&L chart, cash flow chart, minimal widgets. Clean and uncluttered.
- **Pattern to adopt:** Restraint. Wave proves 3-4 well-chosen visualizations beat 20 widgets. CompteQC should have exactly the right amount of information, no more.

### Stripe Dashboard (aspirational target for fintech polish)
- **KPI cards:** Large bold numbers with sparkline trends inline. Semantic coloring (green for growth).
- **Micro-interactions:** Count-up on page load. Hover reveals exact values on chart data points. Smooth transitions between views.
- **Pattern to adopt:** The count-up animation, the sparkline-in-card concept, and the "calm confidence" of the visual design. This is what "fintech polish" means in practice.

## Complexity Summary

| Feature Category | Count | Avg Complexity | Estimated Plans |
|-----------------|-------|----------------|-----------------|
| Table Stakes | 9 | Low-Medium | 2-3 |
| Differentiators (selected) | 6-8 | Low-Medium | 2-3 |
| Anti-Features (avoided) | 9 | -- | 0 (saved effort) |
| **Total estimated** | | | **4-6 plans** |

## Sources

- [Fintech UX Best Practices 2026 - Eleken](https://www.eleken.co/blog-posts/fintech-ux-best-practices)
- [7 Fintech UX Design Trends 2025 - Design Studio](https://www.designstudiouiux.com/blog/fintech-ux-design-trends/)
- [Top 10 Fintech UX Design Practices 2026 - Onething](https://www.onething.design/post/top-10-fintech-ux-design-practices-2026)
- [Complex Approvals App Design - UXPin](https://www.uxpin.com/studio/blog/complex-approvals-app-design/)
- [12 Financial Dashboard Examples - Qlik](https://www.qlik.com/us/dashboard-examples/financial-dashboards)
- [26 Financial Dashboard Examples - Coupler.io](https://blog.coupler.io/financial-dashboards/)
- [Building Modern Drag-and-Drop Upload UI 2025 - Filestack](https://blog.filestack.com/building-modern-drag-and-drop-upload-ui/)
- [File Uploader UX Best Practices - Uploadcare](https://uploadcare.com/blog/file-uploader-ux-best-practices/)
- [QuickBooks Dashboard KPIs - Klipfolio](https://www.klipfolio.com/resources/dashboard-examples/executive/quickbooks-accounting-dashboard)
- [Chart.js Official Documentation and Samples](https://www.chartjs.org/docs/latest/samples/)
- [Fintech UX Design Complete Guide - Webstacks](https://www.webstacks.com/blog/fintech-ux-design)
- [Fintech UX Design Best Practices for Financial Dashboards - Wildnet](https://www.wildnetedge.com/blogs/fintech-ux-design-best-practices-for-financial-dashboards)

---
*Feature research for: CompteQC v1.1 Production UI/UX milestone*
*Researched: 2026-02-25*
