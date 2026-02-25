# Phase 6: Fava Dashboard UX — Pedagogical Tooltips, Sidebar Dropdowns, and Beginner-Friendly Navigation - Research

**Researched:** 2026-02-19
**Domain:** Fava extension JavaScript, CSS, DOM manipulation for sidebar UX and tooltip system
**Confidence:** HIGH

## Summary

Phase 6 transforms the Fava dashboard from a developer-oriented tool into a beginner-friendly accounting interface. The work is entirely frontend: reorganizing the sidebar navigation into collapsible grouped sections, adding plain-language French explanations to every report, and implementing a hover tooltip system on all table headers, calculated values, and metrics.

The key technical insight is that Fava's sidebar is rendered by a compiled Svelte component (`AsideContents.svelte`) that is **not directly extensible** from Python or extension templates. Extension reports appear as a flat `<ul class="navigation">` at the bottom of the sidebar. To achieve collapsible grouped sections, we must use the existing `ThemeQCExtension.js` module (which has `has_js_module = True` and runs `onPageLoad` on every navigation) to manipulate the DOM after Fava renders the sidebar. This is the same proven pattern already used for brand injection and CSS theming.

**Primary recommendation:** Extend `ThemeQCExtension.js` with three new DOM-manipulation functions: (1) `reorganizeSidebar()` to group and wrap sidebar links into collapsible `<details>/<summary>` sections, (2) `injectReportHeaders()` to prepend pedagogical explanation blocks to extension report pages, and (3) `attachTooltips()` to add `data-tooltip` attributes and a CSS-only (or minimal-JS) tooltip system to table headers and KPI values. All tooltip/explanation text is defined in a single French-language JSON dictionary embedded in the JS module.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UX-01 | Collapsible sidebar dropdowns grouped by section | DOM manipulation in `onPageLoad` using `<details>/<summary>` elements to wrap Fava's flat `<ul class="navigation">` lists into named groups |
| UX-02 | Plain-language report header explanations in French | Inject `<div class="cqc-report-intro">` blocks at top of `<article>` content on extension pages, keyed by URL path |
| UX-03 | Pedagogical tooltips on table headers, calculated values, metrics | CSS tooltip system using `data-tooltip` attributes on `.cqc-table th`, `.cqc-kpi-value`, and Fava native `th` elements |
| UX-04 | Consistent tooltip style, desktop + tablet | Pure CSS tooltip with `::after` pseudo-element, `position: absolute`, works with hover (desktop) and focus/tap (tablet) |
| UX-05 | Beginner-level jargon-free French text | All text stored in a single `TOOLTIPS_FR` dictionary in JS, easy to review/edit as a batch |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Fava | 1.30.12 | Web interface for Beancount | Already installed, provides extension JS module API |
| ThemeQCExtension.js | existing | Extension JS module with `onPageLoad` hook | Already proven pattern for DOM manipulation in this project |
| HTML `<details>/<summary>` | native | Collapsible sections | No JS framework needed, accessible by default, works on all browsers |
| CSS `::after` tooltips | native | Hover tooltip display | Zero dependencies, works on desktop and tablet (with `:focus-within`) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None | - | - | No additional libraries needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `<details>/<summary>` | Custom JS accordion | More control but more code, accessibility issues, no benefit |
| CSS-only tooltips | Tippy.js / Floating UI | Better positioning edge cases but adds dependency, build toolchain |
| Embedded JS dictionary | Separate JSON file served via endpoint | Cleaner separation but adds HTTP request, extension endpoint boilerplate |

**Installation:**
```bash
# No new dependencies needed - everything is native HTML/CSS/JS
```

## Architecture Patterns

### Recommended Project Structure
```
src/compteqc/fava_ext/theme_qc/
├── __init__.py                    # ThemeQCExtension (has_js_module = True)
├── ThemeQCExtension.js            # Main JS module — EXTEND THIS FILE
└── static/
    └── quebec-logo.png
```

