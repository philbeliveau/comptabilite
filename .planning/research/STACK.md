# Technology Stack: v1.1 Production UI/UX Polish

**Project:** CompteQC
**Researched:** 2026-02-25
**Scope:** New libraries/techniques for UI polish within Fava's extension architecture (no build step)

## Existing Stack (DO NOT CHANGE)

| Technology | Role | Notes |
|------------|------|-------|
| Python 3.12 | Backend | Fava extensions are Python classes |
| Beancount v3 + Fava | Ledger + Web UI | All UI lives inside Fava |
| ThemeQCExtension.js | 1,769-line CSS-in-JS | Injects CSS via `<style>`, manages branding, tooltips, sidebar |
| `has_js_module = True` | Fava JS module API | ES module exports: `init()`, `onPageLoad()`, `onExtensionPageLoad()` |
| Inter font family | Typography | Already loaded, supports `font-variant-numeric: tabular-nums` |
| CSS custom properties | Design tokens | `--qc-blue`, `--qc-shadow-*`, `--qc-radius-*`, `--qc-transition` |
| 8 Fava extensions | HTML templates | Jinja2 server-rendered, `.cqc-table` / `.cqc-card` / `.cqc-badge` classes |

## How Fava Extension JS Works (Critical Context)

Fava loads extension JS as ES modules when `has_js_module = True`. The file must match the class name (e.g., `ThemeQCExtension.js` for class `ThemeQCExtension`). The module exports:

```javascript
export default {
  init() { /* called once on first load */ },
  onPageLoad() { /* called on every navigation (Fava uses AJAX page loads) */ },
  onExtensionPageLoad() { /* called when THIS extension's page loads */ },
};
```

**Key constraint:** Fava replaces `article` content via `innerHTML` on navigation. Script tags in HTML templates do NOT execute. All JS must go through the module system or be dynamically injected.

**Key constraint:** Fava only auto-serves the `ClassName.js` file from the extension directory. It does NOT serve arbitrary files from subdirectories. To serve vendored libraries, you must either: (a) inject them via dynamic `<script>` creation pointing to an external URL, (b) add a Flask route to serve vendor files, or (c) inline the library source into the module.

---

## Recommended New Stack Additions

### 1. Chart.js 4.4.8 -- Data Visualization

| Property | Value |
|----------|-------|
| **Version** | 4.4.8 (pin exact; 4.5.1 is latest but 4.4.x is battle-tested) |
| **Format** | UMD build (`chart.umd.min.js`) |
| **Size** | ~204 KB uncompressed, ~70 KB gzipped |
| **License** | MIT |
| **CDN URL** | `https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js` |

**Why Chart.js:** Lightweight canvas-based charting that covers the three chart types needed (line for revenue trend, doughnut for expense breakdown, bar for cash flow). Already identified as pending decision in PROJECT.md. UMD build exposes `window.Chart` -- no bundler, no import maps, works with dynamic script injection.

**Why NOT ECharts:** fava-dashboards uses ECharts but it is ~1 MB. Overkill for 3 fixed chart types. Chart.js is 5x smaller.

**Why NOT D3.js:** Too low-level. Would require building bar/line/doughnut abstractions from scratch. Chart.js provides these as primitives.

**Loading strategy -- Dynamic script injection from extension JS module:**

```javascript
function loadChartJs() {
  return new Promise((resolve, reject) => {
    if (window.Chart) { resolve(window.Chart); return; }
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js';
    script.onload = () => resolve(window.Chart);
    script.onerror = reject;
    document.head.appendChild(script);
  });
}
```

**IMPORTANT -- CDN vs Vendoring decision:**

The project constraint says "all financial data stays local." However, loading a charting library from a CDN does NOT transmit financial data -- it only downloads a JS file. CDN loading is acceptable here because:
1. The library is public open-source code, not user data
2. It loads once and is browser-cached indefinitely
3. The self-hosted constraint applies to financial data, not to static asset delivery

If strict air-gap operation is needed, vendor the file by adding a Flask route:

