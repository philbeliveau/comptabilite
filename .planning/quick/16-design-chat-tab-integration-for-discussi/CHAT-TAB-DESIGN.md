# Chat Tab Integration Design Document

## 1. Architecture Overview

The Chat tab is a new Fava extension (`ChatExtension`) that follows the established CompteQC extension pattern (same as `OperationsExtension`, `ApprobationExtension`, etc.). It allows the user to converse with Claude directly from the Fava dashboard, with Claude having access to all 13 existing CompteQC MCP tools.

**Core idea:** The user asks financial questions in natural language (French or English), and Claude answers by querying the real ledger data through the same tool functions the MCP server uses.

**Key components:**
- `ChatExtension` (Fava extension) -- Flask-based backend with a POST `/chat` endpoint
- `ChatExtension.html` -- Jinja2 template with chat UI using the CompteQC design system
- Tool bridge -- maps Anthropic tool_use calls to local Python function calls
- System prompt -- configures Claude as a bilingual Quebec CCPC financial assistant

---

## 2. Approach Comparison

### Option A: Anthropic API with tool_use (RECOMMENDED)

The Fava extension backend calls the Anthropic Messages API directly using the `anthropic` Python SDK. All 13 MCP tools are defined as Anthropic tool definitions (JSON schema) in the extension. When Claude returns a `tool_use` block, the extension executes the corresponding function by importing the same code the MCP server uses, then feeds the result back as a `tool_result`.

**Pros:**
- Simple frontend (only sends/receives chat messages)
- No subprocess lifecycle management
- Reuses existing Python functions directly (same imports as MCP tools)
- Single HTTP roundtrip per user message (tool loop runs server-side)
- Easy to test -- just call the endpoint with curl

**Cons:**
- Must maintain tool definitions in sync with MCP tools (mitigated by generating from source)
- Requires `ANTHROPIC_API_KEY` environment variable
- API costs per conversation turn

### Option B: MCP Client Subprocess

Spawn the CompteQC MCP server as a subprocess and use the `mcp` Python client SDK to connect via stdio. Use the `anthropic` SDK with MCP client integration.

**Pros:**
- Zero tool definition duplication -- MCP protocol handles discovery
- Uses MCP natively as designed

**Cons:**
- Subprocess lifecycle management in Flask request context is fragile
- Heavier resource usage (separate Python process per request or persistent child)
- More complex error handling (subprocess crashes, timeouts)
- Async MCP client in sync Flask context requires bridging (asyncio.run)

### Decision: Option A

Option A is significantly simpler for a single-user local tool. The tool definition maintenance cost is low (13 tools, rarely changing schemas), and the direct function call approach avoids all subprocess complexity.

---

## 3. System Prompt Design

```
Tu es un assistant financier bilingue (francais/anglais) pour une SPCC (societe privee sous controle canadien) incorporee au Quebec. Tu travailles avec le systeme comptable CompteQC.

Contexte fiscal:
- Annee fiscale: {fiscal_year} (se terminant le {fiscal_year_end})
- Date du jour: {today}
- Entreprise: Consultation IT solo, ~230 000 $ de revenus annuels
- Juridiction: Quebec, Canada (TPS 5% + TVQ 9.975%)

Regles strictes:
1. N'invente JAMAIS de chiffres. Utilise toujours les outils pour consulter les donnees reelles du ledger.
2. Quand tu ne sais pas, dis-le clairement.
3. Pour les questions de strategie fiscale (salaire vs dividendes, optimisation T2/CO-17), recommande de consulter le CPA.
4. Montre tes calculs quand tu fais des operations arithmetiques.
5. Reponds dans la langue de la question (francais si francais, anglais si anglais).

Outils disponibles: Tu as acces a 13 outils pour consulter le grand-livre, categoriser des transactions, gerer la file d'approbation, calculer la paie, et consulter les taxes TPS/TVQ, la DPA et le pret actionnaire.
```

The system prompt is built dynamically at request time, pulling:
- `fiscal_year_end` from beancount options (`option "fiscal_year_end"`)
- Current date via `datetime.date.today()`
- Company context from CLAUDE.md constants

---

## 4. Frontend Design

### Layout
- Page header: "Chat" with subtitle "Discuter de vos finances avec Claude"
- Full-width chat container inside a `cqc-card`
- Message area: scrollable `div` with `max-height: calc(100vh - 300px)`
- Input area: fixed at bottom of card, textarea + send button

