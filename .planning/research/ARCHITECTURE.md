# Architecture Patterns

**Domain:** Production UI/UX integration into Fava extension architecture
**Researched:** 2026-02-25
**Confidence:** HIGH

## Recommended Architecture

### How Fava Works (Critical Context)

Fava is a **single-page application**. It intercepts all sidebar link clicks and asynchronously fetches page content via AJAX, replacing only the `<article>` element innerHTML. This has three major implications:

1. **`<script>` tags in templates never execute on SPA navigation** -- browsers refuse to execute scripts inserted via innerHTML (per HTML spec). This is why the existing system uses `has_js_module = True` with a separate `.js` file instead.
2. **The JS module persists across navigations** -- `init()` runs once on first page load, `onPageLoad()` runs on every SPA navigation (including first load). The module's closure state survives across pages.
3. **The `<article>` element is the only thing that changes** -- header, sidebar, and any injected DOM outside `<article>` persist. CSS injected into `<head>` persists.

### Current Component Map

```
Fava (Flask/Svelte SPA)
  |
  +-- ThemeQCExtension (has_js_module=True, no report_title)
  |     +-- ThemeQCExtension.js (1,769 lines)
  |           - init(): injectStyle() [once]
  |           - onPageLoad(): injectStyle + brand + sidebar + reportHeader + tooltips [every nav]
  |           - THEME_CSS: ~1,050 lines of CSS as JS string constant
  |           - REPORT_INTROS: pedagogical headers per report
  |           - TOOLTIPS: 50+ tooltip definitions
  |           - reorganizeSidebar(): groups nav links into collapsible sections
  |
  +-- 8 Report Extensions (report_title set, no JS module)
  |     +-- ApprobationExtension -- approval queue with POST endpoints
  |     +-- PaieQCExtension -- payroll dashboard with KPI cards
  |     +-- TaxesQCExtension -- GST/QST tracking with period table
  |     +-- DpaQCExtension -- CCA/depreciation schedule
  |     +-- PretActionnaireExtension -- shareholder loan tracking
  |     +-- ExportCPAExtension -- CPA export package
  |     +-- EcheancesExtension -- fiscal deadline calendar
  |     +-- RecusExtension -- receipt upload with drag-and-drop
  |
  +-- Each extension follows the same pattern:
        Python: after_load_file() computes data, methods expose it
        Template: Jinja2 calls extension.method(), renders HTML
        Styling: .cqc-* CSS classes from ThemeQCExtension.js
```

### Data Flow: Python Extension to Template to JS

```
1. Fava loads ledger --> after_load_file() on each extension
2. Extension computes data (e.g., payroll_summary() returns list[dict])
3. User navigates to extension page
4. Fava renders Jinja2 template, calling extension.method() for data
5. Template outputs HTML with .cqc-* classes
6. Fava inserts HTML into <article> via innerHTML
7. ThemeQCExtension.js onPageLoad() fires:
   - Attaches tooltips to .cqc-table th elements
   - Injects report intro header based on URL path
   - Re-styles any Fava native components
```

## New Components for v1.1

### Component 1: Chart.js Loading (in ThemeQCExtension.js)

**What:** Load Chart.js library dynamically from CDN, expose it for chart rendering.

**Why in ThemeQCExtension.js:** Chart.js needs to load once and persist across SPA navigations. The theme module's `init()` is the only code that runs on first page load. Loading it per-page would cause flicker and re-downloads.

**Pattern:**
```javascript
// In ThemeQCExtension.js

let chartJsLoaded = false;
let chartJsPromise = null;

function loadChartJs() {
  if (chartJsLoaded) return Promise.resolve();
  if (chartJsPromise) return chartJsPromise;

  chartJsPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js';
    script.onload = () => { chartJsLoaded = true; resolve(); };
    script.onerror = reject;
    document.head.appendChild(script);
  });
  return chartJsPromise;
}
```

**Confidence:** HIGH -- the existing pattern of injecting `<link>` for Google Fonts (line 1061-1067 of ThemeQCExtension.js) proves this approach works within Fava. Chart.js UMD build exposes `window.Chart` globally.

### Component 2: Dashboard Extension (New Python Extension)

**What:** A new `TableauBordExtension` (FavaExtensionBase subclass) that serves as the homepage dashboard with KPI cards and Chart.js visualizations.

**Why a new extension:** The dashboard needs its own report page, its own data aggregation (revenue trends, expense breakdowns, cash flow), and its own template. It does not fit into any existing extension.

