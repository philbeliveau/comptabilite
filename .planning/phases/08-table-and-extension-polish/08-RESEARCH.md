# Phase 8: Table and Extension Polish - Research

**Researched:** 2026-02-25
**Domain:** CSS table styling, keyboard-driven approval UX, SPA page transitions, sidebar badge injection
**Confidence:** HIGH

## Summary

Phase 8 is a pure frontend polish phase operating entirely within the existing Fava extension architecture. The codebase already has a comprehensive design system in `ThemeQCExtension.js` with CSS variables, `.cqc-table` styling, badges, and a `onPageLoad()` lifecycle hook. The work involves: (1) auditing and enhancing table CSS across 8 extension templates, (2) redesigning the approval queue with keyboard shortcuts and improved confidence visualization, (3) adding CSS page entrance animations triggered on SPA navigation, and (4) injecting a pending count badge into the sidebar.

All 4 requirements can be implemented by modifying two files: `ThemeQCExtension.js` (CSS additions + JS logic) and `ApprobationExtension.html` (approval queue template redesign). No new libraries are needed. The existing `onPageLoad()` hook fires on every Fava SPA navigation, which is the right place for animations, sidebar badge injection, and keyboard shortcut binding.

**Primary recommendation:** Implement everything in the existing `ThemeQCExtension.js` (CSS + JS) and `ApprobationExtension.html`. No new dependencies required.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TBLX-01 | All 8 extension tables have hover states, consistent padding, and visual header hierarchy | Existing `.cqc-table` styles need audit; some tables use inline styles that override the system. Research identifies all 8 templates and current inconsistencies. |
| TBLX-02 | Approval queue has redesigned confidence badges, keyboard shortcuts (approve/reject), and scannable layout | Current `ApprobationExtension.html` uses basic badges and no keyboard support. Research documents keyboard shortcut patterns (row selection with j/k, approve with a, reject with r) and badge redesign approach. |
| TBLX-03 | Page entrance animations (fade + slide) on extension navigation | Fava's `onPageLoad()` fires after `<article>` content is replaced. Research documents CSS animation injection approach using `@keyframes` and the animation safety net from DSYS-03. |
| TBLX-04 | Sidebar shows pending approval count badge on Approbation link | `onPageLoad()` already reorganizes the sidebar. Research documents approach: API call or DOM scrape to get count, inject badge span into sidebar link. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pure CSS | N/A | Table hover, padding, header hierarchy, page transitions | Already used throughout ThemeQCExtension.js; no JS framework needed for visual polish |
| Vanilla JS | N/A | Keyboard shortcuts, sidebar badge injection, animation triggers | Fava extension API requires vanilla ES modules; no bundler available |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Fava Extension API | 1.30+ | `onPageLoad()`, `onExtensionPageLoad()`, `init()` lifecycle | All JS logic hooks into these lifecycle methods |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pure CSS animations | GSAP / Framer Motion | Out of scope per REQUIREMENTS.md -- pure CSS covers all needs |
| Vanilla keyboard shortcuts | Hotkeys.js | Adds dependency for ~20 lines of code; not worth it |
| DOM-based pending count | Fetch API to extension endpoint | More reliable but requires adding a JSON endpoint; DOM scrape sufficient for v1.1 |

**Installation:**
```bash
# No installation required -- pure CSS + vanilla JS within existing files
```

## Architecture Patterns

### Recommended Project Structure

No new files needed. Modifications to:
```
src/compteqc/fava_ext/
  theme_qc/
    ThemeQCExtension.js        # Add: table polish CSS, page animation CSS, sidebar badge JS, keyboard shortcut JS
  approbation/
    templates/
      ApprobationExtension.html # Redesign: confidence badges, row layout, keyboard-navigable structure
    __init__.py                 # Possibly add: JSON endpoint for pending count (optional)
```

### Pattern 1: Table Styling Audit and Normalization

**What:** Review all 8 extension templates for inline styles that override `.cqc-table` and normalize them to use CSS classes.

**When to use:** When templates use `style="..."` attributes that conflict with the design system.

