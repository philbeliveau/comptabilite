# Phase 10: Cross-Cutting Polish and Validation - Research

**Researched:** 2026-02-25
**Domain:** UI consistency, cross-browser compatibility, accessibility, visual regression
**Confidence:** HIGH

## Summary

Phase 10 is a quality gate, not a feature phase. It validates that all prior phases (6-9) produced a cohesive, accessible, cross-browser-compatible UI. The codebase is a single-file JS theme (`ThemeQCExtension.js`, ~2300 lines) injecting CSS and behavior into Fava's SPA, plus 10 Jinja2 HTML templates for extensions. All styling flows through CSS custom properties defined on `:root`, with a design system of `--qc-*` and `--cqc-*` tokens.

The research reveals three concrete areas requiring attention: (1) typography inconsistencies across templates where some use hardcoded values instead of the type scale tokens, (2) zero ARIA attributes in any extension template -- a significant accessibility gap, and (3) no existing cross-browser or visual regression testing infrastructure. The project has pytest for backend logic but no browser-level tests.

**Primary recommendation:** Structure this phase as a single plan with four sequential tasks: typography/spacing audit with fixes, cross-browser manual testing checklist, accessibility remediation (ARIA labels, focus management, semantic HTML), and a functional regression walkthrough of all v1.0 features.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Playwright | Latest | Cross-browser testing (Chromium, WebKit, Firefox) | Already available via MCP tools in this project; supports all three target browsers on macOS |
| Lighthouse | Built into Chrome DevTools | Accessibility scoring | Free, authoritative, tests WCAG 2.1 AA compliance |
| axe-core | N/A (via browser extension) | Accessibility audit | Industry standard WCAG automated testing; catches ~57% of accessibility issues |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| WAVE | Browser extension | Visual accessibility overlay | Manual testing to see focus order, heading structure, ARIA labels |
| Safari Web Inspector | Built-in | WebKit-specific CSS debugging | When verifying Safari rendering differences |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Playwright screenshots | Percy/BrowserStack | Cloud-based visual regression; overkill for solo internal tool |
| Manual cross-browser | Automated visual regression | Would require baseline screenshots and CI; premature for this project |
| Full WCAG 2.2 AA audit | Targeted keyboard/screen reader | Full audit is expensive; targeted checks cover the success criteria |

**Installation:**
No new dependencies needed. Playwright is available via MCP. Lighthouse and axe are browser DevTools features. The phase is primarily manual auditing with targeted code fixes.

## Architecture Patterns

### Current UI Architecture
```
ThemeQCExtension.js (single file)
├── THEME_CSS (string literal ~1270 lines)
│   ├── :root CSS custom properties (colors, type scale, shadows, radii)
│   ├── Component classes (.cqc-card, .cqc-table, .cqc-badge, etc.)
│   ├── Fava override rules (header, sidebar, article, flex-table)
│   └── @media queries (responsive, prefers-reduced-motion)
├── JS functions
│   ├── injectStyle() / injectBrand() / reorganizeSidebar()
│   ├── Chart.js lifecycle (loadChartJs, renderCharts, destroyAllCharts)
│   ├── Animation (animatePageEntry, animateKPIs, prefersReducedMotion)
│   ├── Tooltips (initTooltipPopup, attachTooltips, showTooltip)
│   ├── Report headers (injectReportHeader)
│   ├── Keyboard (initApprovalKeyboard)
│   └── Sidebar badge (updateSidebarBadge)
└── Fava module export { init(), onPageLoad() }
```

### Extension Templates (10 total)
```
src/compteqc/fava_ext/
├── tableau_bord/templates/TableauBordExtension.html    # Dashboard with charts
├── approbation/templates/ApprobationExtension.html     # Approval queue
├── paie_qc/templates/PaieQCExtension.html              # Payroll
├── taxes_qc/templates/TaxesQCExtension.html             # GST/QST
├── dpa_qc/templates/DpaQCExtension.html                 # CCA/DPA
├── pret_actionnaire/templates/PretActionnaireExtension.html  # Shareholder loan
├── echeances/templates/EcheancesExtension.html          # Tax deadlines
├── export_cpa/templates/ExportCPAExtension.html         # CPA export
├── recus/templates/RecusExtension.html                  # Receipt upload
└── theme_qc/ThemeQCExtension.js                         # Theme (no template)
```

