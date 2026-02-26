---
phase: quick-16
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/16-design-chat-tab-integration-for-discussi/CHAT-TAB-DESIGN.md
  - src/compteqc/fava_ext/chat/__init__.py
  - src/compteqc/fava_ext/chat/templates/ChatExtension.html
autonomous: true
requirements: [CHAT-01]
must_haves:
  truths:
    - "Design document captures full architecture for Claude chat within Fava"
    - "Extension skeleton registers as a Fava tab and renders a chat UI shell"
    - "Document specifies how the Fava extension proxies to the MCP server for tool calls"
  artifacts:
    - path: ".planning/quick/16-design-chat-tab-integration-for-discussi/CHAT-TAB-DESIGN.md"
      provides: "Architecture design document for chat tab integration"
      min_lines: 80
    - path: "src/compteqc/fava_ext/chat/__init__.py"
      provides: "ChatExtension Fava extension with proxy endpoint"
      min_lines: 30
    - path: "src/compteqc/fava_ext/chat/templates/ChatExtension.html"
      provides: "Chat UI template with message list and input"
      min_lines: 50
  key_links:
    - from: "ChatExtension.html"
      to: "ChatExtension /api/chat endpoint"
      via: "fetch POST from JS"
      pattern: "fetch.*api/chat"
    - from: "ChatExtension.__init__.py"
      to: "Anthropic Messages API"
      via: "anthropic SDK or HTTP"
      pattern: "anthropic|messages"
---

<objective>
Design and scaffold a Chat tab for the CompteQC Fava dashboard that lets the user discuss their finances with Claude directly from the web UI, with Claude having access to all existing MCP tools (ledger queries, categorisation, payroll, taxes, etc.).

Purpose: The user wants to ask questions like "What were my biggest expenses this quarter?" or "Run my payroll for January" directly from the dashboard, with Claude using the 13 existing MCP tools to answer.

Output: A design document (CHAT-TAB-DESIGN.md) covering architecture decisions, plus a working extension skeleton with the chat UI and a proxy endpoint.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/compteqc/mcp/server.py
@src/compteqc/fava_ext/operations/__init__.py
@src/compteqc/fava_ext/operations/templates/OperationsExtension.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create architecture design document for chat tab</name>
  <files>.planning/quick/16-design-chat-tab-integration-for-discussi/CHAT-TAB-DESIGN.md</files>
  <action>
Create a comprehensive design document covering:

**1. Architecture Overview**
- The Chat tab is a new Fava extension (`ChatExtension`) following the same pattern as `OperationsExtension`, `ApprobationExtension`, etc.
- The extension exposes a POST endpoint (`/chat`) that receives user messages and streams Claude's responses back.
- Claude is configured as an MCP client with access to all 13 existing CompteQC tools.

**2. Two viable approaches -- recommend one:**

**Option A: Anthropic API with tool_use (RECOMMENDED)**
- The Fava extension backend calls the Anthropic Messages API directly using the `anthropic` Python SDK.
- Define all 13 MCP tools as Anthropic tool definitions (JSON schema) in the extension.
- When Claude returns a `tool_use` block, the extension executes the tool locally by importing the same functions the MCP server uses (from `compteqc.mcp.tools.*` and `compteqc.mcp.services`), then feeds the result back to Claude as a `tool_result`.
- The conversation loop runs server-side; the frontend only sends/receives chat messages.
- Pros: Simple frontend, no MCP subprocess management, reuses existing Python functions directly.
- Cons: Must maintain tool definitions in sync with MCP tools, requires ANTHROPIC_API_KEY env var.

**Option B: MCP client subprocess**
- Spawn the CompteQC MCP server as a subprocess and use `mcp` Python client SDK to connect via stdio.
- Use `anthropic` SDK with MCP client integration to let Claude call tools through MCP protocol.
- Pros: Zero tool definition duplication, uses MCP natively.
- Cons: Subprocess lifecycle management in a Flask request context is tricky, heavier.

**3. System prompt design**
- Claude acts as a bilingual (FR/EN) financial assistant for a Quebec CCPC.
- System prompt includes: fiscal year context, chart of accounts summary, available tools list with descriptions.
- Claude must never invent numbers -- always use tools to query real data.
- Claude must surface uncertainty and recommend CPA for tax advice.

**4. Frontend design**
- Chat UI in the existing CompteQC design system (cqc-card, cqc-btn, Quebec blue palette).
- Message list with user/assistant bubbles, markdown rendering for Claude's responses.
- Input area with textarea + send button, Shift+Enter for newlines, Enter to send.
- Streaming via SSE (Server-Sent Events) or chunked response for real-time token display.
- "Thinking" indicator when Claude is processing or calling tools.
- Tool call visibility: show which tools Claude called (collapsible detail).
- Conversation persists in browser sessionStorage (not server-side) -- refreshing the tab starts fresh.

**5. Security considerations**
- ANTHROPIC_API_KEY stored as env var, never exposed to frontend.
- Rate limiting: simple in-memory counter (1 req/sec, 100 msgs/hour) since single-user.
- No user auth needed (Fava is already local/trusted).
- Sanitize Claude's output before rendering (XSS prevention).

**6. Data flow diagram** (ASCII)
```
Browser (ChatExtension.html)
  |-- POST /chat {messages: [...]}
  v
ChatExtension (Flask endpoint)
  |-- anthropic.messages.create(tools=[...])
  |-- tool_use? --> call compteqc.mcp.tools.* directly
  |-- tool_result --> feed back to Claude
  |-- final text response
  v
Browser renders response
```