### Message Rendering
- **User messages:** Right-aligned, `--qc-blue` background with white text, rounded corners
- **Assistant messages:** Left-aligned, `--qc-surface-raised` background, normal text color
- **Markdown-like formatting:** Simple regex-based rendering:
  - `**bold**` -> `<strong>`
  - `` `code` `` -> `<code>`
  - ` ```block``` ` -> `<pre><code>`
  - Newlines -> `<br>`
- **Tool call badges:** Below assistant messages when tools were used, collapsible `<details>` element showing "Outils utilises: soldes_comptes, bilan"

### Input Area
- `<textarea>` with auto-resize (grows with content, max 6 lines)
- Send button (`cqc-btn cqc-btn-primary`)
- **Keyboard:** Enter sends message, Shift+Enter inserts newline
- Disabled during request processing

### Loading State
- Animated dots: "Claude reflechit..." with CSS-only dot animation
- Send button shows spinner/disabled state

### Conversation State
- Stored in a JS array (`conversationMessages`)
- Sent with each request for context continuity
- Persisted in `sessionStorage` (survives in-tab navigation, cleared on tab close)
- Welcome message displayed on first load (not sent to API)

### No External Dependencies
- Vanilla JS with XHR (consistent with OperationsExtension pattern)
- All styling uses existing design system variables (`--qc-*`, `--cqc-font-*`, `cqc-card`, etc.)

---

## 5. Security Considerations

### API Key Protection
- `ANTHROPIC_API_KEY` stored as environment variable, never exposed to frontend
- If missing, endpoint returns a friendly error: "Cle API Anthropic non configuree"

### Rate Limiting
- Simple in-memory counter (single-user tool, no need for Redis/distributed)
- Limits: 1 request/second, 100 messages/hour
- Returns 429 with French message when exceeded

### XSS Prevention
- All Claude output sanitized before rendering to HTML
- User messages escaped via `textContent` assignment
- Code blocks rendered in `<pre><code>` with escaped content

### No Authentication Required
- Fava is already local/trusted (runs on localhost)
- No additional auth layer needed

### Cost Controls
- Model: `claude-sonnet-4-20250514` (good balance of quality/cost for tool-use)
- Max tokens: 4096 per response
- Conversation context: last 20 messages sent (sliding window)

---

## 6. Data Flow Diagram

```
Browser (ChatExtension.html)
  |
  |  POST /{slug}/extension/ChatExtension/chat
  |  Body: {"messages": [{"role": "user", "content": "..."}]}
  |
  v
ChatExtension (Flask endpoint)
  |
  |  1. Build system prompt (fiscal year, date, tools)
  |  2. Call anthropic.messages.create(
  |       model="claude-sonnet-4-20250514",
  |       system=system_prompt,
  |       tools=TOOL_DEFINITIONS,
  |       messages=messages
  |     )
  |
  |  3. Response contains tool_use blocks?
  |     |
  |     YES --> Execute tool locally:
  |     |       - Build AppContext from self.ledger
  |     |       - Call compteqc function directly
  |     |       - Append tool_result to messages
  |     |       - Loop back to step 2
  |     |
  |     NO --> Extract text response
  |
  |  4. Return JSON:
  |     {"role": "assistant", "content": "...", "tools_used": [...]}
  |
  v
Browser renders response
  - Append assistant bubble with markdown formatting
  - Show tool badges if tools_used is non-empty
  - Re-enable input
```

---

## 7. Available MCP Tools to Expose

All 13 tools from the CompteQC MCP server, organized by module:

### Ledger (compteqc.mcp.tools.ledger)

| Tool | Signature | Description |
|------|-----------|-------------|
| `soldes_comptes` | `(filtre?: str)` | Account balances, filtered by substring |
| `balance_verification` | `()` | Trial balance with debit/credit totals |
| `etat_resultats` | `(date_debut?: str, date_fin?: str)` | Income statement for a period |
| `bilan` | `()` | Balance sheet (assets, liabilities, equity) |

### Categorisation (compteqc.mcp.tools.categorisation)

| Tool | Signature | Description |
|------|-----------|-------------|
| `proposer_categorie` | `(payee: str, narration: str, montant: str)` | AI-powered transaction categorization |

### Approbation (compteqc.mcp.tools.approbation)

