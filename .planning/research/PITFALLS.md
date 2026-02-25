# Domain Pitfalls: Production UI/UX on Fava Extension System

**Domain:** Adding fintech-polished UI/UX to an existing Fava/Beancount extension system
**Researched:** 2026-02-25
**Confidence:** HIGH (verified against Fava source code, existing CompteQC codebase, and official documentation)

---

## Critical Pitfalls

Mistakes that cause rewrites, memory leaks, or broken UX across the application.

### Pitfall 1: Chart.js Instances Never Destroyed on Fava SPA Navigation

**What goes wrong:** Chart.js chart instances accumulate in memory because Fava has no `onExtensionPageUnload` or cleanup callback. When a user navigates away from a dashboard page and returns, a new Chart instance is created on the same canvas (or a new canvas), but the old instance is never `.destroy()`'d. After 10-20 navigations, the browser consumes hundreds of MB and event listeners pile up, causing sluggish interactions and eventual tab crash.

**Why it happens:** Fava implements SPA-like navigation by intercepting link clicks and replacing the `<article>` innerHTML asynchronously. The extension JS module only has three callbacks: `init()`, `onPageLoad()`, and `onExtensionPageLoad()`. There is no `onPageUnload` or `onExtensionPageUnload` -- verified by inspecting the Fava source code (`/fava/ext/__init__.py`) and the official help documentation. When `<article>` innerHTML is replaced, the canvas DOM element is garbage collected, but the Chart.js instance (stored in a module-scope variable) retains references to the canvas, its 2D context, event listeners, and all data arrays.

**Consequences:**
- Memory leak grows linearly with each navigation cycle
- Canvas event listeners accumulate (mousemove, click, resize)
- Browser tab becomes unresponsive after extended use sessions
- Tooltip artifacts may appear from orphaned chart instances

**Prevention:**
1. Store all Chart.js instances in a module-level registry (e.g., `Map<string, Chart>`)
2. At the TOP of every `onPageLoad()` call, iterate the registry and call `.destroy()` on each instance, then clear the map
3. After destroying, also call `canvas.getContext('2d').clearRect()` to clean visual remnants
4. Use a helper function: `ensureChart(canvasId, config)` that destroys any existing chart on that canvas before creating a new one

**Detection:**
- Chrome DevTools Memory tab: take heap snapshots before/after 5 navigations; search for "Chart" objects
- Performance Monitor: watch JS heap size during navigation -- it should stay flat, not grow
- `Chart.instances` (Chart.js 4.x) or `Chart.getChart(canvas)` -- if this returns a chart on a canvas you are about to create, you have a leak