```python
# In DashboardExtension.__init__.py
from pathlib import Path
from flask import send_from_directory

class DashboardExtension(FavaExtensionBase):
    has_js_module = True

    def _init_app(self, app):
        vendor_dir = Path(__file__).parent / 'vendor'
        @app.route('/compteqc/vendor/<path:filename>')
        def compteqc_vendor(filename):
            return send_from_directory(str(vendor_dir), filename)
```

**Recommendation:** Start with CDN for development speed. Switch to vendored Flask route if offline operation becomes a requirement.

**Chart.js configuration pattern for CompteQC:**

```javascript
const revenueChart = new Chart(ctx, {
  type: 'line',
  data: { /* from Fava extension template */ },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
    },
    scales: {
      y: {
        ticks: {
          callback: (v) => '$' + v.toLocaleString('fr-CA'),
        },
      },
    },
    elements: {
      line: { tension: 0.3, borderColor: '#003DA5', borderWidth: 2 },
      point: { radius: 0, hoverRadius: 6 },
    },
  },
});
```

**Confidence:** HIGH for Chart.js UMD via script injection. MEDIUM for Fava Flask route vendoring (untested pattern, needs validation).

---

### 2. CountUp.js 2.9.0 -- KPI Number Animation

| Property | Value |
|----------|-------|
| **Version** | 2.9.0 |
| **Format** | UMD build (`countUp.umd.js`) |
| **Size** | ~8 KB |
| **License** | MIT |
| **CDN URL** | `https://cdn.jsdelivr.net/npm/countup.js@2.9.0/dist/countUp.umd.js` |

**Why CountUp.js:** Purpose-built for animated number displays. Handles currency formatting (dollar sign, thousand separators, decimals), configurable duration, easing curves. 8 KB is trivial.

**Why NOT pure CSS `@property` counter:** CSS counters display integers only. KPI cards need `$230,000` with dollar signs, thousand separators, and decimal formatting. CSS cannot do this. The `@property` trick also has incomplete browser support.

**Why NOT custom JS:** CountUp.js is 8 KB, handles edge cases (rapid re-render, Intersection Observer trigger, easing), and has been stable for years. Writing equivalent code from scratch is not worth the time.

**At 8 KB, can be inlined directly into the extension JS module** -- no separate script tag needed:

```javascript
// Option A: Inline (recommended for 8 KB)
// Paste countUp.umd.js contents into a function wrapper in the extension module

// Option B: Dynamic script load (same pattern as Chart.js)
function loadCountUp() {
  return new Promise((resolve, reject) => {
    if (window.countUp) { resolve(window.countUp); return; }
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/countup.js@2.9.0/dist/countUp.umd.js';
    script.onload = () => resolve(window.countUp);
    script.onerror = reject;
    document.head.appendChild(script);
  });
}
```

**Usage pattern:**

```javascript
const counter = new countUp.CountUp('revenue-value', 230000, {
  prefix: '$ ',
  separator: ' ',       // French Canadian: space as thousand separator
  decimal: ',',          // French Canadian: comma as decimal
  decimalPlaces: 0,
  duration: 1.5,
  useGrouping: true,
});
if (!counter.error) counter.start();
```

**Confidence:** HIGH -- tiny library, UMD, no dependencies, well-tested.

---

### 3. CSS Animations -- NO External Library

| Property | Value |
|----------|-------|
| **Approach** | Pure CSS `@keyframes` + existing `--qc-transition` custom properties |
| **Additional size** | 0 KB |

**Why NO animation library:** The existing ThemeQCExtension.js already defines transition timings (`--qc-transition: 180ms cubic-bezier(0.4, 0, 0.2, 1)` and `--qc-transition-slow: 300ms`). All needed animations are simple transforms and opacity changes. Adding Animate.css (80 KB) or GSAP (120 KB) for 5 transition effects is waste.

**Animations to implement with pure CSS:**