### Pattern 1: Typography Audit via Token Verification
**What:** Check every template and CSS rule to ensure type sizes, weights, and line-heights use the defined `--cqc-font-*` and `--cqc-weight-*` tokens instead of hardcoded values.
**When to use:** During the typography consistency task.
**Known issues found during research:**
- `ThemeQCExtension.js` CSS uses hardcoded `font-size` values in several places (e.g., `font-size: 0.78em`, `font-size: 0.88em`, `font-size: 0.82em`) that do not map to any `--cqc-font-*` token
- `.cqc-kpi-label` uses `font-size: 0.75em` -- not in the type scale
- `.cqc-badge` uses `font-size: 0.78em` -- not in the type scale
- `.cqc-dropzone-text .icone` uses `font-size: 2.5em` -- not in the type scale
- Several `font-weight` values are hardcoded (e.g., `450`, `700`) instead of using `--cqc-weight-*` tokens
- Dashboard template has an inline `<style>` block for chart grid layout

### Pattern 2: Accessibility Remediation
**What:** Add ARIA attributes, roles, and labels to all interactive elements.
**Current state:** Zero ARIA attributes exist in any extension template. This means:
- Tables have no `role="table"` (though native `<table>` elements get this implicitly)
- Buttons in the approval queue lack `aria-label` for screen readers
- Confidence bars (visual-only divs) have no `aria-valuenow`/`aria-valuemin`/`aria-valuemax`
- Keyboard shortcut listeners don't set `aria-selected` on focused rows
- Badge counts in sidebar lack `aria-live` for dynamic updates
- Dropzone has no `role="button"` or `aria-label` for screen readers
- Chart canvases have no `aria-label` describing the chart content
- Form fields in approval queue's reject section lack proper `<label>` association

### Pattern 3: Cross-Browser Testing Checklist
**What:** Manual verification of specific CSS features known to differ between Safari/Chrome/Firefox.
**When to use:** During the cross-browser testing task.
**Key areas to verify:**
1. `position: sticky` on `.cqc-table thead th` -- known issues in Safari with certain scroll containers
2. `backdrop-filter: blur(4px)` on header inputs -- Safari was first to support, Chrome caught up, Firefox support is newer
3. `font-variant-numeric: tabular-nums` -- supported in all three but Inter font rendering may differ
4. `-webkit-scrollbar` custom styles -- WebKit/Blink only, Firefox ignores them (use `scrollbar-width: thin` for Firefox)
5. `CSS custom properties` inheritance through Fava's Svelte-scoped components
6. `gap` in `flexbox` -- fully supported now but older Safari versions had issues

### Anti-Patterns to Avoid
- **Full visual regression automation for a solo tool:** Setting up Playwright screenshot baselines across 3 browsers and maintaining them adds complexity that exceeds the value for a single-user internal tool. Manual verification with a checklist is more appropriate.
- **WCAG 2.2 AAA compliance:** Targeting AAA is excessive for an internal accounting tool. Focus on practical keyboard access and screen reader basics (WCAG 2.1 AA level).
- **Refactoring the single-file architecture:** Phase 10 is about polish, not restructuring. The single JS file works and splitting it would risk regressions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Accessibility audit | Custom checklist from scratch | Lighthouse + axe-core automated scan | These tools check ~57% of WCAG criteria automatically; supplement with manual keyboard/screen reader testing |
| Cross-browser CSS testing | Pixel-perfect screenshot comparison | Manual checklist + browser DevTools | For 10 pages x 3 browsers, manual testing with a focused checklist is faster than setting up visual regression infra |
| Typography consistency | Manual grep-and-count | CSS custom property audit script | A simple grep for hardcoded `font-size` and `font-weight` values in the CSS string identifies all violations |

**Key insight:** Phase 10 is a validation phase, not a feature phase. The goal is to find and fix inconsistencies, not to build new infrastructure. Keep the tooling lightweight.

## Common Pitfalls

