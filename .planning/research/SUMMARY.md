# Project Research Summary

**Project:** CompteQC v1.1 -- Production UI/UX Polish
**Domain:** Fintech-grade UI polish for a Fava/Beancount accounting extension system
**Researched:** 2026-02-25
**Confidence:** HIGH

## Executive Summary

CompteQC v1.0 is functionally complete (import, categorize, payroll, CCA, GST/QST, CPA export), but the UI remains developer-grade. v1.1 is a pure visual polish milestone that must work entirely within Fava's extension architecture -- no build step, no custom frontend framework, no npm. The research confirms this is achievable with only two new JS dependencies (Chart.js 4.4.8 at 204 KB and CountUp.js 2.9.0 at 8 KB), both loaded as UMD bundles via dynamic script injection. Everything else -- animations, table styling, page transitions, hover states -- is pure CSS injected through the existing ThemeQCExtension.js pattern.

The recommended approach treats ThemeQCExtension.js as the single client-side orchestrator for all UI behavior across all extensions. A new `TableauBordExtension` provides the dashboard homepage (the highest-impact addition), while existing extensions receive incremental polish through data attributes that the theme module discovers and processes on `onPageLoad()`. The critical architectural pattern is the "data attribute bridge": templates embed JSON in `data-chart` and `data-value` attributes, and the JS module renders charts and animations after each SPA navigation. This bypasses Fava's limitation where `<script>` tags inserted via innerHTML do not execute.