**Pattern:**
```python
class TableauBordExtension(FavaExtensionBase):
    report_title = "Tableau de bord"

    def after_load_file(self):
        # Aggregate: monthly revenue, expense by category, cash balance
        self._kpis = self._compute_kpis()
        self._monthly_data = self._compute_monthly_series()

    def kpis(self) -> dict:
        return self._kpis

    def chart_data_json(self) -> str:
        """Return JSON string for Chart.js consumption."""
        import json
        return json.dumps(self._monthly_data)
```

**Template data bridge -- the critical pattern:**
```html
<!-- TableauBordExtension.html -->
{% set kpis = extension.kpis() %}
{% set chart_json = extension.chart_data_json() %}

<div class="cqc-kpi-row">
  <!-- KPI cards as usual -->
</div>

<!-- Chart containers with data attributes for JS pickup -->
<div class="cqc-chart-container" id="cqc-revenue-chart"
     data-chart-type="line"
     data-chart='{{ chart_json }}'>
  <canvas></canvas>
</div>
```

**Why data attributes:** Since `<script>` tags in templates do not execute during SPA navigation, the template cannot call `new Chart()` directly. Instead, it embeds JSON data in `data-chart` attributes on container elements. The JS module's `onPageLoad()` scans for these containers and initializes charts.

**Confidence:** HIGH -- this is the standard pattern for Fava extensions that need JS interactivity. The existing `ApprobationExtension` uses inline `<script>` only for the trivial `toggleAll()` function, which works because it defines a global function that onclick handlers call synchronously (not via SPA re-navigation triggering script tags).

### Component 3: Chart Rendering Engine (in ThemeQCExtension.js)

**What:** A `renderCharts()` function called from `onPageLoad()` that discovers `[data-chart]` containers in the current `<article>` and renders Chart.js charts.

**Pattern:**
```javascript
async function renderCharts() {
  const containers = document.querySelectorAll('.cqc-chart-container[data-chart]');
  if (containers.length === 0) return;

  await loadChartJs();

  containers.forEach(container => {
    const canvas = container.querySelector('canvas');
    if (!canvas) return;

    // Destroy previous chart instance if exists (SPA re-navigation)
    if (canvas._cqcChart) {
      canvas._cqcChart.destroy();
    }

    const chartData = JSON.parse(container.dataset.chart);
    const chartType = container.dataset.chartType || 'bar';

    canvas._cqcChart = new Chart(canvas, {
      type: chartType,
      data: chartData,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { font: { family: "'Inter', sans-serif" } } }
        },
        // Use Quebec palette
        ...getChartThemeOptions()
      }
    });
  });
}

// Updated module export
export default {
  init() {
    injectStyle();
    loadChartJs(); // Pre-load on first page (non-blocking)
  },
  onPageLoad() {
    injectStyle();
    initTooltipPopup();
    injectBrand();
    reorganizeSidebar();
    injectReportHeader();
    attachTooltips();
    renderCharts(); // NEW: render any charts on the page
  },
};
```

**Why destroy + recreate:** Fava replaces `<article>` innerHTML on each navigation. When a user leaves the dashboard and comes back, the canvas elements are new DOM nodes. Any previous Chart.js instances are orphaned. The `canvas._cqcChart` reference lets us clean up properly if the same page is revisited without full innerHTML replacement (edge case).

**Confidence:** HIGH for the approach. Chart.js v4 UMD build exposes `window.Chart` which is accessible to the ES module.

### Component 4: Page Transition System (in ThemeQCExtension.js)

**What:** CSS-based fade transitions when Fava replaces `<article>` content during SPA navigation.

**Why CSS + JS class toggle:** Fava's navigation is not hookable before it happens -- `onPageLoad()` fires after content is already replaced. We cannot intercept the "leaving" moment. The best approach is a CSS animation on the incoming content, triggered via JS.

**Pattern:**
```javascript
function animatePageEntry() {
  const article = document.querySelector('article');
  if (!article) return;
  article.classList.remove('cqc-page-entering');
  // Force reflow to restart animation
  void article.offsetWidth;
  article.classList.add('cqc-page-entering');
}
```

```css
@keyframes cqc-page-enter {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.cqc-page-entering {
  animation: cqc-page-enter 200ms ease-out;
}
```

**Why this works:** Fava replaces `<article>` innerHTML, not the `<article>` element itself. The class toggle + reflow trick restarts the animation on every navigation. The animation is subtle (200ms, 6px vertical shift) -- enough to feel polished without being distracting.