**Current state of all 8 extension tables:**

1. **ApprobationExtension.html** -- Uses `.cqc-table` with inline `style="width: 40px;"` on checkbox column. Has `.montant` class. Confidence badges use basic `.cqc-badge-*` classes.

2. **DpaQCExtension.html** -- Clean `.cqc-table` usage with `.montant` and `.sommaire-row`. No inline overrides. Already well-structured.

3. **TaxesQCExtension.html** -- Clean `.cqc-table` usage. Uses `.cqc-positif`/`.cqc-negatif` for color. Has `.sommaire-row`. Well-structured.

4. **PaieQCExtension.html** -- Two tables (cotisations + impots). Uses inline `style="display: flex; align-items: center; gap: 8px;"` inside progress cells. Has `style="padding: 16px 24px 0;"` on section title wrappers.

5. **PretActionnaireExtension.html** -- Two tables (avances s.15(2) + mouvements). Uses inline `style="padding: 16px 24px 0;"` on section title wrappers. Otherwise clean.

6. **EcheancesExtension.html** -- No table (alert-based layout). Not applicable for table styling, but should participate in page transitions.

7. **ExportCPAExtension.html** -- Placeholder only (Phase 5 stub). No table. Not applicable for table styling.

8. **RecusExtension.html** -- One table for recent uploads. Has inline `style="font-size: 0.85em; color: var(--qc-muted, #64748B);"` on path column cells.

**Key findings:**
- 5 of 8 extensions have actual tables (Approbation, DPA, Taxes, Paie, PretActionnaire, Recus = 6 tables across 5 extensions, plus Paie has 2)
- The existing `.cqc-table tbody tr:hover` rule already sets `background-color: var(--qc-blue-lighter)` but does NOT propagate to `td` backgrounds because `td` has `background: var(--qc-surface-raised)` which overrides the `tr` background
- This is a **known CSS bug**: when `td` has an explicit `background`, the `tr:hover` background is invisible. The fix is to make `td` inherit background on hover or use `tr:hover td` selector
- The `article table tbody tr:hover td` rule (line ~295) already does this for native Fava tables, but the `.cqc-table tbody tr:hover` rule (line ~471) targets only `tr`, not `td`

**Example fix:**
```css
/* Current (broken -- td background covers tr hover) */
.cqc-table tbody tr:hover {
  background-color: var(--qc-blue-lighter);
}

/* Fixed -- target td explicitly */
.cqc-table tbody tr:hover td {
  background-color: var(--qc-blue-lighter);
}
```

### Pattern 2: Page Entrance Animation via CSS @keyframes

**What:** Add a CSS `@keyframes` animation that fades and slides content in on every SPA navigation. Trigger it by adding/removing a CSS class on `<article>` in `onPageLoad()`.

**When to use:** On every SPA navigation (extension-to-extension or any Fava page).

**Example:**
```css
@keyframes cqc-page-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.cqc-page-entering {
  animation: cqc-page-enter 250ms cubic-bezier(0.4, 0, 0.2, 1) both;
}

/* Respect reduced motion */
@media (prefers-reduced-motion: reduce) {
  .cqc-page-entering {
    animation: none;
  }
}
```

**JS trigger in onPageLoad():**
```javascript
function triggerPageAnimation() {
  const article = document.querySelector("article");
  if (!article) return;
  article.classList.remove("cqc-page-entering");
  // Force reflow to restart animation
  void article.offsetHeight;
  article.classList.add("cqc-page-entering");
}
```

**Key insight:** Fava's SPA replaces the `<article>` content on navigation. The `onPageLoad()` hook fires after the new content is in the DOM. Adding an animation class at this point will animate the new content appearing.

### Pattern 3: Keyboard Shortcuts for Approval Queue

**What:** Add keyboard navigation (j/k for row selection, Space/Enter for toggle checkbox, a for approve selected, r for reject focused) scoped only to the approval page.

**When to use:** Only on the ApprobationExtension page.