No new files are needed. All Phase 6 work goes into the existing `ThemeQCExtension.js` file (and its embedded CSS).

### Pattern 1: DOM Manipulation in `onPageLoad`
**What:** Use Fava's extension JS lifecycle hook to modify the DOM after each page render.
**When to use:** Every page load — the sidebar needs regrouping on every navigation since Fava uses SPA-style routing.
**Example:**
```javascript
// Source: Verified from Fava source code (frontend/src/extensions.ts, extension-api.d.ts)
// and existing ThemeQCExtension.js in this project

/** @type import("fava").ExtensionModule */
export default {
  init() {
    injectStyle();       // CSS for tooltips, collapsible sidebar, report intros
  },
  onPageLoad() {
    injectStyle();       // Ensure CSS persists across SPA navigations
    reorganizeSidebar(); // Group sidebar links into collapsible sections
    injectReportHeader();// Add pedagogical header to current report page
    attachTooltips();    // Add data-tooltip attributes to table headers/KPIs
  },
};
```

### Pattern 2: Sidebar Regrouping with `<details>/<summary>`
**What:** Wrap Fava's flat `<ul class="navigation">` lists into named `<details>` elements with French section headers.
**When to use:** On every `onPageLoad` call, since Fava re-renders the sidebar on SPA navigation.
**Example:**
```javascript
// The sidebar DOM structure (from AsideContents.svelte compiled output):
// <aside>
//   <ul class="navigation">  <!-- sidebar_links (if any) -->
//   <ul class="navigation">  <!-- Income Statement, Balance Sheet, Trial Balance, Journal, Query -->
//   <ul class="navigation">  <!-- Holdings, Commodities, Documents, Events, Statistics -->
//   <ul class="navigation">  <!-- Editor, Errors, Import, Options, Help -->
//   <ul class="navigation">  <!-- Extension reports (flat list) -->
// </aside>

function reorganizeSidebar() {
  const aside = document.querySelector("aside");
  if (!aside || aside.dataset.cqcGrouped) return; // idempotent guard

  const navLists = aside.querySelectorAll("ul.navigation");
  if (navLists.length < 2) return;

  // Mark as processed to avoid re-running
  aside.dataset.cqcGrouped = "true";

  // Strategy: wrap each <ul> in a <details> with a <summary>
  // Map Fava's built-in sections + extension section to French group names
  const GROUPS = [
    { name: "Rapports financiers", icon: "📊", open: true },   // ul with Income Statement, Balance Sheet, etc.
    { name: "Donnees et documents", icon: "📁", open: false },  // ul with Holdings, Commodities, etc.
    { name: "Outils", icon: "🔧", open: false },                // ul with Editor, Import, Options, etc.
    { name: "Extensions Quebec", icon: "⚜", open: true },       // ul with extension reports
  ];

  navLists.forEach((ul, i) => {
    if (i >= GROUPS.length) return;
    const group = GROUPS[i];
    const details = document.createElement("details");
    details.className = "cqc-sidebar-group";
    if (group.open) details.open = true;

    const summary = document.createElement("summary");
    summary.className = "cqc-sidebar-group-title";
    summary.textContent = `${group.icon} ${group.name}`;

    details.appendChild(summary);
    ul.parentNode.insertBefore(details, ul);
    details.appendChild(ul);
  });
}
```

### Pattern 3: Extension Report Sub-grouping
**What:** Within the extensions `<ul>`, further subdivide the 8 extension reports into logical sub-groups.
**When to use:** After the initial sidebar grouping, split the flat extension list.
**Example:**
```javascript
// Extension reports appear as:
//   File d'approbation, Paie Quebec, TPS/TVQ, DPA/CCA,
//   Pret actionnaire, Export CPA, Echeances, Recus
//
// Desired sub-groups within "Extensions Quebec":
//   Taxes Quebec: TPS/TVQ, DPA/CCA
//   Paie: Paie Quebec
//   Outils: File d'approbation, Export CPA, Echeances, Recus
//   Surveillance: Pret actionnaire

const EXT_GROUPS = {
  "Rapports financiers": ["TPS/TVQ", "DPA/CCA", "Paie Quebec", "Pret actionnaire"],
  "Validation et import": ["File d'approbation", "Recus"],
  "Outils comptables": ["Export CPA", "Echeances"],
};
```

