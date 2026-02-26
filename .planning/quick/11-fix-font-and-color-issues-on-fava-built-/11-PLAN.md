---
phase: 11-fix-font-and-color-issues-on-fava-built
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
autonomous: false
requirements: [DARK-MODE-FIX, SIDEBAR-LIGHTEN, HEADER-FILTER-CONTRAST]

must_haves:
  truths:
    - "Fava built-in pages render correctly when browser is in dark mode (no color clashes)"
    - "Sidebar background is lighter navy blue, not near-black"
    - "Header filter boxes have clear white text on a distinct blue background"
  artifacts:
    - path: "src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js"
      provides: "Dark mode override, sidebar color fix, header filter styling"
      contains: "color-scheme: light"
  key_links:
    - from: "ThemeQCExtension.js THEME_CSS"
      to: "Fava :root variables"
      via: "CSS variable override on :root"
      pattern: "color-scheme:\\s*light"
---

<objective>
Fix three visual issues on Fava built-in pages: (1) dark mode compatibility by forcing light color scheme, (2) sidebar too dark, (3) header filter box contrast.

Purpose: Built-in Fava pages (editor, options, help, query, journal, trial_balance, balance_sheet, income_statement) currently break when the browser is in dark mode because the theme has no dark mode handling. The sidebar is near-black (#0A1628) and header filter inputs lack clear contrast.

Output: Updated ThemeQCExtension.js with all three fixes applied in the THEME_CSS template literal.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
</context>

<tasks>

<task type="auto">
  <name>Task 1: Force light color scheme and fix sidebar and header filter styling</name>
  <files>src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js</files>
  <action>
In the THEME_CSS template literal inside ThemeQCExtension.js, make three targeted CSS changes:

**1. Force light mode (prevent dark mode conflicts):**
Add `color-scheme: light;` to the existing `:root` block (line ~7, right after the opening `{`). This single declaration tells the browser to always render the page in light mode, preventing Fava's built-in dark mode variables from activating. This is the simplest and most robust approach -- no need for a large `@media (prefers-color-scheme: dark)` override block.

**2. Lighten the sidebar:**
Change `--qc-surface-sidebar` from `#0A1628` (near-black) to `#122B52` (dark navy blue that is visibly lighter while still being clearly dark). This variable is already referenced by `--sidebar-background` on line ~60, so no other changes needed.

**3. Improve header filter box styling:**
Replace the current `header input, header select` rule block (lines ~152-162) with:
```css
header input, header select {
  border-radius: var(--qc-radius-sm);
  border: 1px solid rgba(255,255,255,0.25);
  background: rgba(26, 91, 191, 0.9);
  color: white;
  transition: all var(--qc-transition);
  font-family: 'Inter', sans-serif;
  font-size: var(--cqc-font-sm);
}
```
Key changes: Use `rgba(26, 91, 191, 0.9)` (based on --qc-blue-light #1A5BBF) as a single solid-ish background instead of the dual background/background-color conflict. Remove backdrop-filter (unnecessary with an opaque-ish background). Slightly more visible border at 0.25 opacity. Add font-size token for consistency.

Also update the focus state (lines ~164-169):
```css
header input:focus, header select:focus {
  background: rgba(26, 91, 191, 1);
  border-color: rgba(255,255,255,0.5);
  outline: none;
  box-shadow: 0 0 0 3px rgba(255,255,255,0.15);
}
```

Leave the `header input::placeholder` rule unchanged.

Do NOT add any `@media (prefers-color-scheme: dark)` block -- `color-scheme: light` handles everything.
  </action>
  <verify>
Run: `grep -n "color-scheme: light" src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` -- should find the declaration.
Run: `grep -n "#122B52" src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` -- should find the new sidebar color.
Run: `grep -n "26, 91, 191" src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` -- should find the new filter box background.
  </verify>
  <done>
The three CSS fixes are applied: (1) color-scheme: light on :root forces light mode rendering on all Fava pages, (2) sidebar uses #122B52 instead of #0A1628, (3) header filter boxes use rgba(26, 91, 191, 0.9) with clean single-background approach and visible white text.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Visual verification of dark mode, sidebar, and header filters</name>
  <files>src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js</files>
  <action>User visually verifies the three CSS fixes in browser.</action>
  <verify>User confirms visual correctness.</verify>
  <done>All three visual issues resolved and approved by user.</done>
  <what-built>Dark mode override via color-scheme: light, lighter sidebar (#122B52), and improved header filter box contrast (rgba blue background)</what-built>
  <how-to-verify>
    1. Open Fava in a browser with dark mode enabled (System Preferences > Appearance > Dark on macOS)
    2. Navigate to built-in pages: editor, options, help, query, journal, trial_balance, balance_sheet, income_statement
    3. Verify: All pages render with light backgrounds and correct colors (no dark mode color clashes)
    4. Check sidebar: Should be dark navy blue (#122B52), noticeably lighter than the previous near-black
    5. Check header filter boxes (Periode, Compte, Filtrer par etiquette): Should show white text on a clear blue background
    6. Toggle browser back to light mode and verify everything still looks correct
  </how-to-verify>
  <resume-signal>Type "approved" or describe any remaining visual issues</resume-signal>
</task>

</tasks>

<verification>
- `color-scheme: light` present in :root block
- `--qc-surface-sidebar: #122B52` replaces old `#0A1628`
- Header filter inputs use single `rgba(26, 91, 191, 0.9)` background
- No JavaScript errors in browser console
- All Fava built-in pages render correctly in both light and dark browser modes
</verification>

<success_criteria>
Fava built-in pages display consistently regardless of browser dark/light mode setting. Sidebar is visibly lighter navy. Header filter boxes have clear white-on-blue contrast.
</success_criteria>

<output>
After completion, create `.planning/quick/11-fix-font-and-color-issues-on-fava-built-/11-SUMMARY.md`
</output>