**Confidence:** MEDIUM -- depends on exact Fava behavior regarding `<article>` element replacement vs innerHTML replacement. The JS-triggered class approach with forced reflow is the most reliable pattern. Needs testing to confirm.

### Component 5: KPI Count-Up Animation (in ThemeQCExtension.js)

**What:** Animated number count-up for `.cqc-kpi-value` elements when they appear.

**Pattern:**
```javascript
function animateKPIs() {
  const kpis = document.querySelectorAll('.cqc-kpi-value[data-value]');
  kpis.forEach(el => {
    const target = parseFloat(el.dataset.value);
    const duration = 600; // ms
    const start = performance.now();

    function tick(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = target * eased;
      el.textContent = new Intl.NumberFormat('fr-CA', {
        style: 'decimal',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(current) + ' $';
      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  });
}
```

**Template change:** KPI elements need `data-value` attributes:
```html
<div class="cqc-kpi-value" data-value="{{ totaux.salaire_brut_ytd }}">
  {{ "{:,.2f}".format(totaux.salaire_brut_ytd) }} $
</div>
```

The text content is the fallback (shown before JS runs or if JS fails). JS replaces it with the animated version.

**Confidence:** HIGH -- pure DOM manipulation, no Fava-specific constraints.

### Component 6: Enhanced Receipt Upload (Modify RecusExtension)

**What:** Progress bar, file preview thumbnails, animated drag-and-drop state.

**Current state:** The existing `RecusExtension.html` has basic drag-and-drop via inline event handlers that immediately submit the form. No progress indication, no preview.

**Architecture change:** The upload form should use `XMLHttpRequest` (not fetch -- fetch does not support upload progress) with progress tracking. The response handling moves into ThemeQCExtension.js.

**Pattern:** Add a `handleReceiptUpload()` function to ThemeQCExtension.js that:
1. Detects the `#upload-form` on RecusExtension pages via `onPageLoad()`
2. Intercepts form submission
3. Shows file preview (if image) or filename+icon (if PDF)
4. Uses XHR with `upload.onprogress` to show `.cqc-progress-bar` animation
5. On success, injects the new row into the recent uploads table without page reload

**Endpoint change required:** The Flask `@extension_endpoint("upload")` currently returns a redirect. It needs to return JSON when the request includes `Accept: application/json` or `X-Requested-With: XMLHttpRequest` header.

**Confidence:** MEDIUM -- the XHR approach works, but requires modifying the Python endpoint to support JSON responses alongside the existing redirect behavior.

## Component Boundaries

| Component | Location | Responsibility | Communicates With |
|-----------|----------|---------------|-------------------|
| ThemeQCExtension.js | JS module (persists across pages) | CSS injection, Chart.js loading, chart rendering, page transitions, KPI animations, tooltip system, receipt upload UX | All templates via DOM discovery (`[data-chart]`, `[data-value]`, `#upload-form`) |
| TableauBordExtension | New Python ext + template | Dashboard data aggregation, KPI computation, chart data serialization to JSON | Beancount ledger (read), template (render), JS module (via data attributes on DOM) |
| Chart.js | CDN library loaded into `window.Chart` | Canvas-based chart rendering | ThemeQCExtension.js (caller), `<canvas>` elements (render target) |
| Existing 8 extensions | Python + Jinja2 templates | Domain-specific data and presentation | ThemeQCExtension.js (styling, tooltips, animations), Beancount ledger (data source) |

## Data Flow for Charts

```
Beancount Ledger
    |
    v
TableauBordExtension.after_load_file()
    |  Queries all_entries, computes monthly aggregates
    v
extension.chart_data_json() -> JSON string
    |  Returns Chart.js-compatible {labels:[], datasets:[]}
    v
Jinja2 template embeds JSON in data-chart attribute
    |  <div class="cqc-chart-container" data-chart='{{ chart_json }}'>
    v
Fava inserts HTML into <article> via innerHTML
    |
    v
ThemeQCExtension.js onPageLoad() -> renderCharts()
    |  Discovers [data-chart] containers
    |  Loads Chart.js via CDN (if not already loaded)
    |  Parses JSON from data attribute
    v
Chart.js renders canvas with Quebec-themed colors
```

## Data Flow for KPI Animations

```
Extension.method() returns Decimal values
    |
    v
Jinja2 template renders value in text + data-value attribute
    |  <div class="cqc-kpi-value" data-value="12345.67">12,345.67 $</div>
    v
ThemeQCExtension.js onPageLoad() -> animateKPIs()
    |  Reads data-value, starts requestAnimationFrame loop
    |  Replaces text content with animated counting value
    v
User sees number counting up from 0 to final value (600ms ease-out)
```