### Pattern 4: CSS-Only Tooltips with `data-tooltip`
**What:** Attach `data-tooltip` attributes to elements and use CSS `::after` to display them.
**When to use:** For all table headers, KPI values, and calculated totals.
**Example:**
```css
/* Tooltip container */
[data-tooltip] {
  position: relative;
  cursor: help;
}

/* Tooltip arrow + box */
[data-tooltip]::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--qc-surface-sidebar);
  color: #fff;
  padding: 10px 14px;
  border-radius: var(--qc-radius-sm);
  font-size: 0.82em;
  font-weight: 400;
  line-height: 1.5;
  white-space: normal;
  width: max-content;
  max-width: 320px;
  box-shadow: var(--qc-shadow-lg);
  opacity: 0;
  pointer-events: none;
  transition: opacity 200ms ease;
  z-index: 1000;
}

[data-tooltip]:hover::after,
[data-tooltip]:focus-within::after {
  opacity: 1;
}

/* Underline hint that tooltip exists */
[data-tooltip] {
  text-decoration: underline dotted var(--qc-muted);
  text-underline-offset: 3px;
}
```

### Pattern 5: Report Header Injection
**What:** Detect which report page is loaded and prepend a pedagogical explanation block.
**When to use:** On every `onPageLoad`, check the URL path and inject the matching intro.
**Example:**
```javascript
const REPORT_INTROS = {
  "extension/PaieQCExtension": {
    titre: "Tableau de bord de la paie",
    explication: "Ce rapport montre le cumul annuel de votre salaire et de toutes les retenues " +
      "(cotisations sociales et impots). Il vous permet de verifier que les maximums annuels " +
      "sont respectes et de connaitre votre salaire net reel.",
    qui: "Vous (pour suivre votre paie) et votre comptable (pour valider les retenues).",
    fonction: "PaieQCExtension.payroll_summary() dans compteqc.fava_ext.paie_qc",
  },
  // ... one entry per report
};

function injectReportHeader() {
  const path = window.location.pathname;
  const article = document.querySelector("article");
  if (!article) return;

  // Remove previous injection
  article.querySelector(".cqc-report-intro")?.remove();

  for (const [key, info] of Object.entries(REPORT_INTROS)) {
    if (path.includes(key)) {
      const div = document.createElement("div");
      div.className = "cqc-report-intro cqc-card";
      div.innerHTML = `
        <h3>${info.titre}</h3>
        <p>${info.explication}</p>
        <p><strong>Qui utilise ce rapport :</strong> ${info.qui}</p>
        <p class="cqc-source-tag">Source : ${info.fonction}</p>
      `;
      article.prepend(div);
      break;
    }
  }
}
```

