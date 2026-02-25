---
phase: quick-7
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
autonomous: true
requirements: []

must_haves:
  truths:
    - "Inter font loads reliably on every page navigation in Fava"
    - "All Fava UI elements (Svelte components, journal entries, metadata, flex-table, native tables) render in Inter"
    - "No @import inside dynamically injected style tags"
  artifacts:
    - path: "src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js"
      provides: "Font loading via link element + broadened font-family selectors"
      contains: "createElement.*link"
  key_links:
    - from: "injectStyle()"
      to: "document.head"
      via: "link element for Google Fonts + style element for CSS"
      pattern: "link.*stylesheet.*fonts.googleapis"
---

<objective>
Fix Inter font not loading across the Fava UI by replacing the unreliable `@import url()` inside a dynamically injected `<style>` tag with a proper `<link rel="stylesheet">` element, and broaden the font-family CSS selectors to cover ALL Fava elements including Svelte components.

Purpose: The current approach of using `@import` inside a dynamically created `<style>` element is unreliable -- browsers may not process it, and `@import` must be the first rule which is not guaranteed with dynamic injection. This causes Inter to never load, making all `font-family: 'Inter'` declarations fall back to system fonts.

Output: Updated ThemeQCExtension.js with reliable font loading and comprehensive font coverage.
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
  <name>Task 1: Replace @import with link element and broaden font-family selectors</name>
  <files>src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js</files>
  <action>
  Two changes to the ThemeQCExtension.js file:

  1. **Remove @import from THEME_CSS string:**
     Delete line 7: `@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');`
     from the THEME_CSS template literal.

  2. **Inject a link element in injectStyle():**
     In the `injectStyle()` function, BEFORE creating/appending the `<style>` element, create and inject a `<link>` element:
     ```js
     // Inject Google Fonts via <link> (not @import — @import inside dynamic <style> is unreliable)
     if (!document.getElementById("cqc-font-link")) {
       const link = document.createElement("link");
       link.id = "cqc-font-link";
       link.rel = "stylesheet";
       link.href = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap";
       document.head.appendChild(link);
     }
     ```

  3. **Broaden the font-family CSS selector:**
     The current "Global Reset" selector only targets `body, article, aside, header`. Fava's Svelte components, journal entries, metadata fields, form elements, and flex-table items are NOT covered. Replace the existing global reset block:
     ```css
     /* ===== Global Reset ===== */
     body, article, aside, header {
       font-family: 'Inter', -apple-system, ...
     ```
     with a broader selector that catches all Fava elements:
     ```css
     /* ===== Global Reset ===== */
     body, article, aside, header,
     .flex-table, .flex-table span, .flex-table a, .flex-table p,
     ol, ul, li, p, span, div,
     table, th, td, tr,
     input, select, textarea, button,
     label, legend, fieldset,
     h1, h2, h3, h4, h5, h6 {
       font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
       -webkit-font-smoothing: antialiased;
       -moz-osx-font-smoothing: grayscale;
     }
     ```
     This ensures Inter cascades to Svelte scoped components, journal entry rows, metadata fields, and all native HTML elements that Fava renders.
  </action>
  <verify>
  1. Grep ThemeQCExtension.js for `@import` -- should return NO matches
  2. Grep ThemeQCExtension.js for `cqc-font-link` -- should find the link element creation
  3. Grep ThemeQCExtension.js for `flex-table` in the global reset selector -- should confirm broadened coverage
  4. Start Fava and visually inspect: open DevTools Network tab, filter by "font" -- Inter woff2 files should load. Inspect any element -- computed font should show "Inter".
  </verify>
  <done>
  - No @import inside THEME_CSS string
  - injectStyle() creates a link element with id="cqc-font-link" pointing to Google Fonts before creating the style element
  - Global font-family reset covers all common HTML elements including Svelte-rendered content
  - Inter font loads reliably on every Fava page
  </done>
</task>

</tasks>

<verification>
- `grep -c "@import" src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` returns 0
- `grep -c "cqc-font-link" src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` returns at least 2 (id check + creation)
- File parses as valid JavaScript (no syntax errors)
</verification>

<success_criteria>
Inter font loads on every Fava page via a proper link element. All UI text (headers, tables, sidebar, Svelte flex-tables, journal entries, form inputs) renders in Inter, not system fallback fonts.
</success_criteria>

<output>
After completion, create `.planning/quick/7-fix-font-issues-across-the-whole-fava-ui/7-SUMMARY.md`
</output>