## Patterns to Follow

### Pattern 1: Data Attributes as Template-to-JS Bridge

**What:** Templates embed structured data in HTML `data-*` attributes; the JS module discovers and processes them on `onPageLoad()`.

**When:** Any time a template needs to pass data to JS for interactive rendering (charts, animations, dynamic behavior).

**Why:** `<script>` tags in Fava extension templates do not execute during SPA navigation. Data attributes are the only reliable bridge between server-rendered HTML and client-side JS.

**Example:**
```html
<!-- Template -->
<div class="cqc-chart-container" data-chart='{"labels":["Jan","Fev"],"datasets":[{"data":[1000,2000]}]}'>
  <canvas></canvas>
</div>
```
```javascript
// ThemeQCExtension.js onPageLoad()
document.querySelectorAll('[data-chart]').forEach(el => {
  const config = JSON.parse(el.dataset.chart);
  // render chart...
});
```

### Pattern 2: Idempotent onPageLoad Functions

**What:** Every function called from `onPageLoad()` must be safe to call multiple times on the same page and must clean up previous state.

**When:** Always. Fava may call `onPageLoad()` when navigating away and back to the same page, or when the ledger file is modified and Fava re-renders.

**Why:** The ThemeQCExtension.js module persists -- it is not re-created on each navigation. Functions that append DOM elements without cleanup will create duplicates.

**Existing example:**
```javascript
function attachTooltips() {
  // 1. Idempotent cleanup: remove ALL existing tooltips
  document.querySelectorAll("[data-tooltip]").forEach((el) => {
    el.removeAttribute("data-tooltip");
    el.removeAttribute("tabindex");
  });
  // 2. Re-attach fresh tooltips
  // ...
}
```

### Pattern 3: Lazy CDN Loading with Promise Caching

**What:** External libraries loaded via `<script>` injection with a cached Promise to prevent duplicate loads.

**When:** Loading Chart.js or any future CDN dependency.

**Why:** The `init()` function can pre-load the library (non-blocking), and `onPageLoad()` can `await` it before rendering. The Promise ensures only one `<script>` tag is ever created regardless of how many times the function is called.

### Pattern 4: Extension Methods Return Serializable Data

**What:** Python extension methods called from templates should return simple types (dict, list, Decimal, str) that Jinja2 can render directly or serialize to JSON.

**When:** Designing new extension methods, especially for chart data.

**Why:** Templates cannot import Python modules or run complex logic. The extension is the computation layer; the template is the presentation layer. For Chart.js, the extension must pre-serialize data to a JSON string that Jinja2 can embed as an attribute value.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Script Tags in Extension Templates

**What:** Putting `<script>` blocks in Jinja2 templates for non-trivial logic.

**Why bad:** Scripts inserted via innerHTML do not execute during Fava SPA navigation. The code will work on direct URL access (full page load) but silently fail when navigating via sidebar links. This creates inconsistent behavior that is extremely hard to debug.

**Instead:** Use data attributes in templates + logic in ThemeQCExtension.js `onPageLoad()`.

**Exception:** Tiny inline event handlers (like `onclick="toggleAll(true)"` in ApprobationExtension.html) work because they are attribute-based, not script-block-based. The function they call must already exist in the global scope (defined by a global function declaration or exposed by the JS module).

### Anti-Pattern 2: Multiple has_js_module Extensions

**What:** Creating separate JS modules for each extension that needs interactivity (e.g., a DashboardExtension.js alongside ThemeQCExtension.js).

**Why bad:** Fava loads all extension JS modules on every page. Multiple modules competing to modify the DOM creates ordering issues, race conditions, and duplicated CDN loads. The ThemeQCExtension.js is already the "single orchestrator" for all client-side behavior.

**Instead:** Keep all JS in ThemeQCExtension.js. If it grows past ~3,000 lines, split into sub-modules using dynamic `import()` (which works because the module is loaded as an ES module by Fava, not via innerHTML).

### Anti-Pattern 3: Relying on Chart State Across Navigations

**What:** Keeping Chart.js instances alive across SPA page changes and trying to update them in-place.

**Why bad:** Fava destroys and recreates `<article>` content on each navigation. The canvas elements are gone. Chart.js instances pointing to destroyed canvases will leak memory and throw errors.