**Example:**
```javascript
function initApprovalKeyboard() {
  // Only activate on approval page
  if (!window.location.pathname.includes("ApprobationExtension")) return;

  const rows = document.querySelectorAll(".cqc-table tbody tr");
  if (rows.length === 0) return;

  let focusedRow = -1;

  function focusRow(index) {
    rows.forEach(r => r.classList.remove("cqc-row-focused"));
    if (index >= 0 && index < rows.length) {
      focusedRow = index;
      rows[index].classList.add("cqc-row-focused");
      rows[index].scrollIntoView({ block: "nearest" });
    }
  }

  document.addEventListener("keydown", (e) => {
    // Don't capture when typing in inputs
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;

    switch(e.key) {
      case "j": focusRow(Math.min(focusedRow + 1, rows.length - 1)); break;
      case "k": focusRow(Math.max(focusedRow - 1, 0)); break;
      case " ":
      case "Enter":
        if (focusedRow >= 0) {
          const cb = rows[focusedRow].querySelector('input[type="checkbox"]');
          if (cb) { cb.checked = !cb.checked; e.preventDefault(); }
        }
        break;
      case "a":
        document.querySelector('.cqc-btn-success[type="submit"]')?.click();
        break;
    }
  });
}
```

**Important:** Keyboard listeners must be scoped or removed on navigation to avoid ghost listeners. Since `onPageLoad()` fires on every navigation, use a cleanup pattern: remove old listener before adding new one.

### Pattern 4: Sidebar Pending Count Badge

**What:** On every page load, find the "Approbation" sidebar link and inject a count badge showing number of pending transactions.

**When to use:** In `onPageLoad()`, runs on every navigation.

**Two approaches:**

**Approach A: DOM scrape (simple, works now)**
When on the Approbation page, the count is in the subtitle span. But when on other pages, this data is not available. This approach only works ON the approval page.

**Approach B: Fetch from extension endpoint (reliable)**
Add a lightweight JSON endpoint to `ApprobationExtension` that returns `{"count": N}`. Call it from JS on every page load.

```python
# In ApprobationExtension
@extension_endpoint("count", ["GET"])
def pending_count(self):
    from flask import jsonify
    return jsonify({"count": len(self._pending)})
```

```javascript
async function updateSidebarBadge() {
  const link = Array.from(document.querySelectorAll("aside a"))
    .find(a => a.textContent.includes("Approbation") || a.href.includes("ApprobationExtension"));
  if (!link) return;

  try {
    const slug = window.location.pathname.split("/")[1]; // beancount file slug
    const resp = await fetch(`/${slug}/extension/ApprobationExtension/count`);
    const data = await resp.json();

    // Remove existing badge
    const existing = link.querySelector(".cqc-sidebar-badge");
    if (existing) existing.remove();

    if (data.count > 0) {
      const badge = document.createElement("span");
      badge.className = "cqc-sidebar-badge";
      badge.textContent = String(data.count);
      link.appendChild(badge);
    }
  } catch (e) {
    // Silently fail -- badge is cosmetic
  }
}
```

**Recommendation:** Use Approach B (fetch endpoint). It is more reliable and works from any page. The endpoint is trivial to add (3 lines of Python).

### Anti-Patterns to Avoid

- **Inline styles in templates:** Several templates have `style="..."` that should be extracted to CSS classes. Phase 8 should clean these up.
- **tr:hover without td:hover:** The current `.cqc-table` hover rule targets `tr` but `td` has explicit background, masking the hover. Must target `tr:hover td`.
- **Global keyboard listeners without cleanup:** Adding `document.addEventListener("keydown", ...)` in `onPageLoad()` will accumulate listeners across navigations. Must use a cleanup pattern (store reference, remove on next call).
- **Blocking fetch for badge:** The sidebar badge fetch must be `async` and non-blocking. A failed fetch should not break the page.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS animations | JS-based animation timing | CSS `@keyframes` with `animation` property | Hardware-accelerated, respects `prefers-reduced-motion` automatically when properly coded |
| Keyboard shortcut framework | Custom key combo parser | Simple `switch(e.key)` handler | Only 4-5 shortcuts needed; a framework is overkill |
| Notification badge | Custom polling/WebSocket | Single fetch on `onPageLoad()` | Fava is request-based; count only needs to be current at page load |