### Anti-Patterns to Avoid
- **Modifying Fava's Svelte source or compiled JS:** Never patch `app.js` or Svelte components. Use only the official extension JS module API (`init`, `onPageLoad`, `onExtensionPageLoad`).
- **Creating new extension classes for UI-only changes:** The `ThemeQCExtension` already has `has_js_module = True` and runs on every page. Adding another extension class just for tooltips adds unnecessary complexity.
- **Using a JS tooltip library (Tippy.js, etc.):** Adds a dependency and requires a build toolchain, which contradicts the project constraint of "no JS build toolchain."
- **Putting tooltip text in Python/Jinja templates:** The tooltip text needs to be attached after Fava's Svelte rendering. Jinja templates only control the `<article>` content of extension pages, not native Fava reports or the sidebar.
- **Using `title` attribute for tooltips:** No styling control, inconsistent across browsers, no multiline support, ugly default appearance.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Collapsible sections | Custom accordion with JS state management | HTML `<details>/<summary>` | Native, accessible, zero JS needed for toggle behavior |
| Tooltip positioning | Custom positioning logic for edge detection | CSS `::after` with `position: absolute` | Good enough for this use case; edge cases (viewport clipping) are minor for a known layout |
| SPA navigation detection | Custom MutationObserver or URL polling | Fava's `onPageLoad` hook | Fava already calls this on every SPA navigation — it's the official API |
| French localization framework | i18n library, .po files | Embedded JS dictionary object | Only one language (French), only ~50-80 strings, no need for full i18n |

**Key insight:** The entire Phase 6 can be implemented by extending a single existing JS file with ~400-500 lines of additional code (dictionaries + DOM functions) and ~100 lines of additional CSS. No new files, no new dependencies, no build toolchain.

## Common Pitfalls

### Pitfall 1: Sidebar DOM Re-renders on SPA Navigation
**What goes wrong:** Fava uses Svelte with SPA-style routing. When navigating between reports, the sidebar may or may not be fully re-rendered. If you only run sidebar reorganization once in `init()`, it may be lost on navigation.
**Why it happens:** Fava's `Router` class fetches new content via `?partial=true` and updates the `<article>` content, but the sidebar (`<aside>`) is generally stable. However, certain navigations (e.g., changing the beancount file) will re-render everything.
**How to avoid:** Always run `reorganizeSidebar()` in `onPageLoad()` with an idempotent guard (`aside.dataset.cqcGrouped`). Check if the sidebar has already been processed before transforming it.
**Warning signs:** Sidebar reverts to flat list after navigation; duplicate group headers appear.

### Pitfall 2: Tooltip Text Overflows or Gets Clipped
**What goes wrong:** Long French tooltip text extends beyond the viewport or gets clipped by `overflow: hidden` on parent containers.
**Why it happens:** CSS `::after` tooltips are positioned relative to their parent. Fava's `<table>` or card containers may have `overflow: hidden`.
**How to avoid:** Use `position: fixed` for tooltips instead of `position: absolute` if clipping occurs, or add `overflow: visible` to tooltip parent containers. Keep tooltip text concise (2-3 sentences max). Test with the longest tooltip text.
**Warning signs:** Tooltips cut off at table edges; tooltips appear behind other elements.

### Pitfall 3: Extension Report Order Depends on Beancount Config
**What goes wrong:** The sidebar groups extensions by their DOM order, but this order depends on the sequence of `fava-extension` directives in `main.beancount`.
**Why it happens:** Fava renders extension sidebar links in registration order.
**How to avoid:** Match extensions to groups by their `report_title` text content (e.g., "Paie Quebec", "TPS/TVQ"), not by DOM position. Use `textContent` matching in the sidebar regrouping logic.
**Warning signs:** Extension reports appear in the wrong group after reordering `fava-extension` lines.

### Pitfall 4: Tooltip Attachment Fails on Native Fava Pages
**What goes wrong:** Tooltips work on extension pages (rendered by Jinja templates with `.cqc-table` class) but not on native Fava pages (Income Statement, Balance Sheet, Trial Balance) which use Svelte-rendered tables.
**Why it happens:** Native Fava tables don't have `.cqc-table` class; they use different DOM structure (`.tree-table`, Svelte component containers).
**How to avoid:** Use broader selectors for native pages: `article table th`, `article .tree-table th`. Identify native Fava pages by URL path (`income_statement`, `balance_sheet`, `trial_balance`) and use page-specific tooltip dictionaries.
**Warning signs:** Tooltips only appear on extension pages, not on Fava's built-in reports.