**Instead:** Destroy charts implicitly (they are garbage collected when the canvas is removed from DOM) and recreate from data attributes when arriving on a chart page. Charts are cheap to create; the data is already computed server-side.

### Anti-Pattern 4: Global CSS Animations Without Scoping

**What:** Applying complex animations to generic selectors like `article *` or `table`.

**Why bad:** Fava's native Svelte components also render within `<article>`. Unscoped animations will affect the Income Statement tree, Balance Sheet, Journal -- native Fava pages that should not have the same visual treatment as CompteQC extensions.

**Instead:** Scope animations to `.cqc-*` prefixed classes only. The page-enter animation on `article` itself is acceptable because it is a simple fade that benefits all page transitions uniformly.

## Existing File Modifications Required

| File | Change | Reason |
|------|--------|--------|
| `ThemeQCExtension.js` | Add `loadChartJs()`, `renderCharts()`, `animateKPIs()`, `animatePageEntry()` functions | Core UI/UX engine additions |
| `ThemeQCExtension.js` | Add chart-specific CSS to THEME_CSS constant | `.cqc-chart-container` sizing, responsive rules, chart card styling |
| `ThemeQCExtension.js` | Update `export default` to call new functions in `onPageLoad()` | Hook new features into Fava lifecycle |
| `ThemeQCExtension.js` | Update `SIDEBAR_GROUPS` to add "Tableau de bord" at top | Dashboard navigation priority |
| `ThemeQCExtension.js` | Add `TOOLTIPS` entries for new dashboard KPIs | Pedagogical tooltips for new elements |
| `RecusExtension.html` | Replace inline `onchange` submit with data attributes for JS-driven upload | Animated upload UX |
| `RecusExtension/__init__.py` | Add JSON response mode to upload endpoint | XHR upload support (return JSON when Accept header requests it) |
| `ApprobationExtension.html` | Rework table row structure for better visual hierarchy | Approval queue polish |
| `PaieQCExtension.html` | Add `data-value` to `.cqc-kpi-value` elements | KPI count-up animation |
| `TaxesQCExtension.html` | Add `data-value` to `.cqc-kpi-value` elements | KPI count-up animation |
| `PretActionnaireExtension.html` | Add `data-value` to `.cqc-kpi-value` elements (if it has them) | KPI count-up animation |
| `EcheancesExtension.html` | Add `data-value` to `.cqc-kpi-value` elements (if it has them) | KPI count-up animation |

## New Files Required

| File | Purpose |
|------|---------|
| `src/compteqc/fava_ext/tableau_bord/__init__.py` | Dashboard extension Python class -- aggregates KPIs, monthly revenue/expense series, pending count |
| `src/compteqc/fava_ext/tableau_bord/templates/TableauBordExtension.html` | Dashboard template with KPI cards, chart containers with `data-chart` JSON attributes |

## Suggested Build Order

The order is dictated by Fava's constraints: JS module changes must be tested across the SPA lifecycle (sidebar navigation, not just direct URL), and each phase should produce visible, testable results.

### Phase 1: Foundation (Chart.js + Page Transitions + Design System)
1. **Chart.js lazy loader** in ThemeQCExtension.js -- `loadChartJs()` with Promise caching and CDN script injection. Test: verify `window.Chart` available after `await loadChartJs()`.
2. **Chart rendering engine** (`renderCharts()`) with Quebec color palette defaults and `getChartThemeOptions()` helper. Test: hardcode a `[data-chart]` div in any existing template, verify chart renders on both direct URL and sidebar navigation.
3. **Page entry animation** (CSS keyframes + JS class toggle in `onPageLoad()`). Test: navigate between pages via sidebar, verify subtle fade-in on each transition.
4. **KPI count-up animation** (`animateKPIs()`). Test: add `data-value` to one KPI in PaieQCExtension.html, verify count-up on navigation.
5. **Design system CSS additions** to THEME_CSS: `.cqc-chart-container`, enhanced table hover states, refined shadow/spacing tokens.

### Phase 2: Dashboard Extension
6. **TableauBordExtension Python class** -- compute revenue YTD, expenses YTD, net income, cash position, pending approval count. Compute monthly series for chart data. Return chart-ready JSON via `chart_data_json()`.
7. **Dashboard template** -- KPI cards (revenue YTD, expenses YTD, net income, pending approvals) with `data-value` for count-up + chart containers with `data-chart` JSON.
8. **Three chart types**: line chart (monthly revenue trend), doughnut (expense category breakdown), bar (monthly cash flow). All use Quebec blue palette.
9. **Sidebar update** -- add "Tableau de bord" to `SIDEBAR_GROUPS` at top position, default open.
10. **Dashboard tooltips** -- add entries to `TOOLTIPS` dict for new KPI labels.