### Pitfall 1: Safari position:sticky in Scroll Containers
**What goes wrong:** `position: sticky` on table headers may not work correctly in Safari when the table is inside an element with `overflow: hidden` or when the containing block has certain properties.
**Why it happens:** WebKit has longstanding bugs with sticky positioning inside overflow containers.
**How to avoid:** Test sticky headers in Safari by scrolling long tables. If broken, ensure no ancestor has `overflow: hidden` that would clip the sticky element.
**Warning signs:** Headers scroll away with content in Safari but stick correctly in Chrome/Firefox.

### Pitfall 2: Missing Focus Indicators
**What goes wrong:** Custom button styles (`.cqc-btn`) may override the browser's default focus ring without providing a replacement, making keyboard navigation invisible.
**Why it happens:** The `transition: all` on buttons can transition the outline away. The current CSS has no explicit `:focus-visible` rules for `.cqc-btn` or `.cqc-badge`.
**How to avoid:** Add `:focus-visible` styles with a visible outline to all interactive elements (buttons, links, checkboxes, inputs).
**Warning signs:** Tab through the page -- if you cannot see where focus is, this pitfall has occurred.

### Pitfall 3: Screen Reader Announcement of Dynamic Content
**What goes wrong:** The sidebar badge count (updated via fetch on each page load) and KPI animations change content without notifying screen readers.
**Why it happens:** Dynamic DOM changes are invisible to assistive technology unless marked with `aria-live` regions.
**How to avoid:** Add `aria-live="polite"` to the sidebar badge container and ensure KPI values have their final values in the DOM (the server-rendered fallback already handles this).
**Warning signs:** VoiceOver does not announce the pending count when it updates.

### Pitfall 4: Keyboard Traps in Modal-like Interactions
**What goes wrong:** The approval queue's keyboard shortcuts (j/k/Space/a) could interfere with browser or screen reader shortcuts.
**Why it happens:** Single-letter keyboard shortcuts conflict with screen reader browse mode (VoiceOver uses single letters for navigation).
**How to avoid:** Ensure keyboard shortcuts only activate when the user has explicitly focused the table region, or provide a way to disable them. The current implementation already guards against input fields but not screen reader browse mode.
**Warning signs:** VoiceOver users cannot use single-letter navigation commands on the Approbation page.

### Pitfall 5: Hardcoded Color Values Outside the Design System
**What goes wrong:** Some CSS rules use hardcoded hex colors (e.g., `#15803D`, `#C2410C`, `#B91C1C`, `#92400E`) instead of CSS custom properties.
**Why it happens:** Alert text colors and hover states were defined with direct hex values during earlier phases.
**How to avoid:** Audit all hardcoded color values and determine if they should be tokenized or if they are intentional one-offs (darker shades for text-on-colored-background contrast).
**Warning signs:** Changing a semantic color variable doesn't update all related UI elements.

### Pitfall 6: WebKit Scrollbar Styles Not Applying in Firefox
**What goes wrong:** The sidebar custom scrollbar (`::-webkit-scrollbar`) only works in Chrome/Safari. Firefox shows its default scrollbar.
**Why it happens:** Firefox uses the `scrollbar-width` and `scrollbar-color` CSS properties instead of the WebKit pseudo-elements.
**How to avoid:** Add `scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.1) transparent;` to the `aside` rule for Firefox compatibility.
**Warning signs:** Thick default scrollbar visible in Firefox sidebar.

## Code Examples

### Typography Audit: Finding Hardcoded Values
```bash
# Find all hardcoded font-size values in the CSS string
grep -n 'font-size:' ThemeQCExtension.js | grep -v 'var(--cqc' | grep -v '// '

# Find all hardcoded font-weight values
grep -n 'font-weight:' ThemeQCExtension.js | grep -v 'var(--cqc' | grep -v '// '
```

### Accessibility: Focus-Visible for Buttons
```css
/* Add to THEME_CSS */
.cqc-btn:focus-visible,
.cqc-badge:focus-visible,
article a:focus-visible,
aside a:focus-visible {
  outline: 2px solid var(--qc-blue);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(0, 61, 165, 0.15);
}
```