### Pitfall 5: Tablet Touch Events Don't Trigger `:hover`
**What goes wrong:** CSS `:hover` tooltips don't show on tablets because there's no mouse hover.
**Why it happens:** Touch devices don't fire hover events (or fire them inconsistently).
**How to avoid:** Add `:focus-within` as an alternative trigger. For `<th>` elements, add `tabindex="0"` so they're focusable. Alternatively, use a small JS handler that toggles a `.tooltip-active` class on tap.
**Warning signs:** Tooltips work on desktop but not on iPad/tablet.

## Code Examples

### Example 1: Complete `onPageLoad` Flow
```javascript
// Source: Pattern derived from existing ThemeQCExtension.js + Fava extension-api.d.ts

export default {
  init() {
    injectStyle();
  },
  onPageLoad() {
    injectStyle();
    injectBrand();
    // Phase 6 additions:
    reorganizeSidebar();
    injectReportHeader();
    attachTooltips();
  },
};
```

### Example 2: Tooltip Dictionary Structure
```javascript
// Each tooltip entry includes: what it is, why it matters, and source function
const TOOLTIPS = {
  // -- Paie Quebec --
  "Salaire brut YTD": {
    text: "Total du salaire avant retenues depuis le debut de l'annee. " +
          "C'est le montant que la societe vous verse avant impots et cotisations.",
    source: "PaieQCExtension.totaux().salaire_brut_ytd",
  },
  "Retenues employe": {
    text: "Total de toutes les deductions prelevees sur votre salaire : " +
          "impots federal et provincial, RRQ, RQAP, et assurance-emploi. " +
          "Ce montant est deduit de votre paie nette.",
    source: "PaieQCExtension.totaux().total_retenues_employe",
  },
  "Cotisations employeur": {
    text: "Montant additionnel paye par votre societe en plus de votre salaire : " +
          "part employeur du RRQ, RQAP, AE, FSS, CNESST et normes du travail. " +
          "Ce montant n'apparait pas sur votre cheque de paie mais est une depense pour l'entreprise.",
    source: "PaieQCExtension.totaux().total_cotisations_employeur",
  },
  // -- TPS/TVQ --
  "TPS percue": {
    text: "Taxe sur les produits et services (5%) que vous avez facturee a vos clients. " +
          "Vous la collectez pour le gouvernement federal.",
    source: "TaxesQCExtension.tax_summary().tps_percue",
  },
  // ... etc for all headers and values
};
```

### Example 3: Attaching Tooltips to Table Headers
```javascript
function attachTooltips() {
  // Remove previous tooltips to avoid duplicates
  document.querySelectorAll("[data-tooltip]").forEach(el => {
    el.removeAttribute("data-tooltip");
    el.removeAttribute("tabindex");
  });

  // Extension page tables (.cqc-table th)
  document.querySelectorAll(".cqc-table th, .cqc-kpi-label, .cqc-kpi-value").forEach(el => {
    const text = el.textContent.trim();
    const tip = TOOLTIPS[text];
    if (tip) {
      el.setAttribute("data-tooltip", `${tip.text}\n\n📐 Source: ${tip.source}`);
      el.setAttribute("tabindex", "0"); // For tablet accessibility
    }
  });

  // Native Fava tables (income_statement, balance_sheet, trial_balance)
  document.querySelectorAll("article table th").forEach(el => {
    const text = el.textContent.trim();
    const tip = TOOLTIPS[text];
    if (tip) {
      el.setAttribute("data-tooltip", `${tip.text}\n\n📐 Source: ${tip.source}`);
      el.setAttribute("tabindex", "0");
    }
  });
}
```

