---
phase: quick-16
plan: 01
subsystem: ui
tags: [anthropic, chat, fava-extension, mcp-tools, claude]

requires:
  - phase: 04-mcp-server-and-web-dashboard
    provides: "13 MCP tools (ledger, categorisation, approbation, paie, quebec)"
  - phase: quick-14
    provides: "OperationsExtension pattern for Fava extensions with endpoints"
provides:
  - "CHAT-TAB-DESIGN.md architecture document for Claude chat integration"
  - "ChatExtension Fava extension skeleton with /chat proxy endpoint"
  - "Chat UI template with message bubbles and tool-call display"
affects: [future-chat-implementation, mcp-tools, fava-extensions]

tech-stack:
  added: [anthropic-sdk]
  patterns: [tool-bridge-pattern, rate-limiting, session-storage-persistence]

key-files:
  created:
    - ".planning/quick/16-design-chat-tab-integration-for-discussi/CHAT-TAB-DESIGN.md"
    - "src/compteqc/fava_ext/chat/__init__.py"
    - "src/compteqc/fava_ext/chat/templates/ChatExtension.html"
  modified: []

key-decisions:
  - "Option A (direct Anthropic API with tool_use) over Option B (MCP subprocess) for simplicity"
  - "Disable lancer_paie via chat for safety -- payroll mutations require dedicated UI"
  - "claude-sonnet-4-20250514 model for cost/quality balance in tool-use scenarios"
  - "sessionStorage for conversation persistence (not server-side) -- stateless backend"
  - "Max 10 tool iterations per turn as safety valve"

patterns-established:
  - "Tool bridge: map Anthropic tool_use blocks to local function calls without MCP subprocess"
  - "Rate limiting: in-memory counter with per-second and per-hour limits for single-user"

requirements-completed: [CHAT-01]

duration: 6min
completed: 2026-02-26
---

# Quick Task 16: Chat Tab Integration Design Summary

**Architecture design and working Fava extension skeleton for Claude-powered financial chat with access to 13 MCP tools**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-26T13:37:41Z
- **Completed:** 2026-02-26T13:43:14Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments
- Comprehensive architecture design document (328 lines) covering 9 sections: architecture overview, approach comparison, system prompt, frontend, security, data flow, tool inventory, dependencies, implementation roadmap
- Working ChatExtension Fava extension (796 lines) with POST /chat endpoint, tool bridge for all 13 MCP tools, rate limiting, and graceful error handling
- Chat UI template (513 lines) with CompteQC design system styling, message bubbles, tool-call badges, keyboard shortcuts, and sessionStorage persistence

## Task Commits

Each task was committed atomically:

1. **Task 1: Create architecture design document** - `6d095ba` (docs)
2. **Task 2: Scaffold ChatExtension with proxy endpoint and chat UI** - `9ca2b0b` (feat)

## Files Created/Modified
- `.planning/quick/16-design-chat-tab-integration-for-discussi/CHAT-TAB-DESIGN.md` - Architecture design document with 9 sections
- `src/compteqc/fava_ext/chat/__init__.py` - ChatExtension with /chat endpoint, tool bridge, rate limiting
- `src/compteqc/fava_ext/chat/templates/ChatExtension.html` - Chat UI with message bubbles, tool badges, keyboard shortcuts

## Decisions Made
- **Option A over Option B:** Direct Anthropic API with tool_use chosen over MCP subprocess for simplicity -- no subprocess lifecycle management needed for single-user local tool
- **Safety restriction on lancer_paie:** Payroll execution disabled in chat context; returns informational message directing to Paie tab -- mutations through chat are too risky
- **Model selection:** claude-sonnet-4-20250514 for good tool-use quality at reasonable cost
- **Stateless backend:** Conversation stored in browser sessionStorage, sent with each request -- no server-side session management needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
To activate the chat tab:
1. Add `anthropic` to dependencies: `uv pip install anthropic`
2. Set environment variable: `export ANTHROPIC_API_KEY=sk-ant-...`
3. Register extension in beancount config: `2025-01-01 custom "fava-extension" "compteqc.fava_ext.chat"`

## Next Steps (from Design Document)
- Add `anthropic` to pyproject.toml optional dependencies
- Implement streaming support (SSE) for real-time token display
- Register extension in ledger config
- End-to-end testing with live API key

---
*Quick Task: 16-design-chat-tab-integration*
*Completed: 2026-02-26*
