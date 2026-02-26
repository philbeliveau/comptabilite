---
phase: quick
plan: 18
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
autonomous: true
requirements: []
must_haves:
  truths:
    - "Table in ApprobationExtension scrolls horizontally when browser window is narrower than table content"
    - "Table remains fully usable at full width -- no visual regression"
    - "Other cqc-card-flush usages across extensions are not broken"
  artifacts:
    - path: "src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js"
      provides: "Responsive table scroll wrapper styles and responsive table sizing"
      contains: "overflow-x"
  key_links: []
---

<objective>
Make the ApprobationExtension table (and all cqc-table instances inside cqc-card-flush) responsive by adding horizontal scroll support when the viewport is too narrow.

Purpose: The table gets clipped on non-fullscreen browser windows because cqc-card-flush uses `overflow: hidden` and there is no scroll wrapper.
Output: Updated ThemeQCExtension.js with responsive table CSS.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
@src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add horizontal scroll wrapper and responsive table styles</name>
  <files>src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js</files>
  <action>
In ThemeQCExtension.js, make the following CSS changes:

1. Change `.cqc-card-flush` overflow from `overflow: hidden` to `overflow: visible` (line ~410). The border-radius clipping is handled by the inner scroll wrapper instead.

2. Add a new CSS rule block right after the `.cqc-card-flush` rules (after the hover rule around line 416). This creates an inner scroll wrapper for tables inside card-flush:

```css
/* Horizontal scroll wrapper for tables inside card-flush */
.cqc-card-flush > .cqc-table,
.cqc-card-flush > form > .cqc-table {
  display: block;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
```

Wait -- this approach changes table display. Better approach: wrap the table rendering. Since we cannot modify the HTML template structure easily (the table is directly inside cqc-card-flush or inside a form), the cleanest CSS-only fix is:

Actually, looking at ApprobationExtension.html, the table is inside `.cqc-card-flush` directly. The fix:

a) Keep `.cqc-card-flush` with `overflow: hidden` for border-radius clipping on the block axis, but change to `overflow-x: auto; overflow-y: hidden;` so horizontal content can scroll:

```css
.cqc-card-flush {
  /* existing properties unchanged */
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
}
```

b) Add responsive rules inside the existing `@media (max-width: 768px)` block to reduce table padding and font size for narrower viewports:

```css
/* Inside @media (max-width: 768px) */
.cqc-table thead th {
  padding: 8px 10px;
  font-size: var(--cqc-font-sm, 0.875rem);
}
.cqc-table td {
  padding: 8px 10px;
  font-size: var(--cqc-font-sm, 0.875rem);
}
```

c) Add responsive rules inside the existing `@media (max-width: 480px)` block:

```css
/* Inside @media (max-width: 480px) */
.cqc-table thead th {
  padding: 6px 8px;
  font-size: var(--cqc-font-xs, 0.75rem);
}
.cqc-table td {
  padding: 6px 8px;
  font-size: var(--cqc-font-xs, 0.75rem);
}
.cqc-table .cqc-col-checkbox {
  width: 32px;
}
```

This approach is CSS-only, requires no HTML template changes, works for ALL cqc-table instances across all extensions (ApprobationExtension, TableauBord, RecusExtension, etc.), and preserves border-radius clipping via overflow-y: hidden.
  </action>
  <verify>
    Open Fava in a browser, navigate to the Approbation tab, resize the window to be narrower than the table. Confirm the table scrolls horizontally instead of being clipped. Verify at full width there is no visual regression.
    Automated: grep -c "overflow-x: auto" src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js should return at least 1.
  </verify>
  <done>
    - cqc-card-flush allows horizontal scrolling via overflow-x: auto
    - Table padding and font sizes reduce at 768px and 480px breakpoints
    - No HTML template changes required
    - All cqc-table instances across all extensions benefit from the fix
  </done>
</task>

</tasks>

<verification>
1. Resize browser to ~800px wide -- ApprobationExtension table should show horizontal scrollbar
2. At full width -- table should look identical to before (no regression)
3. Check other extension pages (Tableau de bord, Recus, etc.) -- tables should also scroll if needed
4. Check dark mode -- no visual artifacts from overflow change
</verification>

<success_criteria>
- Table content is fully accessible at any viewport width via horizontal scroll
- No content clipping on non-fullscreen windows
- Visual appearance unchanged at full-width viewports
</success_criteria>

<output>
After completion, create `.planning/quick/18-make-approbationextension-table-responsi/18-SUMMARY.md`
</output>