### Example 4: Collapsible Sidebar CSS
```css
/* Sidebar groups */
.cqc-sidebar-group {
  margin: 2px 0;
}

.cqc-sidebar-group-title {
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.72em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 8px 12px 4px;
  cursor: pointer;
  list-style: none; /* Remove default triangle */
  user-select: none;
  transition: color var(--qc-transition);
}

.cqc-sidebar-group-title:hover {
  color: rgba(255, 255, 255, 0.8);
}

/* Custom disclosure indicator */
.cqc-sidebar-group-title::before {
  content: "▸ ";
  display: inline-block;
  transition: transform var(--qc-transition);
}

.cqc-sidebar-group[open] > .cqc-sidebar-group-title::before {
  transform: rotate(90deg);
}

/* Remove default <details> marker in webkit */
.cqc-sidebar-group-title::-webkit-details-marker {
  display: none;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Modify Fava source code | Use extension JS module API (`init`, `onPageLoad`) | Fava 1.27+ | Extensions are upgrade-safe; no Fava patching needed |
| JS tooltip libraries (Tippy.js) | CSS-only tooltips with `data-tooltip` + `::after` | 2024+ CSS capabilities | No dependencies, smaller footprint, simpler maintenance |
| Custom JS accordion | HTML `<details>/<summary>` | Widely supported since 2020 | Native accessibility, zero JS for toggle logic |
| Server-side sidebar customization | Client-side DOM manipulation | Fava's Svelte architecture | Sidebar is Svelte-rendered; server templates only control `<article>` content |

**Deprecated/outdated:**
- Fava's extension system is marked as "unstable" in official docs and may change in future versions. However, the current JS module API (`init`/`onPageLoad`/`onExtensionPageLoad`) has been stable since at least Fava 1.27 and is still present in 1.30.12.

## Fava Sidebar Internal Architecture (Critical Finding)

The sidebar is rendered by `AsideContents.svelte` (compiled into `app.js`). Key structure:

```
<aside>
  [sidebar_links ul — if any custom links defined]
  <ul class="navigation">  ← Income Statement, Balance Sheet, Trial Balance, Journal, Query
  <ul class="navigation">  ← Holdings, Commodities, Documents, Events, Statistics
  <ul class="navigation">  ← Editor, Errors, Import, Options, Help
  <ul class="navigation">  ← Extension reports (flat: all 8 extensions in registration order)
</aside>
```

Extension reports are rendered in a single flat `<ul>` with one `<SidebarLink>` per extension that has `report_title != null`. The `ThemeQCExtension` has `report_title = None` so it does NOT appear in the sidebar (correct — it's a theme-only extension).

The sidebar `<aside>` is rendered once on initial load and generally persists across SPA navigations (only `<article>` content changes via `?partial=true` fetch). This means sidebar DOM manipulation in `init()` may suffice, but `onPageLoad()` with an idempotent guard is safer.

## Fava Extension JS Module API (Verified)

From `extension-api.d.ts` (verified from Fava GitHub source):

```typescript
export interface ExtensionModule {
  init?: (c: ExtensionContext) => void | Promise<void>;
  onPageLoad?: (c: ExtensionContext) => void;
  onExtensionPageLoad?: (c: ExtensionContext) => void;
}

