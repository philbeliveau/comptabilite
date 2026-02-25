---
phase: quick-5
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
autonomous: true
requirements: [QUICK-5]

must_haves:
  truths:
    - "Hovering any tooltipped element shows the full tooltip text without clipping"
    - "Tooltip popup is always fully readable within the viewport"
    - "Tooltip does not get cut by parent overflow:hidden containers (KPI tiles, card-flush tables)"
  artifacts:
    - path: "src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js"
      provides: "JS-rendered tooltip popup appended to document.body"
  key_links:
    - from: "mouseenter on [data-tooltip]"
      to: "#cqc-tooltip-popup div"
      via: "positionTooltip() using getBoundingClientRect + viewport clamping"
      pattern: "getBoundingClientRect"
---

<objective>
Fix all informational popups (tooltips) in the Fava dashboard so they fully display without clipping.

Purpose: The current CSS ::after pseudo-element tooltip approach is clipped by parent containers with overflow:hidden (notably .cqc-kpi tiles and .cqc-card-flush tables). Users cannot read the tooltip text.

Output: A single JS-rendered tooltip div appended to document.body, positioned via JavaScript with viewport edge clamping, replacing the CSS-only approach.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace CSS tooltip with JS-rendered body-level popup</name>
  <files>src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js</files>
  <action>
The current tooltip system uses CSS `[data-tooltip]::after` with `position: absolute`. This gets clipped by parent containers that have `overflow: hidden` (specifically `.cqc-kpi` at line 387 and `.cqc-card-flush` at line 334). The tooltip is invisible or cut off inside KPI tiles and flush-card tables.

Fix: Replace the CSS ::after tooltip with a JS-rendered single `div#cqc-tooltip-popup` appended to `document.body` once, then positioned on mouseenter/focus using `getBoundingClientRect`.

**Changes to make in ThemeQCExtension.js:**

1. In the `THEME_CSS` string, replace the entire `[data-tooltip]` and `[data-tooltip]::after` CSS block (lines 1015-1053) with:
```css
/* ===== Tooltip system ===== */
[data-tooltip] {
  cursor: help;
  text-decoration: underline dotted var(--qc-muted);
  text-underline-offset: 3px;
}

#cqc-tooltip-popup {
  position: fixed;
  z-index: 9999;
  background: var(--qc-surface-sidebar);
  color: #fff;
  padding: 10px 14px;
  border-radius: var(--qc-radius-sm);
  font-size: 0.82em;
  font-weight: 400;
  line-height: 1.5;
  max-width: 320px;
  box-shadow: var(--qc-shadow-lg);
  pointer-events: none;
  white-space: normal;
  text-align: left;
  opacity: 0;
  visibility: hidden;
  transition: opacity 150ms ease, visibility 150ms ease;
  font-family: 'Inter', sans-serif;
}

#cqc-tooltip-popup.cqc-tooltip-visible {
  opacity: 1;
  visibility: visible;
}
```

2. Add a new function `initTooltipPopup()` (place it after the `attachTooltips` function, before `injectReportHeader`):
```js
function initTooltipPopup() {
  // Idempotent: only create once
  if (document.getElementById('cqc-tooltip-popup')) return;

  const popup = document.createElement('div');
  popup.id = 'cqc-tooltip-popup';
  document.body.appendChild(popup);

  // Single delegated listener on document
  document.addEventListener('mouseover', (e) => {
    const target = e.target.closest('[data-tooltip]');
    if (!target) {
      hideTooltip();
      return;
    }
    showTooltip(target);
  });

  document.addEventListener('mouseout', (e) => {
    // Only hide if leaving the tooltipped element entirely
    const target = e.target.closest('[data-tooltip]');
    if (target && !target.contains(e.relatedTarget)) {
      hideTooltip();
    }
  });

  // Keyboard: show on focus, hide on blur
  document.addEventListener('focusin', (e) => {
    const target = e.target.closest('[data-tooltip]');
    if (target) showTooltip(target);
  });

  document.addEventListener('focusout', (e) => {
    const target = e.target.closest('[data-tooltip]');
    if (target) hideTooltip();
  });
}

function showTooltip(el) {
  const popup = document.getElementById('cqc-tooltip-popup');
  if (!popup) return;

  const text = el.getAttribute('data-tooltip');
  if (!text) return;

  popup.textContent = text;
  popup.classList.remove('cqc-tooltip-visible');

  // Temporarily show off-screen to measure size
  popup.style.left = '-9999px';
  popup.style.top = '-9999px';
  popup.style.visibility = 'hidden';
  popup.style.opacity = '0';
  popup.style.display = 'block';

  // Use rAF to let browser compute popup size
  requestAnimationFrame(() => {
    const rect = el.getBoundingClientRect();
    const popupRect = popup.getBoundingClientRect();
    const margin = 8;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    // Default: above element, centered horizontally
    let top = rect.top - popupRect.height - margin;
    let left = rect.left + rect.width / 2 - popupRect.width / 2;

    // If no room above, place below
    if (top < margin) {
      top = rect.bottom + margin;
    }

    // Clamp horizontally: keep within viewport with 8px padding
    left = Math.max(margin, Math.min(left, vw - popupRect.width - margin));

    // Clamp vertically: keep within viewport
    top = Math.max(margin, Math.min(top, vh - popupRect.height - margin));

    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
    popup.style.visibility = '';
    popup.style.opacity = '';
    popup.classList.add('cqc-tooltip-visible');
  });
}

function hideTooltip() {
  const popup = document.getElementById('cqc-tooltip-popup');
  if (popup) popup.classList.remove('cqc-tooltip-visible');
}
```

3. In the `onPageLoad()` export, add `initTooltipPopup();` call right after `injectStyle();` (call it once per page load, it is idempotent internally).

4. Remove the `position: relative` from the `[data-tooltip]` block in the CSS since the popup is now `position: fixed` on body.

Do NOT change any other CSS blocks, the TOOLTIPS dictionary, the attachTooltips() function logic, or the SIDEBAR_GROUPS / REPORT_INTROS sections.
  </action>
  <verify>
Start Fava and open any extension page (e.g. Paie QC). Hover over a KPI tile label or a table column header. The tooltip popup should appear above the element, fully readable, without being cut off by the tile border. Try hovering elements near the right edge of the viewport — tooltip should clamp left so it stays visible.

Manual check: `python -m fava data/comptabilite.beancount` then open http://localhost:5000 and hover tooltip elements.
  </verify>
  <done>
- Hovering any element with data-tooltip shows the full tooltip text in a readable popup
- Popup is never clipped by parent overflow:hidden containers
- Popup stays within viewport on all screen positions (left/right/top/bottom edges)
- KPI tile tooltips display correctly (previously cut by .cqc-kpi overflow:hidden)
- Table header tooltips in .cqc-card-flush display correctly
  </done>
</task>

</tasks>

<verification>
After implementing, verify:
1. Open Fava in browser
2. Go to Paie QC extension page
3. Hover each KPI tile label (Salaire brut, Salaire net, etc.) — full popup visible
4. Hover a table column header — popup appears above, not clipped
5. Hover an element near the right viewport edge — popup clamps left, stays readable
6. Hover an element near the top — popup falls below the element instead of going off-screen
</verification>

<success_criteria>
All tooltip popups display fully without clipping on any page in the Fava dashboard. The fix uses a body-appended fixed div with viewport clamping, bypassing all parent overflow:hidden constraints.
</success_criteria>

<output>
After completion, create `.planning/quick/5-fix-all-the-informational-pop-up-the-pop/5-SUMMARY.md` with what was changed and how it was verified.
</output>