### Phase 3: Existing Extension Polish
11. **Add `data-value` to all KPI templates** across PaieQC, TaxesQC, PretActionnaire, Echeances. All extensions get count-up animations automatically.
12. **Table styling refinement** -- enhanced `.cqc-table tr:hover` with smoother transitions, slight background shift, better row spacing.
13. **Approval queue redesign** -- better visual hierarchy for confidence badges, scannable layout improvements, smoother bulk action flow.
14. **Consistent card and section styling** across all extension templates.

### Phase 4: Receipt Upload Animation
15. **Modify RecusExtension endpoint** (`@extension_endpoint("upload")`) to return JSON when `Accept: application/json` is present, while keeping redirect for non-JS fallback.
16. **Build upload UX in ThemeQCExtension.js** -- `handleReceiptUpload()` function: file preview (image thumbnail or PDF icon), XHR with `upload.onprogress` for progress bar, success/error animation, dynamic table row insertion.
17. **Drag-and-drop visual enhancement** -- animated dropzone border pulse, file type icon display, size/name preview before upload.

### Phase 5: Final Polish and Cross-Browser
18. **Typography scale audit** -- ensure Inter font weights (400/500/600/700) and sizes are consistent across all extensions and native Fava pages.
19. **Shadow and spacing audit** -- verify card elevation, section spacing, KPI row gaps, responsive breakpoints (768px and 480px).
20. **Cross-browser testing** -- verify Chart.js, CSS animations, custom properties, and `requestAnimationFrame` count-up work in Safari, Chrome, Firefox.

### Build Order Rationale

- **Phase 1 first** because every subsequent phase depends on Chart.js loading, the chart renderer, and animation utilities being functional and tested across Fava's SPA lifecycle.
- **Phase 2 before Phase 3** because the dashboard is the new "homepage" and the most visible addition. It also validates that the entire data flow (Python -> JSON -> data attribute -> Chart.js) works end-to-end.
- **Phase 3 before Phase 4** because KPI animations and table polish are lower-risk changes to existing templates (adding a `data-value` attribute is minimal change, high visual impact).
- **Phase 4 last among features** because receipt upload animation requires both Python endpoint changes and complex JS (XHR progress tracking), making it the highest-effort single feature.
- **Phase 5 last** because polish passes should happen after all features are in place.

## Scalability Considerations

| Concern | Now (8 extensions + dashboard) | At 15 extensions | At 30+ extensions |
|---------|-------------------------------|-------------------|---------------------|
| ThemeQCExtension.js size | 1,769 lines, will grow to ~2,500 | ~3,500 lines -- consider splitting with dynamic `import()` | Split into `cqc-theme.js`, `cqc-charts.js`, `cqc-animations.js` |
| Chart.js bundle size | 67KB gzipped from CDN -- cached by browser | Same | Same |
| `onPageLoad()` cost | ~5ms DOM queries | ~10ms with more containers to scan | Profile; add URL-based early-return (skip chart rendering on non-chart pages) |
| Template data size | Small JSON payloads (~2KB for 12 months of chart data) | Moderate | Cap chart datasets to last 24 months; paginate if needed |
| CSS specificity | `.cqc-*` prefix avoids conflicts with Fava/Svelte | Same -- prefix is good insurance | Same |

## Sources

- [Fava Extension API docs](https://beancount.github.io/fava/api/fava.ext.html) -- FavaExtensionBase class, has_js_module, extension_endpoint decorator
- [Fava Extension Help page](https://fava.pythonanywhere.com/example-beancount-file/help/extensions) -- JS module lifecycle: `init()`, `onPageLoad()`, `onExtensionPageLoad()`
- [Fava GitHub Issue #1175](https://github.com/beancount/fava/issues/1175) -- SPA navigation and innerHTML script execution limitation (critical architectural constraint)
- [Chart.js Integration docs](https://www.chartjs.org/docs/latest/getting-started/integration.html) -- UMD build for no-build-step usage
- [Chart.js CDN on jsDelivr](https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js) -- recommended CDN URL for script injection
- Existing codebase: `ThemeQCExtension.js` lines 1757-1769 (module export with `init`/`onPageLoad`), lines 1055-1073 (style and font injection pattern), lines 1596-1654 (idempotent tooltip system)