export interface ExtensionContext {
  api: ExtensionApi;  // HTTP helpers for extension endpoints
}
```

- `init()`: Called once when the extension JS module is first loaded.
- `onPageLoad()`: Called on every page navigation (SPA-style).
- `onExtensionPageLoad()`: Called only when navigating to this extension's report page.
- The `ExtensionContext.api` provides `get/put/post/delete` helpers for calling extension endpoints.

The existing `ThemeQCExtension.js` already uses `init()` and `onPageLoad()` — but currently only calls `injectStyle()` in both. The `injectBrand()` function exists but is NOT called in the exported module (it is called standalone). This should be cleaned up in Phase 6.

## Current Extension Reports Inventory

| Extension Class | `report_title` | Sidebar Label | Proposed Group |
|----------------|----------------|---------------|----------------|
| ApprobationExtension | "File d'approbation" | File d'approbation | Validation et import |
| PaieQCExtension | "Paie Quebec" | Paie Quebec | Rapports financiers |
| TaxesQCExtension | "TPS/TVQ" | TPS/TVQ | Rapports financiers |
| DpaQCExtension | (inferred "DPA/CCA") | DPA/CCA | Rapports financiers |
| PretActionnaireExtension | (inferred "Pret actionnaire") | Pret actionnaire | Rapports financiers |
| ExportCPAExtension | "Export CPA" | Export CPA | Outils comptables |
| EcheancesExtension | "Echeances" | Echeances | Outils comptables |
| RecusExtension | "Recus" | Recus | Validation et import |
| ThemeQCExtension | None (no report) | (hidden) | N/A |

## Open Questions

1. **Should native Fava reports (Income Statement, Balance Sheet, Trial Balance) also get pedagogical headers?**
   - What we know: These are Svelte-rendered pages, not Jinja templates. We CAN inject DOM elements via `onPageLoad`.
   - What's unclear: Whether the user wants French explanations for standard accounting reports or only for the custom Quebec extensions.
   - Recommendation: Include them. The phase goal says "every report tab" and the success criteria mention trial balance, P&L, and balance sheet explicitly. Use URL path matching to detect these pages.

2. **How to handle the "sidebar_links" section (first `<ul>` if present)?**
   - What we know: Fava supports custom sidebar links via `custom "fava-sidebar-link"` directives. The project currently does not use them.
   - What's unclear: Whether to include this empty section in the grouping logic.
   - Recommendation: Skip the first `<ul>` if it corresponds to `sidebar_links` (check if it exists and is empty). Use content-based detection (look for known link texts like "Income Statement") rather than positional indexing.

3. **Tooltip text volume: how much explanation per tooltip?**
   - What we know: Success criteria say "(a) what this number represents, (b) high-level explanation of the calculation, (c) the Python function/module that produces it."
   - What's unclear: How many unique tooltip strings are needed (estimate: 60-80 across all reports).
   - Recommendation: Start with the most data-heavy reports (Paie, TPS/TVQ, DPA, Pret actionnaire) and add tooltips for native Fava reports in a second pass. Keep each tooltip to 2-3 sentences + source function reference.

## Sources

### Primary (HIGH confidence)
- Fava 1.30.12 installed source code (`/Users/philippebeliveau/Desktop/Notebook/comptabilite/.venv/lib/python3.12/site-packages/fava/`) — verified sidebar Svelte structure, extension loading, JS module API
- Fava GitHub `frontend/src/extension-api.d.ts` — verified ExtensionModule, ExtensionContext, ExtensionApi interfaces
- Fava GitHub `frontend/src/extensions.ts` — verified extension loading lifecycle (init, onPageLoad, handleExtensionPageLoad)
- Fava GitHub `frontend/src/sidebar/AsideContents.svelte` — verified sidebar DOM structure (4 `<ul class="navigation">` groups + extension list)
- Existing `ThemeQCExtension.js` in this project — verified working pattern for `init()`/`onPageLoad()` DOM manipulation

### Secondary (MEDIUM confidence)
- [Fava Extensions Help](https://fava.pythonanywhere.com/example-beancount-file/help/extensions) — confirmed extension JS module lifecycle and instability warning
- [Fava API Documentation](https://beancount.github.io/fava/api/fava.ext.html) — confirmed FavaExtensionBase, report_title, has_js_module

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, all native HTML/CSS/JS verified against Fava source
- Architecture: HIGH — pattern proven by existing ThemeQCExtension.js in this project
- Pitfalls: HIGH — derived from direct source code analysis of Fava's Svelte sidebar rendering
- Tooltip text content: MEDIUM — the dictionary structure is clear but the ~60-80 French tooltip strings need to be drafted during implementation

**Research date:** 2026-02-19
**Valid until:** 2026-04-19 (Fava's extension API is marked unstable but has been stable for 1+ year)