**Key insight:** This phase is entirely CSS + vanilla JS. The existing ThemeQCExtension.js pattern (single file with CSS string + JS functions + Fava lifecycle hooks) works perfectly and should not be replaced with a more complex architecture.

## Common Pitfalls

### Pitfall 1: td background masking tr:hover

**What goes wrong:** Setting `background` on `<td>` elements makes `<tr>:hover { background: ... }` invisible because the td's background paints on top.

**Why it happens:** CSS paint order: td background renders above tr background.

**How to avoid:** Always use `.cqc-table tbody tr:hover td { background-color: ...; }` selector.

**Warning signs:** Hovering over table rows produces no visual change despite CSS being present.

### Pitfall 2: Keyboard listener accumulation on SPA navigation

**What goes wrong:** Each `onPageLoad()` call adds a new `keydown` listener. After 10 navigations, 10 listeners fire simultaneously causing duplicate actions.

**Why it happens:** Fava SPA replaces `<article>` content but does not destroy/recreate JS context. `document`-level listeners persist.

**How to avoid:** Store the listener reference in a module-level variable. In `onPageLoad()`, call `removeEventListener` with the old reference before adding a new one. Alternatively, use `AbortController` for cleanup.

```javascript
let keyboardController = null;

function initApprovalKeyboard() {
  // Clean up previous listener
  if (keyboardController) keyboardController.abort();
  keyboardController = new AbortController();

  if (!window.location.pathname.includes("ApprobationExtension")) return;

  document.addEventListener("keydown", handler, { signal: keyboardController.signal });
}
```

### Pitfall 3: Animation replaying on same page

**What goes wrong:** Adding the animation class in `onPageLoad()` without removing it first means the animation does not replay when navigating away and back.

**Why it happens:** CSS animation only plays once per class addition. If the class is already present, re-adding it does nothing.

**How to avoid:** Remove the class, force a reflow (`void element.offsetHeight`), then re-add it.

### Pitfall 4: Sidebar badge fetch failing silently but breaking layout

**What goes wrong:** If the fetch to `/extension/ApprobationExtension/count` fails (404, network error), an unhandled promise rejection may appear in console, and old badges may persist.

**Why it happens:** Endpoint might not be registered, or extension might not be loaded.

**How to avoid:** Wrap in try/catch, always remove existing badge before attempting to add new one. On failure, leave no badge rather than stale data.

### Pitfall 5: Confidence badge redesign breaking existing functionality

**What goes wrong:** Changing the badge markup in ApprobationExtension.html could break the form submission or the checkbox selection logic.

**Why it happens:** The form uses `name="ids"` and `value="{{ loop.index0 }}"` which must be preserved.

**How to avoid:** Keep the form structure (checkbox name/value) exactly the same. Only change visual presentation (CSS classes, layout, additional visual elements).

## Code Examples

### Table Hover Fix (verified from codebase analysis)

```css
/* Fix: target td explicitly for hover to be visible */
.cqc-table tbody tr:hover td {
  background-color: var(--qc-blue-lighter) !important;
}

/* Focused row (keyboard navigation) */
.cqc-table tbody tr.cqc-row-focused td {
  background-color: rgba(0, 61, 165, 0.08) !important;
  outline: 2px solid var(--qc-blue);
  outline-offset: -2px;
}
```

### Consistent Header Hierarchy

```css
/* Stronger visual header styling */
.cqc-table thead th {
  background-color: var(--qc-blue-lighter);
  color: var(--qc-blue-dark);
  font-weight: 700;
  font-size: 0.76em;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 12px 16px;
  border-bottom: 2px solid var(--qc-blue);
  position: sticky;
  top: 0;
  z-index: 1;
}
```

### Redesigned Confidence Badges

