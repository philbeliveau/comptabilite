# Phase 9: Receipt Upload UX - Research

**Researched:** 2026-02-25
**Domain:** AJAX file upload, drag-and-drop UI, progress tracking, file preview in Fava extension context
**Confidence:** HIGH

## Summary

Phase 9 converts the current receipt upload from a full-page-reload HTML form to a modern AJAX-based upload experience within the existing Fava extension architecture. The current `RecusExtension.upload()` endpoint returns raw HTML strings; it must be converted to return JSON via Flask's `jsonify()`. The Fava `extension_endpoint` dispatcher uses `fava_app.make_response(response)`, which natively handles Flask Response objects including jsonify output -- no framework changes needed.

The frontend work is pure vanilla JavaScript using `XMLHttpRequest` (for progress events) or `fetch` (simpler but no upload progress). XHR is required for RCPT-02 (real progress bar) since `fetch()` does not expose upload progress events. The drag-and-drop zone already exists with basic inline handlers; it needs to be converted to proper JS event listeners with animation states, multi-file support, and thumbnail rendering post-upload.

**Primary recommendation:** Use `XMLHttpRequest` with `upload.onprogress` for real percentage tracking, `flask.jsonify` for the JSON endpoint, inline `<script>` blocks in the Jinja template (matching existing extension patterns like ApprobationExtension), and CSS animations using the existing `--qc-*` design token system.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RCPT-01 | Upload endpoint converted from raw HTML to AJAX/JSON response | Fava's `make_response()` accepts `flask.jsonify()` return values. Current endpoint returns HTML strings; convert to return `jsonify({"status": "ok", "filename": ..., "extracted": ...})`. Frontend uses XHR with `responseType = 'json'`. |
| RCPT-02 | Animated progress bar with real percentage during upload | `XMLHttpRequest.upload.onprogress` provides `event.loaded` / `event.total` for real progress. `fetch()` cannot do this. CSS width transition on a progress bar element gives smooth animation. |
| RCPT-03 | Thumbnail preview after upload (image scaled, PDF shows icon) | For images: use `URL.createObjectURL(file)` on the client-side File object (no server round-trip needed). For PDFs: render a document icon with the filename. Server returns `file_type` in JSON so frontend knows which preview to show. |
| RCPT-04 | Drag-and-drop with animated border, hover glow, multi-file support | Existing `.cqc-dropzone` CSS has hover/dragover states. Add `dragenter`/`dragleave` counter pattern (to handle child element events), CSS keyframe animation for border, and loop over `event.dataTransfer.files` for multi-file. Remove inline `on*` handlers; use `addEventListener`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask `jsonify` | (bundled with Fava 1.30.12) | JSON response from extension endpoint | Already available, zero dependencies. `make_response()` handles it natively. |
| XMLHttpRequest | Browser native | File upload with progress events | Only browser API that exposes `upload.onprogress` for real percentage tracking. `fetch()` cannot do this. |
| CSS Custom Properties | `--qc-*` tokens | Animation styling | Already defined in ThemeQCExtension.js; reuse for consistency. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `URL.createObjectURL()` | Browser native | Client-side image preview | Generate thumbnail from File object without server round-trip. |
| `FileReader` | Browser native | Alternative preview method | Only if `createObjectURL` is insufficient (it won't be for this use case). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| XHR | `fetch()` | Simpler API but NO upload progress events -- fails RCPT-02. Use XHR. |
| XHR | Libraries like Dropzone.js, Uppy | Overkill for single extension; adds CDN dependency. Vanilla XHR is ~40 lines. |
| Inline `<script>` | Separate `.js` module via `has_js_module` | Would require setting `has_js_module = True` on RecusExtension and creating a top-level JS file. Overkill -- the upload logic is page-specific, not global. Inline script in template matches existing patterns (ApprobationExtension uses inline `<script>`). |
| `URL.createObjectURL` | Server-side thumbnail generation | Adds server complexity, latency. Client-side is instant for images. |

**Installation:** No packages to install. Everything uses browser-native APIs and Flask builtins already present in Fava.

## Architecture Patterns

### Recommended File Structure
```
src/compteqc/fava_ext/recus/
  __init__.py              # RecusExtension with JSON upload endpoint
  templates/
    RecusExtension.html    # Template with inline JS for upload UX
```

No new files needed. Both existing files are modified in place.

### Pattern 1: JSON Extension Endpoint
**What:** Convert Fava extension endpoint from HTML string return to `flask.jsonify()` return.
**When to use:** Any extension endpoint that needs to serve AJAX requests.
**Example:**
```python
# Source: Fava 1.30.12 application.py line 358-364
# make_response() handles jsonify() natively

from flask import jsonify, request

@extension_endpoint("upload", ["POST"])
def upload(self):
    fichier = request.files.get("fichier")
    if not fichier or not fichier.filename:
        return jsonify({"status": "error", "message": "Aucun fichier"}), 400

    # ... process file ...

    return jsonify({
        "status": "ok",
        "filename": fichier.filename,
        "file_type": "image" or "pdf",
        "extracted": {...} or None,
    })
```

### Pattern 2: XHR Upload with Progress
**What:** Use XMLHttpRequest to POST a FormData object with real-time progress tracking.
**When to use:** When you need `upload.onprogress` events (percentage-based progress bar).
**Example:**
```javascript
// Browser-native XHR upload with progress
function uploadFile(file, url) {
  const formData = new FormData();
  formData.append('fichier', file);

  const xhr = new XMLHttpRequest();

  xhr.upload.onprogress = function(e) {
    if (e.lengthComputable) {
      const pct = Math.round((e.loaded / e.total) * 100);
      updateProgressBar(pct);
    }
  };

  xhr.onload = function() {
    if (xhr.status === 200) {
      const data = JSON.parse(xhr.responseText);
      showPreview(file, data);
    }
  };

  xhr.open('POST', url);
  xhr.send(formData);
}
```

### Pattern 3: Drag-and-Drop with Counter
**What:** Use a counter to track nested dragenter/dragleave events (child elements fire extra events).
**When to use:** Any drag-and-drop zone with child elements.
**Example:**
```javascript
// Counter pattern prevents flicker from child element events
let dragCounter = 0;

dropzone.addEventListener('dragenter', (e) => {
  e.preventDefault();
  dragCounter++;
  dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', (e) => {
  e.preventDefault();
  dragCounter--;
  if (dragCounter === 0) {
    dropzone.classList.remove('dragover');
  }
});

dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dragCounter = 0;
  dropzone.classList.remove('dragover');
  const files = Array.from(e.dataTransfer.files);
  files.forEach(f => uploadFile(f, uploadUrl));
});
```

### Pattern 4: Client-Side File Preview
**What:** Generate image thumbnails from File objects without server round-trip.
**When to use:** After selecting or dropping files, before or alongside upload.
**Example:**
```javascript
function renderPreview(file) {
  const container = document.createElement('div');
  container.className = 'cqc-preview-item';

  if (file.type.startsWith('image/')) {
    const img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    img.onload = () => URL.revokeObjectURL(img.src);
    img.className = 'cqc-preview-thumb';
    container.appendChild(img);
  } else {
    // PDF or other: show icon + filename
    container.innerHTML = `
      <span class="cqc-preview-icon">&#128196;</span>
      <span class="cqc-preview-name">${file.name}</span>
    `;
  }
  return container;
}
```

### Anti-Patterns to Avoid
- **Fake/indeterminate progress bar:** RCPT-02 explicitly requires real percentage. Never use CSS animation-only progress bars. Always use `xhr.upload.onprogress`.
- **`fetch()` for upload progress:** `fetch()` does not support upload progress events. There is no `onprogress` equivalent for request body. Use XHR.
- **Inline `on*` handlers in HTML attributes:** The current template uses `ondragover`, `ondragleave`, `ondrop` inline. These should be replaced with `addEventListener` for maintainability and to support the counter pattern.
- **Full page reloads after upload:** The current form does `submit()` which causes navigation. Replace with XHR to stay on the page.
- **Forgetting to revoke object URLs:** `URL.createObjectURL()` creates a blob URL that leaks memory. Always call `URL.revokeObjectURL()` after the image loads.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Upload progress tracking | Custom progress estimation | `xhr.upload.onprogress` | Browser gives you real byte-level progress for free |
| Image thumbnails | Server-side resize + return | `URL.createObjectURL(file)` | Instant, zero latency, zero server load |
| Drag-and-drop | Custom drag event system | Native HTML5 drag events + counter pattern | Well-understood, zero dependencies |
| JSON responses in Fava | Custom Response building | `flask.jsonify()` | Already available, handles content-type and serialization |
| CSS animations | Animation library (GSAP etc.) | CSS `@keyframes` + `transition` | Project decision: pure CSS + no animation libraries |

**Key insight:** Every piece of this phase uses browser-native or Flask-built-in capabilities. Zero external dependencies needed.

## Common Pitfalls

### Pitfall 1: Drag Events Fire on Child Elements
**What goes wrong:** Dragging over child elements inside the dropzone triggers `dragleave` on the parent, causing the visual state to flicker.
**Why it happens:** Each child element fires its own `dragenter`/`dragleave` events that bubble up.
**How to avoid:** Use the counter pattern (increment on `dragenter`, decrement on `dragleave`, only remove class when counter reaches 0).
**Warning signs:** Dropzone border/glow flickers when dragging over text or icon inside it.

### Pitfall 2: FormData File Field Name Mismatch
**What goes wrong:** Server returns "Aucun fichier" even though file was sent.
**Why it happens:** The FormData field name in JS (`formData.append('fichier', file)`) must exactly match `request.files.get("fichier")` in the Python endpoint.
**How to avoid:** Use the same field name constant. Current endpoint uses `"fichier"`.
**Warning signs:** XHR returns 200 but response says no file.

### Pitfall 3: HEIC Files Not Previewable in Browser
**What goes wrong:** HEIC files (from iPhone) cannot be displayed as image thumbnails.
**Why it happens:** Most browsers do not support HEIC format natively. Safari on macOS does, but Chrome/Firefox do not.
**How to avoid:** For HEIC files, treat them like PDFs -- show an icon + filename instead of trying to render a thumbnail. The accept attribute already includes `.heic`.
**Warning signs:** Broken image icon in preview area.

### Pitfall 4: Multiple File Upload Serialization
**What goes wrong:** When uploading multiple files, all uploads fire simultaneously and may overload or confuse the server.
**Why it happens:** Looping over files and calling XHR for each creates parallel requests.
**How to avoid:** Upload files sequentially (chain uploads, start next after previous completes) or accept that Fava's single-threaded dev server handles one at a time anyway. Sequential is safer and gives better per-file progress UX.
**Warning signs:** Progress bars jump erratically, server returns errors on concurrent writes.

### Pitfall 5: Progress Bar Stuck at 100% Before Server Processing
**What goes wrong:** Upload progress reaches 100% but server is still processing (AI extraction can take seconds).
**Why it happens:** `upload.onprogress` tracks bytes sent to server, not server processing time.
**How to avoid:** Show "Traitement en cours..." spinner/state after progress reaches 100% but before `xhr.onload` fires. Two visual states: uploading (progress bar) and processing (spinner).
**Warning signs:** User thinks upload is frozen after bar fills.

### Pitfall 6: Current Endpoint Returns HTML for Errors
**What goes wrong:** AJAX request gets HTML error response instead of JSON.
**Why it happens:** If the endpoint has error paths that still return HTML strings.
**How to avoid:** Convert ALL return paths to JSON, including error cases. Return `jsonify({"status": "error", "message": ...}), 400`.
**Warning signs:** `JSON.parse()` throws on error responses.

## Code Examples

### Converting Current Upload Endpoint to JSON
```python
# Current: returns raw HTML strings
# New: returns flask.jsonify()

from flask import jsonify, request

@extension_endpoint("upload", ["POST"])
def upload(self):
    fichier = request.files.get("fichier")

    if not fichier or not fichier.filename:
        return jsonify({"status": "error", "message": "Aucun fichier selectionne."}), 400

    # ... save file, run extraction ...

    # Determine file type for frontend preview
    ext = Path(fichier.filename).suffix.lower()
    file_type = "image" if ext in {".jpg", ".jpeg", ".png"} else "pdf" if ext == ".pdf" else "other"

    result = {
        "status": "ok",
        "filename": fichier.filename,
        "file_type": file_type,
    }

    if extracted_data:
        result["extracted"] = {
            "fournisseur": extracted_data.fournisseur,
            "date": extracted_data.date,
            "total": str(extracted_data.total),
            "confiance": extracted_data.confiance,
        }

    return jsonify(result)
```

### Progress Bar HTML + CSS
```html
<!-- Inside RecusExtension.html template -->
<div id="upload-progress" class="cqc-progress" style="display: none;">
  <div class="cqc-progress-bar" id="progress-bar">
    <span class="cqc-progress-text" id="progress-text">0%</span>
  </div>
</div>

<style>
.cqc-progress {
  width: 100%;
  height: 28px;
  background: var(--qc-surface);
  border-radius: var(--qc-radius-sm);
  overflow: hidden;
  margin: 16px 0;
  border: 1px solid var(--qc-border);
}
.cqc-progress-bar {
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, var(--qc-blue), var(--qc-blue-light));
  border-radius: var(--qc-radius-sm);
  transition: width 150ms ease-out;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cqc-progress-text {
  color: var(--qc-white);
  font-size: var(--cqc-font-sm, 0.875rem);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
</style>
```

### Animated Dropzone Border (CSS Keyframes)
```css
@keyframes cqc-border-pulse {
  0%, 100% { border-color: var(--qc-blue); }
  50% { border-color: var(--qc-blue-light); }
}

.cqc-dropzone.dragover {
  animation: cqc-border-pulse 1.2s ease-in-out infinite;
  border-style: solid;
  box-shadow: 0 0 16px rgba(0, 61, 165, 0.15);
}

@media (prefers-reduced-motion: reduce) {
  .cqc-dropzone.dragover {
    animation: none;
  }
}
```

### Multi-File Sequential Upload
```javascript
async function uploadFiles(files, url) {
  for (let i = 0; i < files.length; i++) {
    showFileStatus(files[i], 'uploading', i, files.length);
    await uploadSingleFile(files[i], url);
  }
}

function uploadSingleFile(file, url) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('fichier', file);

    const xhr = new XMLHttpRequest();

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        updateProgressBar(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status === 200) {
        const data = JSON.parse(xhr.responseText);
        showPreview(file, data);
        resolve(data);
      } else {
        reject(new Error('Upload failed'));
      }
    };

    xhr.onerror = () => reject(new Error('Network error'));

    xhr.open('POST', url);
    xhr.send(formData);
  });
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Form submit with page reload | XHR/fetch AJAX upload | Standard since ~2015 | No page navigation, inline feedback |
| Server-side thumbnail generation | `URL.createObjectURL()` client-side | Supported since ~2014 | Zero server load for previews |
| jQuery $.ajax for uploads | Vanilla XHR or fetch | jQuery usage declined ~2020 | No dependency needed |
| `ondragover` inline handlers | `addEventListener` with counter pattern | Best practice since ~2018 | Fixes child-element flicker bug |

**Deprecated/outdated:**
- `FileReader.readAsDataURL()` for image preview: Still works but `URL.createObjectURL()` is simpler and more memory-efficient. Use createObjectURL.
- jQuery file upload plugins: Unnecessary with modern vanilla JS. Project has no jQuery dependency.

## Open Questions

1. **Should multi-file upload send files in a single request or sequential requests?**
   - What we know: Current endpoint accepts a single file (`request.files.get("fichier")`). Each file goes through AI extraction which can take seconds.
   - What's unclear: Whether to modify the endpoint to accept multiple files at once.
   - Recommendation: Keep single-file endpoint, upload sequentially from frontend. Simpler, better per-file progress, and AI extraction is inherently sequential. Show per-file status.

2. **Should extraction results (AI) be shown inline or deferred?**
   - What we know: Current flow runs extraction synchronously during upload. This can take 2-5 seconds for AI processing.
   - What's unclear: Whether to show extraction results in the upload response or make it a separate step.
   - Recommendation: Keep synchronous for now (matches existing behavior). The progress bar handles the upload portion; a "Traitement..." spinner handles the extraction wait. This keeps the UX simple.

3. **Match proposal UI after AJAX upload**
   - What we know: Current endpoint returns HTML with a match table and "Lier" buttons. Converting to JSON means the match UI needs to be rendered client-side or handled differently.
   - What's unclear: How to handle the match/link workflow in the new AJAX flow.
   - Recommendation: Return match data as JSON array in the upload response. Render match cards client-side with the same "Lier" action (still a form POST to /link, which can remain as-is since it redirects). This is the most significant architectural change in the phase.

## Sources

### Primary (HIGH confidence)
- Fava 1.30.12 source code: `fava/ext/__init__.py` -- extension_endpoint decorator, FavaExtensionBase class
- Fava 1.30.12 source code: `fava/application.py` lines 349-364 -- extension endpoint dispatch, `make_response()` handling
- Existing codebase: `src/compteqc/fava_ext/recus/__init__.py` -- current upload endpoint implementation
- Existing codebase: `src/compteqc/fava_ext/recus/templates/RecusExtension.html` -- current template with inline drag-and-drop
- Existing codebase: `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` -- CSS variable system, dropzone styles
- Existing codebase: `src/compteqc/documents/extraction.py` -- DonneesRecu model, AI extraction pipeline

### Secondary (MEDIUM confidence)
- MDN Web API: XMLHttpRequest.upload.onprogress -- standard browser API, well-documented
- MDN Web API: URL.createObjectURL() -- standard browser API for blob URLs
- MDN Web API: HTML Drag and Drop API -- dragenter/dragleave/drop events

### Tertiary (LOW confidence)
- None. All findings verified against codebase or official browser APIs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all browser-native APIs and Flask builtins, verified against Fava source
- Architecture: HIGH -- extension endpoint pattern verified in Fava source, existing inline JS pattern confirmed in ApprobationExtension
- Pitfalls: HIGH -- drag-and-drop counter pattern, XHR vs fetch limitation, and HEIC preview issue are well-known and verified

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable browser APIs, Fava 1.30.x unlikely to change extension dispatch)