| Tool | Signature | Description |
|------|-----------|-------------|
| `lister_pending_tool` | `()` | List pending transactions awaiting review |
| `approuver_lot` | `(ids: list[str], confirmer_gros_montants?: bool)` | Batch approve pending transactions |
| `rejeter` | `(id: str, compte_corrige?: str, raison?: str)` | Reject a pending transaction |

### Paie (compteqc.mcp.tools.paie)

| Tool | Signature | Description |
|------|-----------|-------------|
| `calculer_paie_tool` | `(salaire_brut: str, nb_periodes?: int)` | Dry-run payroll calculation |
| `lancer_paie` | `(salaire_brut: str, nb_periodes?: int, offset_pret?: str, confirmer?: bool)` | Execute payroll and write to ledger |

### Quebec (compteqc.mcp.tools.quebec)

| Tool | Signature | Description |
|------|-----------|-------------|
| `sommaire_tps_tvq` | `(periode?: str)` | GST/QST summary for a period |
| `etat_dpa` | `(annee?: int)` | CCA/DPA status by asset class |
| `etat_pret_actionnaire` | `()` | Shareholder loan status and s.15(2) alerts |

### Tool Bridge Implementation

Each tool definition maps to a local callable. The bridge:

1. Strips the `ctx` parameter (tools expect MCP Context, but we build our own AppContext)
2. Builds an `AppContext` from `self.ledger` (Fava's loaded beancount data)
3. Calls the underlying service function directly (not the `@mcp.tool()` wrapper)

```python
# Example bridge entry
TOOLS = {
    "soldes_comptes": {
        "callable": _call_soldes_comptes,
        "definition": {
            "name": "soldes_comptes",
            "description": "Afficher les soldes de tous les comptes du ledger...",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filtre": {"type": "string", "description": "Sous-chaine pour filtrer"}
                }
            }
        }
    },
    ...
}
```

---

## 8. Dependencies to Add

### Python (pyproject.toml)
```toml
[project.optional-dependencies]
chat = ["anthropic>=0.40.0"]
```

The `anthropic` SDK is the only new dependency. It handles:
- Messages API calls
- Tool use/result message formatting
- Token counting and streaming (future)

### Frontend
No new dependencies. Uses:
- Vanilla JavaScript (XHR pattern from OperationsExtension)
- Existing CompteQC design system CSS variables
- No markdown library (simple regex replacement is sufficient)

### Environment Variables
```bash
ANTHROPIC_API_KEY=sk-ant-...  # Required for chat functionality
```

---

## 9. Implementation Plan

### Step 1: Add `anthropic` to pyproject.toml
- Add as optional dependency under `[project.optional-dependencies]` chat group
- Or add to main dependencies if chat is considered core

### Step 2: Create ChatExtension with /chat POST endpoint
- `src/compteqc/fava_ext/chat/__init__.py`
- Class `ChatExtension(FavaExtensionBase)` with `report_title = "Chat"`
- POST endpoint via `@extension_endpoint("chat", ["POST"])`
- System prompt builder pulling fiscal year from beancount options

### Step 3: Build tool bridge
- Define `TOOL_DEFINITIONS` list (Anthropic tool format)
- Implement `_execute_tool(name, args, ledger)` dispatcher
- Build `AppContext` adapter from Fava's `FavaLedger`
- Handle tool_use loop (max 10 iterations as safety)

### Step 4: Create chat HTML template
- `src/compteqc/fava_ext/chat/templates/ChatExtension.html`
- Message list with user/assistant bubbles
- Input area with textarea + send button
- Keyboard shortcuts (Enter/Shift+Enter)
- Loading state animation

### Step 5: Add streaming support (SSE)
- Future enhancement: use `stream=True` on Anthropic API
- Return Server-Sent Events for real-time token display
- Fallback: current synchronous JSON response works for v1

### Step 6: Register extension in ledger config
- Add to `main.beancount`: `2025-01-01 custom "fava-extension" "compteqc.fava_ext.chat"`
- Extension auto-appears as "Chat" tab in Fava sidebar

### Step 7: Test end-to-end
- Verify extension loads without API key (shows config message)
- Verify chat roundtrip with API key set
- Verify tool calls work (ask "Quel est mon solde bancaire?")
- Verify conversation context persists across messages
- Verify error handling (network failure, API errors)