```css
/* === Card and content entrance === */
@keyframes cqc-fadeSlideUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* === Page transition (article content swap) === */
@keyframes cqc-fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

/* === KPI card staggered entrance === */
.cqc-kpi-card:nth-child(1) { animation: cqc-fadeSlideUp 400ms ease-out 0ms both; }
.cqc-kpi-card:nth-child(2) { animation: cqc-fadeSlideUp 400ms ease-out 80ms both; }
.cqc-kpi-card:nth-child(3) { animation: cqc-fadeSlideUp 400ms ease-out 160ms both; }
.cqc-kpi-card:nth-child(4) { animation: cqc-fadeSlideUp 400ms ease-out 240ms both; }

/* === Table row hover === */
.cqc-table tbody tr {
  transition: background-color var(--qc-transition);
}
.cqc-table tbody tr:hover {
  background-color: var(--qc-blue-lighter);
}

/* === Progress bar fill === */
.cqc-progress-fill {
  transition: width 600ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* === Badge pulse on new items === */
@keyframes cqc-badgePulse {
  0%, 100% { transform: scale(1); }
  50%      { transform: scale(1.05); }
}
```

**Page transition technique for Fava's AJAX navigation:**

Fava replaces `article` content on navigation. Inject the fade-in in `onPageLoad()`:

```javascript
onPageLoad() {
  const article = document.querySelector('article');
  if (article) {
    article.style.animation = 'none';
    // Force reflow
    article.offsetHeight;
    article.style.animation = 'cqc-fadeIn 200ms ease-out';
  }
}
```

**Confidence:** HIGH -- standard CSS, no dependencies, already partially implemented.

---

### 4. Modern Table Styling -- CSS Only

| Property | Value |
|----------|-------|
| **Approach** | Extend existing `.cqc-table` styles |
| **Additional size** | 0 KB |
| **Font for numbers** | Inter with `font-variant-numeric: tabular-nums` (already loaded) |

**Why NO table library:** Tables are server-rendered Jinja2 HTML. Adding AG Grid, TanStack Table, or DataTables would require restructuring all 8 extension templates. The tables are simple -- no virtual scrolling, no column reorder, no inline editing. Fintech-quality appearance is achievable with CSS alone.

**Key fintech table patterns:**

```css
.cqc-table {
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid var(--qc-border);
  border-radius: var(--qc-radius-sm);
  overflow: hidden;
  width: 100%;
}

/* Uppercase, small, muted headers (Mercury/Stripe style) */
.cqc-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--qc-blue-lighter);
  font-weight: 600;
  font-size: 0.6875rem;  /* 11px */
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--qc-text-secondary);
  padding: 10px 16px;
  border-bottom: 2px solid var(--qc-border);
  white-space: nowrap;
}

/* Compact, well-spaced rows */
.cqc-table tbody td {
  padding: 12px 16px;
  font-size: 0.875rem;
  border-bottom: 1px solid var(--qc-border-light);
  color: var(--qc-text);
}

/* Last row: no bottom border (container border handles it) */
.cqc-table tbody tr:last-child td {
  border-bottom: none;
}

/* Tabular numbers for money columns */
.cqc-table .montant {
  font-variant-numeric: tabular-nums;
  text-align: right;
  font-weight: 500;
}

/* Negative amounts in red */
.cqc-table .montant-negatif {
  color: var(--qc-error);
}

/* Zebra striping (subtle) */
.cqc-table tbody tr:nth-child(even) {
  background-color: rgba(0, 61, 165, 0.015);
}
```

**Confidence:** HIGH -- pure CSS, no dependencies.

---

## What NOT to Add

| Technology | Why Not |
|------------|---------|
| **React / Vue / Svelte / Angular** | Requires build step. Fava uses Svelte internally but extensions cannot access it. Would need a complete frontend rewrite. |
| **Tailwind CSS** | Requires PostCSS build step. The existing CSS custom properties system provides equivalent capability for a single-developer project. |
| **Animate.css** | 80 KB for 5 animations that take 20 lines of CSS to write. |
| **GSAP** | 120 KB, commercial license concerns, overkill for fade/slide transitions. |
| **Motion One** | Requires npm/build step for full functionality. |
| **AG Grid / TanStack Table / DataTables** | Would require restructuring all 8 Jinja2 templates. Tables are simple enough for CSS-only styling. |
| **ECharts** | ~1 MB. fava-dashboards uses it for user-defined arbitrary charts. CompteQC has 3 fixed chart types -- Chart.js at 204 KB is sufficient. |
| **Bootstrap / Material UI** | Conflicts with existing design system. Already have a comprehensive CSS variable palette. |
| **Sass / Less / PostCSS** | Requires build step. CSS custom properties handle theming natively. |
| **Import maps** | Would require modifying Fava's HTML `<head>`, which extensions cannot do. |
| **Chart.js ESM from CDN** | Known issue: bare specifier `@kurkle/color` cannot be resolved without import maps. UMD build avoids this entirely. |

