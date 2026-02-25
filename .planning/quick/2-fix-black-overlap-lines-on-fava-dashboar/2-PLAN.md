---
phase: quick-2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
autonomous: true
requirements:
  - QUICK-2-fix-tooltip-artifacts
must_haves:
  truths:
    - "No black/dark horizontal lines appear over table rows or amounts"
    - "Tooltip still appears correctly on hover"
    - "Tooltip disappears cleanly when cursor leaves the element"
  artifacts:
    - path: "src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js"
      provides: "Fixed tooltip CSS with visibility: hidden preventing paint artifacts"
      contains: "visibility: hidden"
  key_links:
    - from: "[data-tooltip]::after"
      to: "browser paint pipeline"
      via: "visibility: hidden + opacity: 0"
      pattern: "visibility:\\s*hidden"
---

<objective>
Fix black artifact lines appearing over Fava dashboard table records caused by tooltip pseudo-elements being painted by the browser despite opacity: 0.

Purpose: The dark background of [data-tooltip]::after (color #0A1628, near-black) is rendered by browsers even at opacity: 0 when CSS transitions and z-index are involved, creating visible dark bands over table rows and amounts. Adding visibility: hidden prevents the browser from painting the element entirely.

Output: Modified ThemeQCExtension.js where tooltip pseudo-elements use both opacity: 0 and visibility: hidden when not active, completely eliminating paint artifacts.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add visibility: hidden to tooltip CSS to prevent paint artifacts</name>
  <files>src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js</files>
  <action>
In the THEME_CSS string, locate the [data-tooltip]::after block (lines 979-1004) and the hover rules (lines 1005-1009).

Make these two changes:

1. In the [data-tooltip]::after block:
   - Add `visibility: hidden;` on the line after `opacity: 0;` (line 996)
   - Update the transition property from `transition: opacity 200ms ease;` to `transition: opacity 200ms ease, visibility 200ms ease;`

2. In the [data-tooltip]:hover::after, [data-tooltip]:focus-within::after, [data-tooltip]:focus::after block:
   - Add `visibility: visible;` on the line after `opacity: 1;` (line 1008)

The final [data-tooltip]::after block should have:
```
opacity: 0;
visibility: hidden;
pointer-events: none;
transition: opacity 200ms ease, visibility 200ms ease;
```

The final hover block should have:
```
opacity: 1;
visibility: visible;
```

Do NOT change any other CSS property. Do NOT touch JavaScript logic. Only these three line-level additions/modifications within the THEME_CSS template literal.
  </action>
  <verify>
    1. Run: grep -n "visibility" src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
       Expected: two matches — "visibility: hidden" in ::after block and "visibility: visible" in hover block.
    2. Run: grep -n "transition:" src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js | grep tooltip -A2
       Expected: transition includes both "opacity" and "visibility".
    3. Load the Fava dashboard in a browser and confirm no black lines appear over table rows or amounts before hovering any element.
  </verify>
  <done>
    - `visibility: hidden` present in [data-tooltip]::after block
    - `visibility: visible` present in hover/focus block
    - `transition` covers both opacity and visibility
    - No black artifact lines visible on dashboard table records
    - Tooltip still appears correctly on hover and fades out cleanly on mouse-leave
  </done>
</task>

</tasks>

<verification>
1. grep -n "visibility" src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js returns exactly two matches (hidden + visible).
2. No other sections of the file were modified (git diff shows only the tooltip CSS block).
3. Browser smoke test: table rows show no dark artifact lines at rest; tooltips appear and disappear smoothly on hover.
</verification>

<success_criteria>
The dark/black horizontal artifact lines over Fava dashboard table records are completely absent. Tooltip functionality (appear on hover, fade on leave) is unaffected. Change is confined to 3 lines within the THEME_CSS template literal.
</success_criteria>

<output>
After completion, create `.planning/quick/2-fix-black-overlap-lines-on-fava-dashboar/2-01-SUMMARY.md`
</output>