### Accessibility: ARIA for Confidence Bars
```html
<!-- In ApprobationExtension.html -->
<div class="cqc-confidence cqc-confidence-{{ level }}"
     role="meter"
     aria-valuenow="{{ (txn.confiance * 100)|round|int }}"
     aria-valuemin="0"
     aria-valuemax="100"
     aria-label="Confiance de categorisation: {{ (txn.confiance * 100)|round|int }}%">
```

### Accessibility: Chart Canvas Labels
```html
<!-- In TableauBordExtension.html -->
<canvas aria-label="Graphique des revenus mensuels {{ extension.annee() }}"
        role="img"></canvas>
```

### Firefox Scrollbar Fallback
```css
/* Add alongside ::-webkit-scrollbar rules */
aside {
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.1) transparent;
}
```

### Accessibility: Sidebar Badge Live Region
```javascript
// In updateSidebarBadge()
badge.setAttribute('aria-live', 'polite');
badge.setAttribute('aria-label', data.count + ' transactions en attente');
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `:focus` for all | `:focus-visible` for keyboard-only | CSS Level 4 / 2022+ | Shows focus ring only for keyboard users, not mouse clicks |
| `-webkit-scrollbar` only | `scrollbar-width` + `-webkit-scrollbar` | Firefox 64+ (2018) | Need both for cross-browser custom scrollbars |
| `role="application"` on SPAs | Minimal ARIA, semantic HTML first | WCAG 2.2 guidance | Over-ARIA is worse than under-ARIA; use native elements |
| Pixel-perfect cross-browser | "Good enough" with progressive enhancement | Industry consensus | Minor rendering differences between browsers are acceptable |

**Deprecated/outdated:**
- `tabindex="-1"` on every non-interactive element: outdated pattern, use only where needed for focus management
- `::-moz-scrollbar`: never existed; use `scrollbar-width` for Firefox

## Open Questions

1. **Should the approval queue keyboard shortcuts be scoped to an explicit focus mode?**
   - What we know: Current implementation fires on any keypress when not in an input field. Screen readers in browse mode use single-letter keys.
   - What's unclear: Whether the sole user uses a screen reader on the Approbation page.
   - Recommendation: Add `aria-roledescription` to the table and document the keyboard shortcuts in an `aria-describedby` region. Do not change the current behavior unless screen reader usage is confirmed.

2. **How many hardcoded font-size values should be migrated to tokens?**
   - What we know: The type scale has 8 stops (xs through 3xl). Many CSS rules use `em`-based sizes (0.75em, 0.78em, 0.82em, etc.) that fall between token values.
   - What's unclear: Whether adding more token stops or mapping existing values to the nearest token is better.
   - Recommendation: Map to nearest token where the difference is < 2px at 14px base. For values that don't map cleanly, leave as-is but document them as intentional.

3. **Should `!important` count be further reduced?**
   - What we know: Current count is 21 lines with `!important`. Phase 6 target was 80% reduction from 97. The remaining `!important` declarations are justified (Svelte-scoped overrides, accessibility reduced-motion, Chart.js canvas sizing).
   - What's unclear: Whether any remaining `!important` can be eliminated by reordering CSS injection.
   - Recommendation: Document each remaining `!important` with inline comments explaining why it is necessary. Do not attempt further reduction as each remaining one overrides Svelte-injected inline styles.

## Inventory of All Extension Pages to Audit

| # | Extension | URL Path | Has Table | Has KPIs | Has Charts | Has Forms | Interactive JS |
|---|-----------|----------|-----------|----------|------------|-----------|----------------|
| 1 | Tableau de bord | TableauBordExtension | Yes | Yes (5) | Yes (2) | No | KPI animation, charts |
| 2 | Approbation | ApprobationExtension | Yes | No | No | Yes (approve/reject) | Keyboard shortcuts |
| 3 | Paie Quebec | PaieQCExtension | Yes (2) | Yes (4) | No | No | Tooltips |
| 4 | TPS/TVQ | TaxesQCExtension | Yes | Yes (3) | No | No | Tooltips |
| 5 | DPA/CCA | DpaQCExtension | Yes | No | No | No | Tooltips |
| 6 | Pret actionnaire | PretActionnaireExtension | Yes (2) | No | No | No | Tooltips |
| 7 | Echeances | EcheancesExtension | No | No | No | No | None |
| 8 | Export CPA | ExportCPAExtension | No | No | No | No | None |
| 9 | Recus | RecusExtension | Yes | No | No | Yes (upload) | Drag-and-drop |
| 10 | Fava native pages | income_statement, balance_sheet, trial_balance, journal | Yes (flex-table) | No | Yes (Fava SVG) | No | Report intro injection |

## Concrete Findings from Codebase Audit

### Typography Inconsistencies Found
1. **Hardcoded `font-size` values not in type scale:** 0.72em, 0.73em, 0.75em, 0.76em, 0.78em, 0.8em, 0.82em, 0.85em, 0.88em, 0.9em, 0.92em, 0.95em, 1em, 1.3em, 2.2em, 2.5em
2. **Hardcoded `font-weight: 450`:** used in sidebar links, solde-direction, report intro -- not in the `--cqc-weight-*` system (which has 400, 500, 600, 700)
3. **Type scale tokens defined but underused:** `--cqc-font-xs` through `--cqc-font-3xl` exist but most CSS rules use hardcoded em values

### Spacing Inconsistencies Found
1. **Padding varies across card types:** `.cqc-card` uses `22px 26px`, `.cqc-card-flush > .cqc-section-title` uses `16px 24px`, `.cqc-alert` uses `16px 20px`
2. **Gap values are inconsistent:** `.cqc-kpi-row` uses `16px`, `.cqc-dashboard-charts` uses `24px`, `.cqc-actions-bar` uses `10px`
3. **Margin-bottom varies:** `.cqc-card` uses `20px`, `.cqc-card-flush` uses `20px`, `.cqc-section-title` uses `16px`

### Accessibility Gaps Found
1. **Zero ARIA attributes** in any extension template HTML
2. **No `:focus-visible` styles** for custom interactive elements
3. **Charts have no text alternative** (`<canvas>` without `aria-label`)
4. **Confidence bars are purely visual** (no ARIA meter role)
5. **Dynamic sidebar badge** has no `aria-live` announcement
6. **Dropzone** has no `role="button"` and relies on `onclick` with `<div>`
7. **Keyboard shortcuts** not documented in an accessible way (hint text exists but is not associated with the table)

### Cross-Browser Risks Identified
1. **`::-webkit-scrollbar`** in sidebar -- Firefox will show default scrollbar
2. **`backdrop-filter: blur(4px)`** on header inputs -- verify Firefox support
3. **`position: sticky`** on table headers -- verify Safari with scroll containers
4. **Google Fonts CDN load** -- verify no FOUT differences between browsers
5. **`font-variant-numeric: tabular-nums`** -- verify Inter renders identically across browsers

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` (2319 lines) -- full CSS and JS source reviewed
- Codebase analysis: All 10 extension HTML templates reviewed for consistency
- Phase 6, 7, 8 verification reports reviewed for known gaps and human-verification items
- [Can I Use: font-variant-numeric](https://caniuse.com/font-variant-numeric) -- browser support confirmed
- [MDN: font-variant-numeric](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/font-variant-numeric) -- usage reference

### Secondary (MEDIUM confidence)
- [LambdaTest: CSS position:sticky cross-browser](https://www.lambdatest.com/web-technologies/css-sticky) -- Safari sticky positioning issues
- [W3C WAI: Easy Checks for Accessibility](https://www.w3.org/WAI/test-evaluate/preliminary/) -- accessibility audit methodology
- [Playwright visual testing docs](https://playwright.dev/docs/test-snapshots) -- screenshot comparison approach

### Tertiary (LOW confidence)
- None -- all findings verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed; browser DevTools and manual testing
- Architecture: HIGH -- direct codebase analysis with specific line-number evidence
- Pitfalls: HIGH -- identified from actual code patterns, not hypothetical scenarios
- Accessibility gaps: HIGH -- verified by grep showing zero ARIA attributes in templates

**Research date:** 2026-02-25
**Valid until:** 2026-04-01 (stable -- no external dependencies changing)
