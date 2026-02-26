---
phase: 09-receipt-upload-ux
plan: 02
subsystem: ui
tags: [drag-drop, file-preview, thumbnails, multi-upload, css-animations, objecturl]

requires:
  - phase: 09-receipt-upload-ux
    provides: XHR upload with progress bar and JSON endpoint
provides:
  - File preview thumbnails (image) and icons (PDF/HEIC) after upload
  - Animated drag-and-drop with pulsing border and glow
  - Multi-file sequential upload with per-file progress
affects: [receipt workflow, upload UX]

tech-stack:
  added: []
  patterns: [dragCounter pattern for child-element flicker prevention, URL.createObjectURL with revokeObjectURL cleanup, sequential async upload loop]

key-files:
  created: []
  modified:
    - src/compteqc/fava_ext/recus/templates/RecusExtension.html
    - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js

key-decisions:
  - "dragCounter pattern instead of relatedTarget for cross-browser flicker prevention"
  - "Blue palette for dragover animation (success green reserved for completion states)"
  - "HEIC treated as icon (not thumbnail) since browsers cannot render HEIC natively"
  - "Sequential upload (not parallel) to avoid server overload and provide clear per-file progress"

patterns-established:
  - "dragCounter pattern: increment on dragenter, decrement on dragleave, reset on drop"
  - "createObjectURL + revokeObjectURL on img.onload for memory-safe client-side previews"

requirements-completed: [RCPT-03, RCPT-04]

duration: 2min
completed: 2026-02-25
---

# Phase 9 Plan 02: File Previews and Drag-and-Drop Animations Summary

**Image thumbnail previews via createObjectURL, animated pulsing dropzone border, and multi-file sequential upload with per-file progress tracking**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T02:02:10Z
- **Completed:** 2026-02-26T02:04:18Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Drag-and-drop uses dragCounter pattern preventing child-element flicker
- Dropzone has animated pulsing blue border with glow effect on dragover
- Multiple files can be dropped or selected and upload sequentially with "Fichier X sur N" status
- Image files (jpg, jpeg, png) show scaled thumbnail preview after upload
- PDF and HEIC files show document icon with filename
- Object URLs properly revoked after image load to prevent memory leaks
- All animations respect prefers-reduced-motion
- Extracted amount badge displayed when available

## Task Commits

Each task was committed atomically:

1. **Task 1: Drag-and-drop animations and multi-file support** - `d132ac8` (feat)
2. **Task 2: File preview thumbnails after upload** - `9d9b13f` (feat)

## Files Created/Modified
- `src/compteqc/fava_ext/recus/templates/RecusExtension.html` - dragCounter pattern, multi-file uploadFiles(), renderPreview() with createObjectURL, preview container HTML
- `src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js` - cqc-border-pulse keyframe animation, dragover glow, preview grid/item/thumb/icon/badge CSS, queue status styling, reduced-motion guard

## Decisions Made
- Used dragCounter pattern for flicker prevention (simpler and more reliable than relatedTarget across browsers)
- Blue palette for dragover state since green/success should indicate completion, not in-progress interaction
- HEIC files treated as document icons since browsers cannot render HEIC format natively
- Sequential upload loop (await each) rather than parallel to provide clear per-file progress and avoid server overload

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Receipt upload UX complete with full modern upload experience
- Phase 09 fully complete (both plans executed)
- Ready for any subsequent phases

---
*Phase: 09-receipt-upload-ux*
*Completed: 2026-02-25*