The top risks are Chart.js memory leaks from missing cleanup on SPA navigation (solved with a chart registry and destroy-on-load pattern), CSS `!important` escalation (91 existing uses that should migrate to Fava's CSS variable system), and DOM mutations lost during navigation (solved by replacing boolean flags with DOM presence checks). All three have clear, validated prevention strategies. The receipt upload endpoint also needs conversion from HTML redirects to JSON responses before any upload UX polish can proceed.

## Key Findings

### Recommended Stack

The existing stack (Python 3.12, Beancount v3, Fava, ThemeQCExtension.js with CSS-in-JS, Inter font) remains unchanged. Two libraries are added.

**New dependencies:**
- **Chart.js 4.4.8 (UMD):** Dashboard charts (line, doughnut, bar) -- 204 KB, loaded via CDN or vendored Flask route. Chosen over ECharts (5x smaller) and D3 (too low-level). Must use UMD format because Chart.js ESM has a known bare specifier issue (`@kurkle/color`) that cannot be resolved without import maps.
- **CountUp.js 2.9.0 (UMD):** KPI number animation -- 8 KB, small enough to inline in the JS module. Handles French-Canadian number formatting (space as thousand separator, comma as decimal). Could be replaced by a custom `requestAnimationFrame` implementation if the dependency is unwanted.
- **Pure CSS animations:** All transitions, hover states, page-entry effects, and staggered card entrances use CSS `@keyframes` and existing `--qc-transition` custom properties. No animation library needed (Animate.css at 80 KB and GSAP at 120 KB both rejected as overkill).

**Critical constraint:** Fava only auto-serves one JS file per extension (matching the class name). External libraries must load via dynamic `<script>` injection or a Flask route. No build step, no npm, no import maps.

**Total additional payload:** ~212 KB JS (loaded on demand, browser-cached). 0 KB additional CSS (injected via existing JS pattern).

### Expected Features

**Must have (table stakes):**
- Dashboard homepage with KPI summary (revenue, expenses, net income, cash, pending approvals)
- KPI cards with semantic coloring (green/red/amber) and consistent dimensions across all extensions
- Revenue trend line chart (monthly, 12-month rolling)
- Expense breakdown doughnut chart (top 6 categories + "Autres")
- Table hover states and consistent row styling with `tabular-nums` for money columns
- Consistent spacing and typography hierarchy across all 8 extensions
- Loading and empty states for all data views
- Responsive table containers (horizontal scroll on narrow viewports)
- Confidence badges with visual urgency scaling

**Should have (differentiators):**
- KPI count-up animation (numbers animate from 0 to value, 600ms ease-out)
- Cash flow bar chart (monthly inflows vs outflows)
- Smooth page transitions (CSS fade-in on SPA navigation)
- Sidebar notification badge (pending approval count)
- Contextual French tooltips on accounting jargon (CTI, RTI, DPA, UCC)
- Upload progress animation with file preview (image thumbnail or PDF icon)
- Bulk approval keyboard shortcuts (Shift+click range select, Enter to approve)

**Defer (v2+):**
- Cash flow waterfall chart -- revenue trend + expense donut cover 80% of insight
- Transaction row expansion (inline detail accordion) -- high complexity, current Fava journal view works
- Period selector for dashboard -- start with YTD fixed view
- GST/QST period status stepper -- current table view is functional
- Customizable dashboard layout, dark mode, mobile-responsive redesign, multi-language toggle, real-time WebSocket updates, infinite scroll

### Architecture Approach

All client-side behavior lives in ThemeQCExtension.js, the single JS module that persists across Fava's SPA navigations. Templates pass data to JS via `data-*` attributes (the "data attribute bridge" pattern). Chart.js is loaded lazily with a cached Promise to prevent duplicate script injections. Every function called from `onPageLoad()` must be idempotent -- safe to call multiple times, cleaning up previous state before re-creating.

**Major components:**
1. **ThemeQCExtension.js** -- CSS injection, Chart.js loading, chart rendering engine (`renderCharts()` scanning for `[data-chart]` containers), page transitions, KPI animations (`animateKPIs()` scanning for `[data-value]` elements), tooltip system, receipt upload UX. Single orchestrator for all client-side behavior.
2. **TableauBordExtension** -- New Python extension (FavaExtensionBase subclass) computing KPIs and monthly data series from Beancount entries. Exposes `kpis()` returning dict and `chart_data_json()` returning Chart.js-compatible JSON string. Template embeds JSON in data attributes for JS pickup.
3. **Chart.js (CDN/vendored)** -- Canvas-based chart rendering via `window.Chart` global. Three chart types: line (revenue trend), doughnut (expense breakdown), bar (cash flow). Instances stored in module-level registry for destroy-on-load cleanup.
4. **Existing 8 extensions** -- Receive incremental polish: `data-value` attributes on KPI elements for count-up, refined CSS classes, improved template structure. No Python logic changes needed for most extensions.

**Key patterns:**
- Data attributes as template-to-JS bridge (because `<script>` in innerHTML does not execute)
- Idempotent `onPageLoad()` functions (because the JS module persists but DOM is replaced)
- Lazy CDN loading with Promise caching (load once, use everywhere)
- Chart destroy-before-create (prevent memory leaks on SPA navigation)

**Anti-patterns to avoid:**
- `<script>` blocks in Jinja2 templates for non-trivial logic
- Multiple `has_js_module` extensions competing to modify DOM
- Relying on Chart.js instance state across SPA navigations
- Global CSS animations on unscoped selectors (must use `.cqc-*` prefix)

### Critical Pitfalls

1. **Chart.js memory leak on SPA navigation** -- Chart instances accumulate because Fava has no `onPageUnload` callback. Store instances in a module-level `Map<string, Chart>` registry; destroy all at the top of every `onPageLoad()` before creating new ones. Detect with Chrome DevTools heap snapshots or `Chart.getChart(canvas)`.

2. **CSS `!important` escalation** -- 91 existing `!important` declarations vs. Fava's 0 (Fava uses 40+ CSS custom properties as the intended theming mechanism). Audit all uses; migrate to overriding `:root` variables. Reserve `!important` only for Svelte-scoped inline styles that cannot be overridden otherwise.

3. **DOM mutations lost on navigation** -- Boolean flags in JS module scope say "already injected" but the DOM element was destroyed by innerHTML replacement. Replace all boolean flags with `document.querySelector()` checks for actual DOM presence.

4. **Upload breaks SPA context** -- RecusExtension endpoint returns raw HTML strings and performs full-page redirect via form POST. Convert to AJAX with JSON responses before adding any upload UX polish. Use XHR (not fetch) for upload progress tracking.

5. **Accessibility regressions from visual polish** -- Adding animations without `prefers-reduced-motion` guards, removing focus outlines, relying on color alone for badges. Add `@media (prefers-reduced-motion: no-preference)` wrapper to all animation/transition rules from day one. Current tooltip system already handles keyboard focus (good).

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation -- Chart.js Infrastructure and Design System Hardening

**Rationale:** Every subsequent phase depends on Chart.js loading, the chart rendering engine, animation utilities, and a cleaned-up CSS foundation. The three critical pitfalls (#1 chart leak, #2 `!important` war, #3 DOM flag bug) must be solved here before any visual work begins. Self-hosting the Inter font eliminates the Google Fonts external dependency.
**Delivers:** Chart.js lazy loader with destroy-on-load registry, `renderCharts()` engine with Quebec color palette, `animateKPIs()` with `requestAnimationFrame`, page-entry CSS animation, `!important` audit and CSS variable migration, self-hosted Inter font, `prefers-reduced-motion` guard on all animations, enhanced table hover states, consistent spacing/typography tokens, loading/empty state audit, responsive table containers.
**Addresses features:** Table hover states, consistent spacing/typography, loading/empty states, responsive tables, confidence badges, page transitions.
**Avoids pitfalls:** Chart.js memory leak (#1), CSS `!important` war (#2), DOM mutation loss (#3), FOUC (#5), accessibility regression (#7), offline font failure (#8).

### Phase 2: Dashboard Homepage

**Rationale:** The dashboard is the highest-impact visual addition and the primary showcase for Chart.js. It validates the entire data flow (Python -> JSON -> data attribute -> Chart.js) end-to-end. Must come before extension polish because it introduces the data attribute bridge pattern that other extensions will adopt for KPI animations.
**Delivers:** New `TableauBordExtension` with KPI cards (revenue YTD, expenses YTD, net income, cash position, pending approval count), revenue trend line chart (12-month rolling), expense breakdown doughnut chart (top 6 + Autres), cash flow bar chart (monthly). Sidebar updated with "Tableau de bord" at top position.
**Uses:** Chart.js 4.4.8 UMD, CountUp.js 2.9.0 (or custom implementation), data attribute bridge pattern.
**Implements:** TableauBordExtension component, chart data flow architecture, KPI count-up animation on dashboard.

### Phase 3: Existing Extension Polish

**Rationale:** With foundation and dashboard complete, proven patterns (data-value attributes, refined CSS) are applied incrementally across all 8 existing extensions. Low risk: adding a `data-value` attribute to a template is minimal change with high visual impact. Extensions can be polished independently.
**Delivers:** KPI count-up animations across PaieQC, TaxesQC, PretActionnaire, Echeances. Enhanced table row styling. Approval queue visual hierarchy improvements and keyboard shortcuts (Shift+click, Enter, Space). Consistent card/section styling. Sidebar notification badge for pending approvals. Contextual French tooltips on accounting jargon.
**Addresses features:** KPI card consistency, count-up animation, sidebar badge, tooltips, keyboard shortcuts, confidence badge urgency.

### Phase 4: Receipt Upload UX

**Rationale:** Isolated as its own phase because it requires both Python endpoint changes (JSON response mode) and complex JS (XHR with upload.onprogress). Has a clear prerequisite: the endpoint must return JSON before any UX polish is possible. Separating it prevents it from blocking other polish work.
**Delivers:** AJAX-based file upload via XHR, progress bar animation, image thumbnail preview (FileReader API), PDF/file type icon display, client-side validation (size limit, file type, duplicate detection via SHA-256 hash), animated drag-and-drop states, inline error handling with retry.
**Avoids pitfalls:** Upload breaks SPA context (#6).

### Phase 5: Final Polish and Validation

**Rationale:** Typography audit, shadow/spacing consistency check, cross-browser testing, and accessibility validation must happen after all features are in place. This is the "sand and varnish" phase.
**Delivers:** Typography scale audit (Inter font weights 400/500/600/700, consistent sizes), shadow and spacing audit across all extensions and Fava native pages, cross-browser verification (Safari, Chrome, Firefox), accessibility audit (keyboard navigation, screen reader, WCAG contrast ratios, `prefers-reduced-motion` verification).
**Avoids pitfalls:** Animation jank on large tables (#4), accessibility regression (#7), mobile layout issues (#9).

### Phase Ordering Rationale

- Phase 1 before everything because Chart.js lifecycle management, CSS variable migration, and animation guards are safety nets that prevent bugs in all subsequent phases.
- Phase 2 before Phase 3 because the dashboard validates the data attribute bridge pattern end-to-end; if it works for charts, the simpler KPI count-up pattern is guaranteed to work across other extensions.
- Phase 3 before Phase 4 because extension polish is lower-risk (adding attributes to templates) and delivers broad visual improvement across the entire app, while upload UX is high-effort for a single extension.
- Phase 4 is isolated because it requires Python endpoint changes, making it architecturally distinct from CSS/JS-only work in other phases.
- Phase 5 last because polish audits only make sense after all features exist.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Dashboard):** The `TableauBordExtension` Python backend needs to query Beancount for monthly aggregates. Validate the exact API for querying entries by date range within a Fava extension against existing codebase patterns (e.g., how PaieQCExtension queries payroll data).
- **Phase 4 (Upload UX):** The RecusExtension endpoint modification (JSON response mode alongside existing redirect) needs careful testing for backward compatibility. XHR upload progress with Flask needs validation.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** All patterns are well-documented CSS and JS. Chart.js UMD loading proven by fava-dashboards project. CSS variable override is Fava's intended extension mechanism.
- **Phase 3 (Extension Polish):** Adding `data-value` attributes and CSS refinements follows established patterns already working in the codebase.
- **Phase 5 (Final Polish):** Standard cross-browser and accessibility testing procedures.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Only 2 new dependencies, both battle-tested UMD libraries. Loading pattern proven by fava-dashboards. CDN URLs and sizes verified. |
| Features | MEDIUM | Feature list well-defined from competitor analysis (QuickBooks, Xero, Stripe). Fava-specific implementation of some features (period selector, inline row expansion) needs build-time validation. |
| Architecture | HIGH | Data attribute bridge, single JS module orchestrator, and lazy CDN loading all verified against Fava source code and existing CompteQC patterns. Anti-patterns documented with root causes. |
| Pitfalls | HIGH | All pitfalls verified against actual source code: 91 `!important` counted, no `onPageUnload` confirmed in Fava source, raw HTML upload responses confirmed, boolean flag pattern identified. |

**Overall confidence:** HIGH

### Gaps to Address

- **Fava Flask route for vendored libraries:** The pattern of adding a custom Flask route inside a Fava extension (`_init_app` hook) to serve vendor files is untested. Start with CDN; validate vendoring only if offline operation becomes a requirement.
- **Fava `<article>` replacement behavior:** Page transition animation assumes Fava replaces `<article>` innerHTML (not the element itself). Needs runtime confirmation in Phase 1 before relying on the CSS class toggle + forced reflow trick.
- **Chart.js canvas sizing within Fava layout:** Chart.js responsive mode needs a container with explicit height. Fava's article area has variable height. May need explicit `height` or `aspect-ratio` CSS on `.cqc-chart-container` -- validate during Phase 2.
- **CountUp.js vs custom implementation:** The custom `requestAnimationFrame` approach in ARCHITECTURE.md handles French-Canadian formatting via `Intl.NumberFormat`. If it works correctly, CountUp.js dependency can be skipped entirely. Decide during Phase 1 implementation.

## Sources

### Primary (HIGH confidence)
- [Fava Extension API docs](https://beancount.github.io/fava/api/fava.ext.html) -- FavaExtensionBase, has_js_module, extension_endpoint
- [Fava Extension Help](https://fava.pythonanywhere.com/example-beancount-file/help/extensions) -- JS module lifecycle (init, onPageLoad, onExtensionPageLoad)
- [Fava GitHub Issue #1175](https://github.com/beancount/fava/issues/1175) -- SPA innerHTML script execution limitation (critical architectural constraint)
- [Chart.js Installation/Integration Docs](https://www.chartjs.org/docs/latest/getting-started/installation.html) -- UMD build, CDN options, no-build-step usage
- [Chart.js GitHub Issues #462, #7931, #11299](https://github.com/chartjs/Chart.js/issues/462) -- Memory leak patterns and destroy() requirement in SPAs
- [Chart.js ESM CDN Issue #11592](https://github.com/chartjs/Chart.js/issues/11592) -- Bare specifier problem confirms UMD is the right format
- [CountUp.js GitHub](https://github.com/inorganik/countUp.js) -- v2.9.0, UMD build, MIT license, 8 KB
- [MDN: CSS/JS animation performance](https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/CSS_JavaScript_animation_performance) -- Compositor-layer properties (transform, opacity)
- Fava source code: `/fava/ext/__init__.py` (verified no onPageUnload callback), `/fava/static/app.css` (verified 0 `!important`, 40+ CSS custom properties)
- CompteQC source: `ThemeQCExtension.js` (1,769 lines, 91 `!important`, boolean flag pattern), 8 extension templates, RecusExtension upload endpoint

### Secondary (MEDIUM confidence)
- [fava-dashboards (GitHub)](https://github.com/andreasgerstmayr/fava-dashboards) -- Proves external library loading works in Fava extensions (uses ECharts)
- Fintech UX references: [Eleken](https://www.eleken.co/blog-posts/fintech-ux-best-practices), [Onething](https://www.onething.design/post/top-10-fintech-ux-design-practices-2026), [UXPin](https://www.uxpin.com/studio/blog/complex-approvals-app-design/), [Qlik](https://www.qlik.com/us/dashboard-examples/financial-dashboards)
- Competitor dashboard analysis: QuickBooks, Xero, FreshBooks, Wave, Stripe Dashboard

### Tertiary (LOW confidence)
- Flask `_init_app` route for vendored files inside Fava extension -- pattern inferred from Flask docs, not tested in Fava context
- Fava `<article>` element vs innerHTML replacement behavior -- needs runtime validation

---
*Research completed: 2026-02-25*
*Ready for roadmap: yes*