---

## Summary: Total New Dependencies

| Library | Version | Size | Format | Loading Method | Purpose |
|---------|---------|------|--------|----------------|---------|
| Chart.js | 4.4.8 | 204 KB | UMD | Dynamic `<script>` (CDN or vendored) | Dashboard charts |
| CountUp.js | 2.9.0 | 8 KB | UMD | Inline in module or dynamic `<script>` | KPI count-up animation |

**Total additional JS payload:** ~212 KB (loaded on demand, browser-cached)
**Total additional CSS:** 0 KB (all animations are pure CSS added to ThemeQCExtension.js)
**Build step required:** None
**npm required:** No

Everything else (animations, table styling, page transitions, hover states, micro-interactions) is pure CSS injected through the existing ThemeQCExtension.js pattern or added to new extension JS modules.

---

## Installation

```bash
# No npm install. No package.json. No build step.

# For vendored approach (optional, only if offline operation needed):
mkdir -p src/compteqc/fava_ext/dashboard/vendor

curl -o src/compteqc/fava_ext/dashboard/vendor/chart.umd.min.js \
  "https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"

curl -o src/compteqc/fava_ext/dashboard/vendor/countUp.umd.js \
  "https://cdn.jsdelivr.net/npm/countup.js@2.9.0/dist/countUp.umd.js"
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Charts | Chart.js 4.4.8 UMD | ECharts | 5x larger, overkill for 3 chart types |
| Charts | Chart.js 4.4.8 UMD | D3.js | Too low-level, no chart primitives |
| Charts | Chart.js 4.4.8 UMD | Chart.js ESM | Bare specifier issue from CDN; requires import maps |
| KPI animation | CountUp.js 2.9.0 | CSS `@property` counter | Cannot format currency (no $, no separators, integers only) |
| KPI animation | CountUp.js 2.9.0 | Custom JS | 8 KB library handles edge cases; not worth reimplementing |
| CSS animation | Pure CSS `@keyframes` | Animate.css | 80 KB overhead for 5 transitions |
| CSS animation | Pure CSS `@keyframes` | GSAP | 120 KB, commercial license, overkill |
| Table styling | Pure CSS | DataTables | Requires restructuring Jinja2 templates |
| Table styling | Pure CSS | AG Grid | Massive JS library for simple read-only tables |

---

## Sources

- [Chart.js Installation Docs](https://www.chartjs.org/docs/latest/getting-started/installation.html) -- CDN options, UMD vs ESM formats
- [Chart.js jsDelivr CDN file listing](https://cdn.jsdelivr.net/npm/chart.js@latest/dist/) -- Confirms 4.5.1 latest, UMD at 204 KB
- [Chart.js ESM CDN Issue #11592](https://github.com/chartjs/Chart.js/issues/11592) -- Documents bare specifier problem with ESM from CDN
- [Chart.js Integration Guide](https://www.chartjs.org/docs/latest/getting-started/integration.html) -- Module format guidance
- [Fava Extension Script Issue #1175](https://github.com/beancount/fava/issues/1175) -- innerHTML does not execute scripts; JS module pattern is the solution
- [Fava Extension API Help](https://fava.pythonanywhere.com/example-beancount-file/help/extensions) -- `has_js_module`, `onPageLoad()`, `onExtensionPageLoad()` API
- [CountUp.js GitHub](https://github.com/inorganik/countUp.js) -- v2.9.0, UMD build, MIT license, 8 KB
- [CSS @property Counter Animation (CSS-Tricks)](https://css-tricks.com/animating-number-counters/) -- Pure CSS approach limitations
- [fava-dashboards (GitHub)](https://github.com/andreasgerstmayr/fava-dashboards) -- Uses ECharts (~1 MB), confirms external lib loading works in Fava

---
*Stack research for: v1.1 Production UI/UX Polish*
*Researched: 2026-02-25*
