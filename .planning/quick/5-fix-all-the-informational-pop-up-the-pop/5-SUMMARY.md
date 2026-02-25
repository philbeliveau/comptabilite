---
phase: quick-5
plan: "01"
subsystem: fava-ext/theme-qc
tags: [tooltip, ui, overflow-fix, fava-extension, javascript]
dependency_graph:
  requires: []
  provides: [body-level-tooltip-popup]
  affects: [ThemeQCExtension.js]
tech_stack:
  added: []
  patterns: [delegated-event-listeners, getBoundingClientRect, requestAnimationFrame, viewport-clamping]
key_files:
  created: []
  modified:
    - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
decisions:
  - "JS body-appended fixed div replaces CSS ::after pseudo-element to bypass all parent overflow:hidden constraints"
  - "Single delegated mouseover/mouseout/focusin/focusout listeners on document (not per-element) for performance"
  - "requestAnimationFrame used to measure popup size after textContent set, before final positioning"
  - "Viewport clamping: left=Math.max(margin, Math.min(left, vw-popupRect.width-margin)), same for top"
  - "Falls below element (rect.bottom + margin) when top < margin (no room above)"
  - "initTooltipPopup() is idempotent: checks for existing #cqc-tooltip-popup before creating"
metrics:
  duration: "< 1 minute"
  completed: "2026-02-20T03:28:36Z"
  tasks_completed: 1
  files_modified: 1
---

# Quick Task 5: Fix All Informational Popups (Tooltip Clipping) Summary

**One-liner:** Replaced CSS `::after` pseudo-element tooltips with a JS-rendered `position:fixed` div appended to `document.body`, with `getBoundingClientRect` positioning and viewport edge clamping, eliminating all `overflow:hidden` clipping.

## What Was Done

### Root Cause

The previous tooltip implementation used `[data-tooltip]::after` with `position: absolute`. When a tooltipped element lived inside a parent with `overflow: hidden` (specifically `.cqc-kpi` tiles at line 387 and `.cqc-card-flush` tables at line 334), the pseudo-element was clipped by the parent boundary and invisible to users.

### Solution

A single `div#cqc-tooltip-popup` is appended to `document.body` once per session. Because it is a direct child of `<body>` with `position: fixed`, no ancestor `overflow: hidden` can clip it.

### Changes to `ThemeQCExtension.js`

**CSS block (lines 1014-1045):** Replaced the old `[data-tooltip]` + `[data-tooltip]::after` rules with:
- `[data-tooltip]` retains only `cursor: help` and dotted underline (removed `position: relative` since it is no longer needed).
- `#cqc-tooltip-popup` styled as `position: fixed; z-index: 9999` with opacity/visibility transitions.
- `.cqc-tooltip-visible` class toggles opacity to 1 / visibility to visible.

**Three new JS functions (after `attachTooltips`, before `injectReportHeader`):**
- `initTooltipPopup()` — creates the popup div, appends to body, registers four delegated event listeners on `document` (mouseover, mouseout, focusin, focusout). Idempotent guard via `getElementById`.
- `showTooltip(el)` — sets `textContent`, positions off-screen, then uses `requestAnimationFrame` to measure the rendered popup size via `getBoundingClientRect`, then computes clamped `left`/`top` within the viewport.
- `hideTooltip()` — removes `.cqc-tooltip-visible` class.

**`onPageLoad()` export:** Added `initTooltipPopup()` call after `injectStyle()`. Called once per page navigation; idempotency guard prevents duplicate popup divs and listener leaks.

## Verification

Manual testing checklist (requires running Fava):
- `python -m fava data/comptabilite.beancount` then open http://localhost:5000
- Navigate to Paie QC extension
- Hover KPI tile labels (Salaire brut, Salaire net, etc.) — popup appears fully above tile, not clipped
- Hover table column headers inside `.cqc-card-flush` — popup visible above header
- Hover element near right viewport edge — popup clamps left, stays within screen
- Hover element near top of page — popup falls below element instead of going off-screen
- Tab to tooltipped element (keyboard navigation) — popup appears on focus, hides on blur

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- File modified: `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` — exists and contains all three changes
- Commit `8cb8d60` — verified in git log
- No regressions to other CSS blocks, TOOLTIPS dictionary, attachTooltips(), SIDEBAR_GROUPS, or REPORT_INTROS