**Confidence:** HIGH -- verified no cleanup callback exists in Fava source; Chart.js memory leak pattern is well-documented in GitHub issues (#462, #7931, #11299).

---

### Pitfall 2: `!important` Escalation War with Fava's CSS

**What goes wrong:** The current ThemeQCExtension.js already contains 91 `!important` declarations, while Fava's own `app.css` contains zero. As production UI polish adds more style overrides, every new rule that conflicts with a previous `!important` rule also needs `!important`, creating an unwinnable specificity arms race. Eventually, debugging why a style is not applying becomes impossible without DevTools, and any Fava version upgrade that changes selectors breaks the entire theme.

**Why it happens:** Fava's CSS uses CSS custom properties (variables) on `:root` as the primary theming mechanism (e.g., `--header-background`, `--sidebar-background`, `--link-color`, `--button-background`). The intended override path is simply redefining these variables. However, when extension CSS uses element selectors like `header { background: ... !important; }`, it bypasses the variable system entirely and creates a hard dependency on Fava's exact DOM structure. When Fava (built with Svelte) changes its component output, the selectors break silently.

**Consequences:**
- Fava upgrades break theme silently (selectors no longer match new DOM)
- New UI features require increasingly specific selectors to override prior `!important` rules
- Dark mode or print stylesheets become impossible to implement (everything is `!important`)
- Debugging CSS takes 10x longer than necessary

**Prevention:**
1. **Phase 1: Audit** -- Catalog all 91 `!important` uses; for each one, determine if it can be replaced by overriding the corresponding Fava CSS variable on `:root`
2. **Use Fava's variable system first:** Override `--header-background`, `--sidebar-background`, `--link-color`, `--text-color`, `--border`, `--button-background`, `--button-color`, `--background`, etc. in `:root` -- this is the intended extension mechanism
3. **For styles with no Fava variable:** Use `.compteqc-` prefixed class selectors with one level of nesting (e.g., `.compteqc-dashboard .kpi-card`) instead of element selectors with `!important`
4. **Reserve `!important` for**: only overriding Svelte-scoped inline styles that Fava components inject at runtime (these are genuinely impossible to override otherwise)
5. **Test after Fava upgrades:** Pin Fava version in requirements and test theme after any upgrade

**Detection:**
- `grep -c '!important'` on all CSS/JS files -- track this count; it should decrease, not grow
- DevTools "Computed" tab: any property showing a crossed-out value from your own stylesheet means you are fighting yourself

**Confidence:** HIGH -- verified Fava's app.css has 0 `!important` and 40+ CSS custom properties; CompteQC theme has 91 `!important`. The contrast is stark.

---

### Pitfall 3: DOM Mutations Lost on Fava SPA Navigation

**What goes wrong:** Custom DOM elements injected into Fava's `<article>` area (dashboard cards, KPI widgets, Chart.js canvases, report headers) vanish when the user navigates to another page and back. Injections into persistent DOM regions (sidebar, header) may be duplicated on each navigation.

**Why it happens:** Fava's SPA navigation replaces the entire `<article>` innerHTML when loading a new page. The existing ThemeQCExtension.js already handles some of this correctly (using `onPageLoad()` to re-inject), but it uses boolean flags (`styleInjected`, `brandInjected`) that create a subtle bug: if Fava replaces the DOM but the JS module scope persists (it does -- ES modules are cached), the flag says "already injected" but the DOM element is gone.

**Consequences:**
- Brand strip disappears after first navigation (if flag is not reset)
- Report intro blocks vanish (currently handled correctly with `.remove()` before re-inject)
- Sidebar reorganization runs once but not after Fava reloads sidebar content
- Dashboard charts show empty canvases or no canvases at all

**Prevention:**
1. **Never use boolean flags for DOM presence** -- always check `document.getElementById(...)` or `document.querySelector(...)` for the actual DOM element before deciding to skip injection
2. **The existing code partially does this** (`if (existing) { styleInjected = true; return; }`) but should be the ONLY check, not a combination of flag AND DOM check
3. **For `<article>` content:** Always re-inject on `onPageLoad()` and `onExtensionPageLoad()` without caching assumptions
4. **For persistent regions (header, sidebar):** Check DOM presence, not module-scope flags
5. **Avoid `aside.dataset.cqcGrouped = "true"` pattern** -- this data attribute is on the DOM, so it survives if Fava does not replace `<aside>`, but if Fava ever rebuilds the sidebar (e.g., on ledger reload), it breaks

**Detection:**
- Navigate between 3+ different pages rapidly, then return to dashboard -- all widgets should render
- Trigger a ledger file reload (save beancount file) -- sidebar should still show grouped navigation
- Open DevTools Console and check for "Cannot read properties of null" errors during navigation

**Confidence:** HIGH -- verified by reading ThemeQCExtension.js source code; the `brandInjected` flag pattern has this exact flaw.

---

## Moderate Pitfalls

### Pitfall 4: Animation Performance on Large Financial Tables

**What goes wrong:** CSS hover animations, row transitions, and count-up animations on tables with 500+ rows trigger layout recalculations (reflow) on every frame, causing visible jank. The browser must recalculate geometry for every visible row when any animated property triggers layout (e.g., `padding`, `margin`, `height`, `width`, `border-width`).

**Prevention:**
1. **Only animate compositor-friendly properties:** `transform`, `opacity`, and `filter` are GPU-accelerated and do not trigger reflow. Use `transform: scale()` instead of changing `font-size`; use `transform: translateX()` instead of `margin-left`
2. **Row hover effects:** Use `background-color` change (triggers repaint, not reflow) or `box-shadow` (also repaint-only). Avoid changing `padding` or `border-width` on hover
3. **KPI count-up animations:** Use `requestAnimationFrame` with a counter updating `textContent` -- this is a single text node change per frame, very cheap
4. **Apply `contain: content` on table rows** to isolate reflow scope -- the browser will not recalculate siblings when one row changes
5. **For tables with 1000+ rows:** Defer animation entirely. Apply `transition: none` via a class (e.g., `.cqc-large-table tr { transition: none }`) when row count exceeds a threshold
6. **will-change:** Only apply to elements that are actively animating; remove it after animation completes. Do not blanket-apply to all rows

**Detection:**
- Chrome DevTools Performance tab: record during scroll/hover on a large table; look for long "Recalculate Style" or "Layout" blocks exceeding 16ms
- Lighthouse Performance audit: check for "Avoid large layout shifts"

**Confidence:** HIGH -- MDN documentation and Smashing Magazine best practices confirm compositor-layer properties.

---

### Pitfall 5: CSS Injection Order and Flash of Unstyled Content (FOUC)

**What goes wrong:** The theme CSS is injected via JavaScript (`document.head.appendChild(style)`) in the `init()` callback. Between the initial page load and the moment `init()` fires, the user sees Fava's default blue/gray theme for a fraction of a second before CompteQC styles apply. This FOUC is jarring and makes the app feel unpolished -- the opposite of the goal.

**Why it happens:** Fava loads its own `app.css` synchronously in the HTML `<head>`, but extension JS modules are loaded asynchronously after the page structure renders. The Google Fonts `<link>` injection adds a second FOUC when Inter font loads and causes a font swap.

**Prevention:**
1. **For CSS variables (`:root`):** These take effect instantly and do not cause FOUC because they override computed values before first paint -- prioritize variable-based theming
2. **For the Google Fonts link:** Add `font-display: swap` (already in the Google Fonts URL via `&display=swap`) and include a system font fallback with similar metrics so the layout does not shift
3. **Consider preloading the font:** Inject a `<link rel="preload" as="font" ...>` at the same time as the stylesheet link
4. **Accept the constraint:** Within Fava's extension architecture, some FOUC is unavoidable. Minimize it by keeping the JS module small and fast, and by preferring CSS variable overrides over selector-based rules
5. **Do not add a loading overlay or spinner** to mask the FOUC -- this would be worse UX than the brief flash

**Detection:**
- Hard-refresh (Cmd+Shift+R) with "Disable cache" enabled and CPU throttling set to 4x slowdown
- Record a screen capture of page load -- any visible style jump indicates FOUC

**Confidence:** MEDIUM -- the FOUC is confirmed by the code architecture, but its severity depends on network conditions and may be imperceptible on localhost.

---

### Pitfall 6: File Upload UX Failures Without Proper Error Handling

**What goes wrong:** The current `RecusExtension` upload endpoint has no client-side validation. Users can upload 100MB PDFs (browser hangs), upload the same receipt twice (duplicate entries), or lose their work to a network timeout with no feedback. The response from a failed upload is an unstyled HTML page that breaks out of Fava's SPA layout entirely.

**Why it happens:** The upload endpoint returns raw HTML strings (`'<html><body>...'`) instead of JSON, bypasses Fava's template system, and performs a full page navigation via form POST. This breaks the SPA illusion and loses sidebar/header state.

**Consequences:**
- Large file uploads block the browser tab with no progress feedback
- Duplicate receipts create duplicate document directives in the beancount file
- Upload errors show a bare HTML page outside the Fava layout
- User loses their place in the app after every upload

**Prevention:**
1. **Client-side validation before upload:** Check file size (reject > 10MB with clear message), check file extension (only .pdf, .jpg, .jpeg, .png, .heic), check for duplicate filenames against recently uploaded list
2. **Use AJAX (fetch/XMLHttpRequest) for uploads** instead of form POST: this keeps the user in the SPA context and enables progress tracking via `XMLHttpRequest.upload.onprogress`
3. **Show progress bar:** Use the existing `.cqc-progress` / `.cqc-progress-bar` CSS classes from the theme
4. **Return JSON from endpoints:** Change upload/link endpoints to return JSON responses, render results client-side within the existing Fava article area
5. **Deduplicate:** Hash file content (SHA-256) before upload; if the hash matches an existing document, show a warning instead of creating a duplicate
6. **Graceful error handling:** On network failure, show an inline error message with a retry button, not a blank page

**Detection:**
- Test: upload a 50MB file -- should show a "file too large" error before upload begins
- Test: upload the same receipt twice -- should warn about duplicate
- Test: disconnect network during upload -- should show recoverable error inline

**Confidence:** HIGH -- verified by reading RecusExtension source code; raw HTML return pattern confirmed.

---

### Pitfall 7: Accessibility Regressions from Visual Polish

**What goes wrong:** Adding animations, custom hover states, tooltip overlays, and redesigned components can break keyboard navigation, screen reader compatibility, and WCAG contrast requirements. The existing tooltip system uses `mouseover`/`mouseout` listeners and a fixed-position popup, which is invisible to screen readers and unreachable via keyboard alone (though the current code does add `tabindex` and `focusin`/`focusout` -- a good start).

**Prevention:**
1. **Tooltips:** The current implementation already handles keyboard focus events (good). Ensure the tooltip popup has `role="tooltip"` and the trigger element has `aria-describedby` pointing to the popup ID
2. **Color contrast:** Quebec blue (#003DA5) on white gives a contrast ratio of approximately 8.5:1 (excellent). But lighter variants like `--qc-blue-light: #1A5BBF` on `--qc-blue-lighter: #EDF2FB` may fail WCAG AA for small text -- verify every color combination
3. **Animations:** Respect `prefers-reduced-motion` media query. Wrap all `transition` and `animation` declarations in `@media (prefers-reduced-motion: no-preference) { ... }`. The current theme has `--qc-transition: 180ms` everywhere with no reduced-motion guard
4. **Confidence badges:** The colored badges (green/amber/red) must not rely solely on color to convey meaning. Current implementation uses text labels ("Elevee", "Moderee", "Revision") alongside colors -- this is correct, maintain it
5. **Drag-and-drop:** Provide an alternative file input button for keyboard/screen reader users. Never make drag-and-drop the only upload method
6. **Focus visibility:** Ensure `:focus-visible` outlines are not removed by the theme. The current `.cqc-input:focus` uses `outline: none` with a `box-shadow` replacement -- this works for mouse users but verify it remains visible in Windows High Contrast Mode

**Detection:**
- Tab through every page with keyboard only -- every interactive element should be reachable and have a visible focus indicator
- Run axe-core or Lighthouse Accessibility audit on each extension page
- Test with `prefers-reduced-motion: reduce` enabled (System Preferences > Accessibility > Display > Reduce motion)

**Confidence:** MEDIUM -- current code has partial accessibility support; the risk is in new additions breaking what works.

---

## Minor Pitfalls

### Pitfall 8: Google Fonts External Dependency

**What goes wrong:** The theme loads Inter font from Google Fonts CDN. If the user runs CompteQC offline (stated goal: self-hosted, local data), or if Google Fonts is blocked by a corporate firewall or Pi-hole, the font fails to load and the system font fallback causes layout shifts.

**Prevention:**
1. Self-host the Inter font files (woff2) in the extension's static directory
2. Serve them via Fava's static file mechanism or inline them as base64 in the CSS (woff2 is already small)
3. This also eliminates the privacy concern of Google tracking font requests for a financial application

**Confidence:** HIGH -- the external dependency is visible in the code; self-hosting is straightforward.

---

### Pitfall 9: Mobile Responsiveness Within Fava's Fixed Layout

**What goes wrong:** Fava's layout uses a fixed sidebar that does not collapse on mobile. Custom responsive breakpoints in the theme (the existing `@media (max-width: 768px)` rules) only affect the extension content area, not Fava's own sidebar/header/article layout. On a phone, the sidebar consumes most of the screen width and the article content is cramped.

**Prevention:**
1. Do not attempt to fix Fava's own responsive behavior -- it is outside extension scope
2. Focus responsive CSS on the content within `<article>`: KPI grids, tables, cards
3. Use `overflow-x: auto` on all tables so they scroll horizontally on narrow screens instead of breaking layout
4. Treat mobile as "functional but not polished" -- the stated scope excludes mobile apps

**Confidence:** MEDIUM -- mobile is explicitly out of scope ("web-first, no mobile app"), but basic usability should not regress.

---

### Pitfall 10: Svelte-Scoped Styles in Fava Components

**What goes wrong:** Fava uses Svelte for some of its frontend components. Svelte scopes CSS by adding unique class attributes (e.g., `class="svelte-abc123"`) to elements and their style rules. These scoped styles have higher specificity than generic element selectors in extension CSS, making them impossible to override without `!important` or matching the scoped class (which changes between Fava versions).

**Prevention:**
1. **Accept that some Fava component internals cannot be styled.** Do not try to override Svelte-scoped styles with increasingly specific selectors
2. **Target CSS custom properties** exposed by Fava (e.g., `--text-color`, `--border`) which flow through to Svelte components via variable inheritance
3. **For flex-table specifically:** The current code's approach (`article .flex-table { color: var(--qc-text) !important; }`) is the correct workaround -- Svelte scopes inline `color: rgb(64,64,64)` which can only be overridden with `!important`
4. **Document which `!important` rules exist specifically for Svelte overrides** vs. which are unnecessary -- this is the legitimate use case

**Confidence:** HIGH -- verified `article .flex-table` pattern in existing ThemeQCExtension.js; Fava's Svelte usage is confirmed.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Dashboard + KPI cards | Chart.js memory leak on navigation (#1) | Implement chart registry + destroy-on-load pattern before any chart work |
| Table redesign across all extensions | Animation jank on large tables (#4) | Compositor-only properties; add `contain: content`; threshold-based animation disable |
| Receipt upload UX overhaul | Upload breaks SPA context (#6) | Convert to AJAX-based upload with JSON responses before adding progress bar |
| Design system refinement | `!important` escalation (#2) | Audit all 91 existing `!important` uses; migrate to CSS variable overrides first |
| Micro-interactions | Accessibility regression (#7) | Add `prefers-reduced-motion` guard to every transition/animation from day one |
| All extension restyling | DOM mutations lost on navigation (#3) | Replace boolean flags with DOM presence checks; test navigation cycle thoroughly |
| Global theme polish | FOUC on page load (#5) | Prioritize `:root` variable overrides which apply before first paint |
| Overall system | Offline font loading (#8) | Self-host Inter font before any typography work |

---

## Recommended Implementation Order (Based on Pitfalls)

1. **First:** Self-host fonts and audit `!important` declarations -- these are prerequisites that reduce friction for all subsequent work
2. **Second:** Implement Chart.js lifecycle management (registry + destroy pattern) -- this must exist before any chart is created
3. **Third:** Convert upload to AJAX/JSON -- must happen before UX polish on upload flow
4. **Fourth:** Add `prefers-reduced-motion` media query wrapper -- must exist before adding any animations
5. **Then:** Proceed with visual polish (tables, KPIs, cards, animations) with the safety nets in place

---

## Sources

- [Fava Extension Help Documentation](https://fava.pythonanywhere.com/example-beancount-file/help/extensions) -- Official callback documentation (init, onPageLoad, onExtensionPageLoad)
- [Fava GitHub Issue #1175: Extensions with script tags](https://github.com/beancount/fava/issues/1175) -- SPA navigation and innerHTML replacement behavior
- [Chart.js GitHub Issue #462: Memory leak](https://github.com/chartjs/Chart.js/issues/462) -- Chart.js destroy() requirement in SPAs
- [Chart.js GitHub Issue #7931: destroy() in React](https://github.com/chartjs/Chart.js/issues/7931) -- Additional memory leak patterns
- [MDN: CSS and JavaScript animation performance](https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/CSS_JavaScript_animation_performance) -- Compositor-layer properties
- [Smashing Magazine: CSS GPU Animation](https://www.smashingmagazine.com/2016/12/gpu-animation-doing-it-right/) -- will-change and GPU compositing best practices
- [Uploadcare: File Uploader UX Best Practices](https://uploadcare.com/blog/file-uploader-ux-best-practices/) -- Upload error handling and duplicate prevention
- Fava source code: `/fava/ext/__init__.py` (verified no onPageUnload callback)
- Fava source code: `/fava/static/app.css` (verified 0 `!important`, 40+ CSS custom properties)
- CompteQC source: `ThemeQCExtension.js` (verified 91 `!important` declarations, boolean flag pattern)