```css
/* Confidence badge with numeric percentage */
.cqc-confidence {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.cqc-confidence-bar {
  width: 48px;
  height: 6px;
  border-radius: 3px;
  background: var(--qc-border);
  overflow: hidden;
}

.cqc-confidence-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width var(--qc-transition-slow);
}

.cqc-confidence-high .cqc-confidence-bar-fill { background: var(--qc-success); }
.cqc-confidence-medium .cqc-confidence-bar-fill { background: var(--qc-amber); }
.cqc-confidence-low .cqc-confidence-bar-fill { background: var(--qc-error); }
```

### Sidebar Badge CSS

```css
.cqc-sidebar-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: var(--qc-error);
  color: #fff;
  font-size: 0.72em;
  font-weight: 700;
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}
```

### Page Enter Animation with Safety Net

```css
@keyframes cqc-page-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

article.cqc-page-entering {
  animation: cqc-page-enter 200ms cubic-bezier(0.4, 0, 0.2, 1) both;
}

@media (prefers-reduced-motion: reduce) {
  article.cqc-page-entering {
    animation: none;
    opacity: 1;
    transform: none;
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| tr:hover for table rows | tr:hover td for explicit targeting | Always been best practice | Ensures hover is visible when td has background |
| JS-based animation | CSS @keyframes + class toggle | CSS3 (2012+) | Hardware-accelerated, declarative, respects prefers-reduced-motion |
| Global keyboard handlers | AbortController-scoped handlers | AbortController widely supported since 2019 | Clean lifecycle management without manual reference tracking |

**Deprecated/outdated:**
- `element.animate()` (Web Animations API) -- perfectly valid but overkill for simple entrance animations; CSS @keyframes is simpler and equally performant

## Open Questions

1. **Sidebar badge: fetch vs DOM approach**
   - What we know: A fetch endpoint is more reliable but requires adding Python code to ApprobationExtension
   - What's unclear: Whether the user prefers to keep Phase 8 as pure CSS/JS-only or is okay adding a small Python endpoint
   - Recommendation: Add the JSON endpoint (3 lines of Python). It's trivial and the benefit is significant -- badge works from any page.

2. **How many tables qualify as "8 extension tables"?**
   - What we know: There are 8 extensions in the sidebar. Of those, 5 have actual data tables (Approbation, DPA, Taxes, Paie x2 tables, PretActionnaire x2 tables, Recus = 8 tables total). Echeances and ExportCPA are alert/placeholder pages.
   - What's unclear: Whether "8 extension tables" means "tables in all 8 extensions" or "exactly 8 table elements"
   - Recommendation: Polish all tables that exist (8 table elements across 5 extensions) and ensure consistent styling on non-table extensions too (page headers, cards).

3. **Keyboard shortcut discoverability**
   - What we know: Users won't know shortcuts exist unless told
   - What's unclear: How to communicate available shortcuts
   - Recommendation: Add a small "Raccourcis: j/k naviguer, Espace selectionner, a approuver" hint text below the actions bar on the approval page.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** of `ThemeQCExtension.js` (1770 lines) -- complete CSS design system, JS lifecycle hooks, sidebar reorganization
- **Codebase analysis** of all 8 extension templates -- identified exact table structures, inline style overrides, form mechanics
- **Codebase analysis** of `ApprobationExtension.__init__.py` -- understood pending transaction data model, form endpoints
- **Fava extension API** from `FavaExtTest.js` -- confirmed `init()`, `onPageLoad()`, `onExtensionPageLoad(ctx)` lifecycle

### Secondary (MEDIUM confidence)
- **CSS animation patterns** -- `@keyframes` with forced reflow for replay is a well-documented pattern
- **AbortController for event cleanup** -- standard DOM API, supported in all modern browsers

### Tertiary (LOW confidence)
- None -- all findings verified from codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed; everything builds on existing ThemeQCExtension.js patterns
- Architecture: HIGH -- modifications to 2-3 existing files; patterns verified from codebase
- Pitfalls: HIGH -- all identified from direct codebase analysis (hover bug, listener accumulation)

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable -- CSS/JS patterns don't change)