**7. Available MCP tools to expose** (list all 13 with their signatures):
- soldes_comptes(filtre?) -- account balances
- balance_verification() -- trial balance
- etat_resultats(date_debut?, date_fin?) -- income statement
- bilan() -- balance sheet
- proposer_categorie(payee, narration, montant) -- AI categorization
- lister_pending_tool() -- pending transactions
- approuver_lot(ids, action, compte?) -- batch approve/reject
- rejeter(id) -- reject single
- calculer_paie_tool(brut, periode, ...) -- payroll calc
- lancer_paie(brut, periode, ...) -- execute payroll
- sommaire_tps_tvq(trimestre?) -- GST/QST summary
- etat_dpa() -- CCA/DPA status
- etat_pret_actionnaire() -- shareholder loan status

**8. Dependencies to add**
- `anthropic` Python SDK (pip install anthropic)
- No frontend dependencies needed -- vanilla JS with existing design system.

**9. Implementation plan** (ordered steps for future execution)
- Step 1: Add `anthropic` to pyproject.toml
- Step 2: Create ChatExtension with /chat POST endpoint
- Step 3: Build tool bridge (Anthropic tool defs -> local function calls)
- Step 4: Create chat HTML template with message UI
- Step 5: Add streaming support (SSE)
- Step 6: Register extension in ledger config
- Step 7: Test end-to-end
  </action>
  <verify>File exists at .planning/quick/16-design-chat-tab-integration-for-discussi/CHAT-TAB-DESIGN.md with all 9 sections and at least 80 lines</verify>
  <done>Design document covers architecture, two options with recommendation, system prompt, frontend, security, data flow, tool inventory, dependencies, and implementation roadmap</done>
</task>

<task type="auto">
  <name>Task 2: Scaffold ChatExtension Fava extension with proxy endpoint and chat UI</name>
  <files>src/compteqc/fava_ext/chat/__init__.py, src/compteqc/fava_ext/chat/templates/ChatExtension.html</files>
  <action>
Create the working extension skeleton following the established Fava extension pattern (see OperationsExtension as reference).

**__init__.py:**
- Class `ChatExtension(FavaExtensionBase)` with `report_title = "Chat"`.
- POST endpoint via `@extension_endpoint("chat", ["POST"])` that:
  1. Reads JSON body `{"messages": [{"role": "user", "content": "..."}], "system_context": optional}`.
  2. Builds the system prompt with fiscal year info pulled from the ledger (fiscal_year_end from beancount options, current date, company name).
  3. Calls `anthropic.Anthropic().messages.create()` with the messages, system prompt, and tool definitions.
  4. Implements the tool-use loop: when Claude returns `tool_use` blocks, execute the corresponding function from `compteqc.mcp.tools.*` by importing and calling them directly (build an `AppContext` from `self.ledger` for the tools that need it).
  5. Returns JSON `{"role": "assistant", "content": "...", "tools_used": ["tool_name", ...]}`.
- A `TOOLS` constant list mapping Anthropic tool definitions (name, description, input_schema) to local callables.
- Helper `_execute_tool(name, args, ledger)` that routes tool calls to local functions.
- Graceful error handling: if ANTHROPIC_API_KEY is missing, return a helpful error message.

**ChatExtension.html:**
- Page title "Chat" with header "Discuter de vos finances" and subtitle.
- Chat message area (`cqc-chat-messages`) styled as a scrollable container with max-height.
- User messages: right-aligned, blue background (--qc-blue with white text).
- Assistant messages: left-aligned, surface-raised background, with markdown-like formatting (bold, code blocks via simple regex replacement -- no library needed).
- Tool call badges: when `tools_used` is non-empty, show collapsible "Outils utilises: soldes_comptes, bilan" below the assistant message.
- Input area: textarea with auto-resize, send button (cqc-btn cqc-btn-primary), keyboard shortcut (Enter sends, Shift+Enter newline).
- Loading state: animated dots "Claude reflechit..." during request.
- Conversation state: stored in a JS array, sent with each request for context continuity.
- Welcome message on first load: "Bonjour! Je suis votre assistant financier. Je peux consulter vos comptes, calculer la paie, verifier vos taxes TPS/TVQ, et bien plus. Posez-moi une question!"
- All styling uses existing design system variables (--qc-*, --cqc-font-*, cqc-card, etc.).
- Error display: if API key missing or network error, show in cqc-ops-result-error style.
- No external JS dependencies -- vanilla JS with XHR (consistent with OperationsExtension pattern).
  </action>
  <verify>python -c "from compteqc.fava_ext.chat import ChatExtension; print('OK')" && test -f src/compteqc/fava_ext/chat/templates/ChatExtension.html && echo "PASS"</verify>
  <done>ChatExtension is importable, has /chat endpoint, template renders a chat interface with message bubbles, input area, and tool-call display -- all using the existing CompteQC design system</done>
</task>

</tasks>

<verification>
- Design document exists and covers all 9 sections
- ChatExtension is importable without errors
- Chat template follows CompteQC design system conventions (cqc-* classes, Quebec blue palette, design tokens)
- Extension endpoint pattern matches OperationsExtension
</verification>

<success_criteria>
- CHAT-TAB-DESIGN.md is a complete, actionable architecture document that a future execution phase can implement from
- ChatExtension skeleton compiles and could be registered in the beancount config
- Chat UI template matches the look and feel of existing CompteQC tabs
</success_criteria>

<output>
After completion, create `.planning/quick/16-design-chat-tab-integration-for-discussi/16-SUMMARY.md`
</output>
