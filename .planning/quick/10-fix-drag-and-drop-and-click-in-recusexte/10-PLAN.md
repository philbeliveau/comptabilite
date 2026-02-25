---
phase: quick-10
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/fava_ext/recus/templates/RecusExtension.html
autonomous: true
requirements: [QUICK-10]
must_haves:
  truths:
    - "Clicking the dropzone opens the file picker in Fava SPA navigation"
    - "Dragging a file over the dropzone shows visual dragover feedback"
    - "Dropping a file onto the dropzone submits the upload form"
    - "Selecting a file via the file picker submits the upload form"
  artifacts:
    - path: "src/compteqc/fava_ext/recus/templates/RecusExtension.html"
      provides: "Working drag-and-drop and click upload via inline event attributes"
      contains: "onclick"
  key_links:
    - from: "dropzone div onclick"
      to: "fichier-input click()"
      via: "inline onclick attribute"
      pattern: "onclick="
    - from: "fichier-input onchange"
      to: "form.submit()"
      via: "inline onchange attribute"
      pattern: "onchange="
---

<objective>
Fix broken drag-and-drop and click handlers on the RecusExtension upload page.

Purpose: Fava is a Svelte SPA that injects extension HTML via innerHTML. Browsers do not execute `<script>` tags inserted via innerHTML, so the current event listeners never attach. Replacing the `<script>` block with inline event attributes (`onclick`, `ondragover`, `ondragleave`, `ondrop`, `onchange`) fixes this because inline attributes DO execute in dynamically injected HTML.

Output: Working file upload via both click and drag-and-drop in the Fava extension page.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/compteqc/fava_ext/recus/templates/RecusExtension.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace script block with inline event attributes</name>
  <files>src/compteqc/fava_ext/recus/templates/RecusExtension.html</files>
  <action>
Remove the entire `<script>...</script>` block (lines 68-107).

Replace the dropzone div (line 21) with inline event attributes:

```html
<div id="dropzone" class="cqc-dropzone"
     onclick="document.getElementById('fichier-input').click()"
     ondragover="event.preventDefault(); event.stopPropagation(); this.classList.add('dragover')"
     ondragleave="event.preventDefault(); event.stopPropagation(); this.classList.remove('dragover')"
     ondrop="event.preventDefault(); event.stopPropagation(); this.classList.remove('dragover'); if(event.dataTransfer.files.length > 0){ document.getElementById('fichier-input').files = event.dataTransfer.files; document.getElementById('upload-form').submit(); }">
```

Replace the file input (line 29-31) to add an onchange attribute:

```html
<input type="file" id="fichier-input" name="fichier"
       accept=".pdf,.jpg,.jpeg,.png,.heic"
       style="display: none;"
       onchange="if(this.files.length > 0){ document.getElementById('upload-form').submit(); }">
```

Verify there is NO remaining `<script>` tag in the file after editing.
  </action>
  <verify>
1. `grep -c '<script>' src/compteqc/fava_ext/recus/templates/RecusExtension.html` returns 0
2. `grep -c 'onclick' src/compteqc/fava_ext/recus/templates/RecusExtension.html` returns 1
3. `grep -c 'ondrop' src/compteqc/fava_ext/recus/templates/RecusExtension.html` returns 1
4. `grep -c 'onchange' src/compteqc/fava_ext/recus/templates/RecusExtension.html` returns 1
  </verify>
  <done>
The RecusExtension.html template uses only inline event attributes (no script block). All five handlers are present: onclick (click to select), ondragover (visual feedback), ondragleave (remove feedback), ondrop (handle dropped files and submit), onchange (submit after file picker selection).
  </done>
</task>

</tasks>

<verification>
- No `<script>` tags remain in RecusExtension.html
- All 5 inline event handlers present: onclick, ondragover, ondragleave, ondrop, onchange
- HTML is valid (no unclosed tags or attribute syntax errors)
- Form action URL pattern preserved unchanged
</verification>

<success_criteria>
- Clicking the dropzone triggers the file input dialog (via inline onclick)
- Drag-and-drop provides visual feedback and submits files (via inline ondragover/ondragleave/ondrop)
- File picker selection auto-submits (via inline onchange)
- No JavaScript script blocks in the template
</success_criteria>

<output>
After completion, create `.planning/quick/10-fix-drag-and-drop-and-click-in-recusexte/10-SUMMARY.md`
</output>
