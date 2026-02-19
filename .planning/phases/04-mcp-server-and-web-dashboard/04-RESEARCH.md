# Phase 4: MCP Server and Web Dashboard - Research

**Researched:** 2026-02-19
**Domain:** MCP Protocol (Python SDK) + Fava extension system for Beancount
**Confidence:** HIGH

## Summary

Phase 4 wraps the existing CompteQC domain modules (payroll, GST/QST, CCA, shareholder loan, categorization pipeline, ledger queries) behind two interfaces: an MCP server for Claude integration and custom Fava extensions for browser-based interaction. Both interfaces share the same underlying pending transaction approval queue and call the same pure-Python Quebec modules.

The MCP Python SDK (v1.x, pinned `mcp>=1.25,<2`) provides `FastMCP` with decorator-based tool registration, typed context injection via lifespan, and stdio transport for Claude Desktop/Claude Code. Fava (v1.30.x) provides `FavaExtensionBase` with Jinja2 templates, lifecycle hooks (`after_load_file`), and `@extension_endpoint()` for custom HTTP endpoints. Four custom Fava extensions (payroll, GST/QST, CCA, shareholder loan) plus one approval queue extension give the user browser-based dashboards. The MCP server is a separate process that loads the ledger directly via `beancount.loader.load_file` and calls the same domain modules the CLI already uses.

**Primary recommendation:** Build the MCP server first (it is simpler and validates the service layer), then build the Fava extensions. Both share a common `service/` layer that abstracts ledger operations away from transport concerns.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Full scope: Claude can query, propose entries/categorizations, approve/reject pending transactions, and run payroll -- complete workflow without leaving Claude
- Tool output includes proposed entry + short reasoning explanation (e.g. "Matched vendor X to Fournitures informatiques based on previous pattern") -- not minimal, not full trace
- Payroll via MCP: Claude can trigger payroll computation for a given gross salary and generate all journal entries
- Batch approve by default -- select multiple transactions and approve/reject as a group for speed
- Approval available in both interfaces -- MCP (via Claude conversation) and Fava web UI, same underlying queue
- Auto-approve above confidence threshold for transactions that pass; only lower-confidence items need manual review
- All four Quebec-specific views as custom Fava extensions: Payroll dashboard, GST/QST tracker, CCA schedule, Shareholder loan status
- Dollar-amount guardrail: transactions over $2,000 always require explicit human confirmation, even if high-confidence
- $2,000 is the explicit amount cap for auto-approval
- Quebec views to show real filing periods (annual/quarterly) not just calendar months
- CCA classes specifically called out: 8, 10, 12, 50, 54
- Shareholder loan view must include s.15(2) deadline countdown
- MCP tool reasoning should explain categorization logic (pattern matching, vendor history) not just the result

### Claude's Discretion
- MCP tool granularity (few broad vs many specific tools)
- Correction flow UX on rejected transactions
- AI confidence/source tag visual treatment in dashboard
- Pending queue as separate Fava page vs journal integration
- Dashboard network access defaults
- Read-only mode implementation
- Audit trail approach (dedicated log vs git history)
- Payroll run confirmation requirements for recurring amounts

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCP-01 | Custom MCP server exposes ledger query tools (balances, reports, account details) | FastMCP `@mcp.tool()` decorator with typed Pydantic returns; service layer wraps `_calculer_soldes()` and `_charger_ledger()` from existing `rapports.py` |
| MCP-02 | MCP server exposes categorization tools (propose category for transaction) | `PipelineCategorisation.categoriser()` already returns `ResultatPipeline` with compte/confiance/source; wrap in MCP tool with reasoning string |
| MCP-03 | MCP server exposes payroll tools (run payroll, get payroll summary) | `calculer_paie()` and `generer_transaction_paie()` exist; MCP tool wraps them with $2,000 confirmation guardrail |
| MCP-04 | MCP server exposes approval workflow tools (list pending, approve, reject) | New service layer for pending.beancount: parse #pending entries, batch approve/reject by moving to monthly files |
| MCP-05 | MCP server supports read-only mode for safe exploration | FastMCP lifespan context with `read_only: bool` flag; tools check flag before mutations |
| MCP-06 | MCP server built with official Python MCP SDK (mcp>=1.25,<2) | Verified: `mcp` v1.26.0 current on PyPI; FastMCP class confirmed in Context7 docs |
| WEB-01 | Fava serves as base web UI for ledger browsing, trial balance, P&L, balance sheet | `fava>=1.30` provides these out of the box; `create_app([ledger_path])` or `fava ledger/main.beancount` |
| WEB-02 | Custom Fava extension for transaction approval workflow (pending queue, approve/reject) | FavaExtensionBase with `report_title`, `@extension_endpoint()` for POST approve/reject, Jinja2 template |
| WEB-03 | Custom Fava extension for Quebec-specific report views (payroll, CCA, GST/QST) | Three separate extensions calling existing quebec modules; templates render data from `after_load_file()` |
| WEB-04 | Custom Fava extension for CPA export package generation | Extension with endpoint to trigger export; actual export logic deferred to Phase 5, but hook prepared |
| WEB-05 | Dashboard shows confidence indicators for AI-categorized transactions | Parse `confidence` and `ai-source` metadata from #pending entries; render as badges in Jinja2 template |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mcp | >=1.25,<2 | MCP server SDK | Official Anthropic Python SDK; FastMCP decorator API |
| fava | >=1.30 | Web dashboard base | Standard Beancount web UI; extension system for custom views |
| beancount | >=3.2 | Ledger engine | Already in project; loader, parser, data types |
| jinja2 | (via fava) | HTML templates | Fava's template engine; no additional dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uvicorn | (via mcp) | ASGI server | Implied by MCP SDK for streamable-http; not needed for stdio |
| starlette | (via mcp) | HTTP framework | Already pulled in by MCP SDK |
| pydantic | >=2 | Tool input/output schemas | Already in project; MCP uses it for tool schemas |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastMCP high-level API | Low-level `mcp.server.lowlevel.Server` | More control but much more boilerplate; FastMCP is sufficient |
| Fava extensions | fava-dashboards (TypeScript/ECharts) | Powerful charts but requires JS build toolchain; our views are tables/lists, Jinja2 suffices |
| Separate FastAPI app | Fava for everything | FastAPI was considered for approval UI but Fava extensions handle it without a separate process |

**Installation:**
```bash
uv add "mcp>=1.25,<2"
uv add "fava>=1.30"
```

## Architecture Patterns

### Recommended Project Structure
```
src/compteqc/
+-- mcp/                       # MCP server
|   +-- __init__.py
|   +-- server.py              # FastMCP instance, lifespan, stdio entry
|   +-- tools/
|   |   +-- __init__.py
|   |   +-- ledger.py          # query_balance, query_resultats, query_bilan, query_compte
|   |   +-- categorisation.py  # proposer_categorie, categoriser_lot
|   |   +-- approbation.py     # lister_pending, approuver, rejeter, approuver_lot
|   |   +-- paie.py            # calculer_paie, lancer_paie
|   |   +-- quebec.py          # sommaire_tps_tvq, etat_dpa, etat_pret_actionnaire
|   +-- services.py            # Shared service layer (load ledger, parse pending, write)
|
+-- fava_ext/                  # Fava extensions
|   +-- approbation/           # WEB-02: Approval queue
|   |   +-- __init__.py        # ApprobationExtension(FavaExtensionBase)
|   |   +-- templates/
|   |       +-- ApprobationExtension.html
|   |
|   +-- paie_qc/               # WEB-03 part 1: Payroll dashboard
|   |   +-- __init__.py        # PaieQCExtension(FavaExtensionBase)
|   |   +-- templates/
|   |       +-- PaieQCExtension.html
|   |
|   +-- taxes_qc/              # WEB-03 part 2: GST/QST tracker
|   |   +-- __init__.py        # TaxesQCExtension(FavaExtensionBase)
|   |   +-- templates/
|   |       +-- TaxesQCExtension.html
|   |
|   +-- dpa_qc/                # WEB-03 part 3: CCA schedule
|   |   +-- __init__.py        # DpaQCExtension(FavaExtensionBase)
|   |   +-- templates/
|   |       +-- DpaQCExtension.html
|   |
|   +-- pret_actionnaire/      # WEB-03 part 4: Shareholder loan
|   |   +-- __init__.py        # PretActionnaireExtension(FavaExtensionBase)
|   |   +-- templates/
|   |       +-- PretActionnaireExtension.html
|   |
|   +-- export_cpa/            # WEB-04: CPA export (stub for Phase 5)
|       +-- __init__.py
|       +-- templates/
|           +-- ExportCPAExtension.html
```

### Pattern 1: FastMCP with Lifespan Context (MCP Server)

**What:** Use FastMCP's lifespan pattern to load the Beancount ledger once at startup and inject it into tool handlers via typed context. Reload on mutations.

**When to use:** Every MCP tool that needs ledger access.

**Example:**
```python
# Source: Context7 /modelcontextprotocol/python-sdk (verified)
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from beancount import loader
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession


@dataclass
class AppContext:
    ledger_path: str
    entries: list
    errors: list
    options: dict
    read_only: bool

    def reload(self):
        self.entries, self.errors, self.options = loader.load_file(self.ledger_path)


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    ledger_path = os.environ.get("COMPTEQC_LEDGER", "ledger/main.beancount")
    read_only = os.environ.get("COMPTEQC_READONLY", "false").lower() == "true"
    entries, errors, options = loader.load_file(ledger_path)
    yield AppContext(
        ledger_path=ledger_path,
        entries=entries, errors=errors, options=options,
        read_only=read_only,
    )


mcp = FastMCP("CompteQC", lifespan=app_lifespan)


@mcp.tool()
def query_balance(ctx: Context[ServerSession, AppContext]) -> dict:
    """Afficher la balance de verification."""
    app = ctx.request_context.lifespan_context
    # Call existing service logic
    from compteqc.mcp.services import calculer_balance
    return calculer_balance(app.entries)
```

### Pattern 2: FavaExtensionBase with Jinja2 Template (Fava Extensions)

**What:** Subclass `FavaExtensionBase`, set `report_title`, implement `after_load_file()` to compute data, and render via a Jinja2 template in `templates/ClassName.html`.

**When to use:** Every custom Fava page (payroll, GST/QST, CCA, shareholder loan, approval queue).

**Example:**
```python
# Source: Context7 /beancount/fava + Fava API docs (verified)
from fava.ext import FavaExtensionBase

class PaieQCExtension(FavaExtensionBase):
    report_title = "Paie Quebec"

    def after_load_file(self):
        """Compute payroll data when ledger reloads."""
        from compteqc.quebec.paie.ytd import calculer_ytd
        entries = self.ledger.all_entries
        self._payroll_data = calculer_ytd(entries, year=2026)

    def payroll_summary(self):
        """Called from Jinja2 template."""
        return self._payroll_data
```

Template at `templates/PaieQCExtension.html`:
```html
{% extends "fava/templates/base.html" %}
{% block content %}
<h2>Paie Quebec - Cumulatif annuel</h2>
<table class="table">
  <thead><tr><th>Cotisation</th><th>Employe</th><th>Employeur</th><th>Maximum</th></tr></thead>
  <tbody>
    {% for item in extension.payroll_summary() %}
    <tr>
      <td>{{ item.nom }}</td>
      <td>{{ item.employe }}</td>
      <td>{{ item.employeur }}</td>
      <td>{{ item.maximum }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

### Pattern 3: Shared Service Layer

**What:** Extract ledger operations (load, query balances, parse pending, write approved) into a `services.py` module that both MCP tools and Fava extensions call. This avoids duplicating logic.

**When to use:** Any operation that both MCP and Fava need.

**Example:**
```python
# src/compteqc/mcp/services.py
from decimal import Decimal
from beancount import loader
from beancount.core import data

def charger_ledger(chemin: str):
    return loader.load_file(chemin)

def lister_pending(entries: list) -> list[dict]:
    """List all #pending transactions from the ledger."""
    pending = []
    for entry in entries:
        if isinstance(entry, data.Transaction) and entry.tags and "pending" in entry.tags:
            pending.append({
                "date": str(entry.date),
                "payee": entry.payee,
                "narration": entry.narration,
                "confidence": entry.meta.get("confidence", "unknown"),
                "source": entry.meta.get("ai-source", "unknown"),
                "montant": sum(
                    p.units.number for p in entry.postings
                    if p.units and p.units.number > 0
                ),
            })
    return pending
```

### Pattern 4: Read-Only Mode via Lifespan Flag

**What:** Set `read_only` flag in the MCP server's AppContext (via environment variable at startup). Mutation tools check this flag and return an error message if enabled. Simple and explicit.

**When to use:** When user wants to safely explore the ledger without risk of accidental changes.

**Example:**
```python
@mcp.tool()
def approuver_lot(
    ids: list[str],
    ctx: Context[ServerSession, AppContext],
) -> str:
    """Approuver un lot de transactions pending."""
    app = ctx.request_context.lifespan_context
    if app.read_only:
        return "Mode lecture seule actif. Desactivez COMPTEQC_READONLY pour modifier le ledger."
    # ... proceed with approval
```

**Recommendation for discretion item:** Use `COMPTEQC_READONLY=true` environment variable (startup flag). Simpler than per-session toggle. Users set it in their Claude Desktop config for safe exploration sessions.

### Pattern 5: $2,000 Guardrail with MCP Elicitation

**What:** Transactions over $2,000 require explicit confirmation even at high confidence. The MCP tool returns a confirmation request rather than auto-approving.

**When to use:** Any auto-approval or batch-approval tool.

**Example:**
```python
SEUIL_CONFIRMATION_MONTANT = Decimal("2000")

@mcp.tool()
def approuver_lot(ids: list[str], confirmer_gros_montants: bool = False, ctx: Context = None) -> dict:
    """Approuver un lot de transactions pending."""
    # ... load pending transactions
    gros_montants = [t for t in pending if t["montant"] > SEUIL_CONFIRMATION_MONTANT]
    if gros_montants and not confirmer_gros_montants:
        return {
            "status": "confirmation_requise",
            "message": f"{len(gros_montants)} transaction(s) > 2 000 $ necessitent confirmation explicite",
            "transactions": gros_montants,
            "action": "Relancez avec confirmer_gros_montants=True pour approuver",
        }
    # ... proceed
```

### Anti-Patterns to Avoid

- **MCP server calling Fava HTTP API:** Do NOT have the MCP server call Fava's REST API to read data. Both should read the `.beancount` files directly via `loader.load_file`. Coupling to Fava's HTTP API adds a fragile dependency and requires Fava to be running.

- **Monolithic MCP tool with switch statement:** Do NOT create one giant `accounting_action(action: str, params: dict)` tool. Claude works best with specific, well-typed tools. Use one tool per logical operation.

- **JavaScript build toolchain for Fava extensions:** Do NOT use fava-dashboards or custom JS/TS for the Quebec views. The views are HTML tables with calculated numbers -- Jinja2 templates suffice. This avoids the `has_js_module` complexity and keeps the project Python-only per the HTMX/no-JS decision.

- **Storing approval state outside beancount:** Do NOT use a separate database or JSON file for the approval queue. The `#pending` tag on transactions in `pending.beancount` IS the queue. Both MCP and Fava read the same file.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP protocol handling | Custom JSON-RPC over stdio | `mcp` SDK FastMCP class | Protocol has many edge cases (initialization, capabilities negotiation, progress) |
| Web dashboard framework | Flask/FastAPI from scratch | Fava + FavaExtensionBase | Fava already has trial balance, P&L, balance sheet, journal, account views |
| Tool input validation | Manual parameter parsing | Pydantic models via FastMCP | FastMCP auto-generates JSON Schema from Python type hints |
| Ledger loading and querying | Custom file parser | `beancount.loader.load_file` | Handles includes, plugins, validation |
| HTML table rendering | Custom template system | Jinja2 via Fava | Fava already configures Jinja2 with filters for amounts, dates, accounts |

**Key insight:** The MCP server is a thin shell over existing domain modules. The Fava extensions are thin HTML views over existing domain modules. Neither should contain business logic -- they delegate to `compteqc.quebec.*`, `compteqc.categorisation.*`, and `compteqc.ledger.*`.

## Common Pitfalls

### Pitfall 1: MCP Tool Returns Too Much Data
**What goes wrong:** Claude's context window fills up with 500+ transaction details, leaving no room for reasoning.
**Why it happens:** Tools return full ledger dumps instead of summaries.
**How to avoid:** Tools return aggregated summaries by default. Add optional filters (date range, account, limit) for drill-down. Never return more than ~50 items without explicit pagination.
**Warning signs:** Tool responses exceeding 2,000 tokens.

### Pitfall 2: Stale Ledger Data After Mutations
**What goes wrong:** MCP approves a transaction but subsequent queries still show it as pending because the in-memory entries are stale.
**Why it happens:** `loader.load_file` returns a snapshot. After writing to `.beancount` files, the snapshot must be refreshed.
**How to avoid:** After any mutation (approve, reject, write payroll), call `app.reload()` to refresh the in-memory entries. For Fava, this happens automatically on the next request (Fava watches files).
**Warning signs:** Approved transactions still appearing in pending list.

### Pitfall 3: Fava Extension Template Not Found
**What goes wrong:** Fava returns 500 error or blank page for custom extension.
**Why it happens:** Template must be at `templates/ClassName.html` (exact class name match, case-sensitive) and the extension module must be importable by Fava.
**How to avoid:** Extension class name must match template file name exactly. Register extension in `main.beancount` via `custom "fava-extension" "compteqc.fava_ext.paie_qc"`. Verify the module is on `PYTHONPATH`.
**Warning signs:** Fava sidebar shows the extension but page is empty.

### Pitfall 4: MCP SDK v2 Breaking Changes
**What goes wrong:** Installing `mcp>=2` breaks the server because v2 changed the import structure.
**Why it happens:** PyPI has both v1.x and v2.x; without pinning, pip might upgrade.
**How to avoid:** Pin to `mcp>=1.25,<2` in pyproject.toml. The v2 migration guide (in SDK docs) shows `MCPServer` replacing `FastMCP` in some patterns, and transport parameters moved from constructor to `run()`. Stay on v1 until v2 stabilizes.
**Warning signs:** ImportError on `from mcp.server.fastmcp import FastMCP`.

### Pitfall 5: Concurrent File Writes from MCP and Fava
**What goes wrong:** Both MCP (approving via Claude) and Fava (approving via browser) write to the same file simultaneously, corrupting it.
**Why it happens:** No file locking between the two processes.
**How to avoid:** Use the shared service layer with file-level locking (e.g., `filelock` library or `fcntl.flock`). Alternatively, since this is a single-user system, accept the low risk and document that approvals should go through one interface at a time. The git auto-commit provides a safety net.
**Warning signs:** Garbled `.beancount` files after simultaneous edits.

### Pitfall 6: Fava Extension Missing `after_load_file` Data
**What goes wrong:** Extension page shows empty tables or crashes on first load.
**Why it happens:** `after_load_file()` did not run yet, or the extension was not registered in `main.beancount`.
**How to avoid:** Initialize `self._data = []` in `__init__` or as class attribute. Fava calls `after_load_file()` on ledger reload, but the template may render before the first load completes.
**Warning signs:** AttributeError on `self._payroll_data`.

## Code Examples

### MCP Server Entry Point (stdio for Claude Desktop/Code)
```python
# src/compteqc/mcp/server.py
# Source: Context7 /modelcontextprotocol/python-sdk (verified patterns)
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from beancount import loader
from mcp.server.fastmcp import FastMCP

@dataclass
class AppContext:
    ledger_path: str
    entries: list
    errors: list
    options: dict
    read_only: bool

    def reload(self):
        self.entries, self.errors, self.options = loader.load_file(self.ledger_path)

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    ledger_path = os.environ.get("COMPTEQC_LEDGER", "ledger/main.beancount")
    read_only = os.environ.get("COMPTEQC_READONLY", "false").lower() == "true"
    entries, errors, options = loader.load_file(ledger_path)
    yield AppContext(
        ledger_path=ledger_path,
        entries=entries, errors=errors, options=options,
        read_only=read_only,
    )

mcp = FastMCP("CompteQC", lifespan=app_lifespan)

# Import tool modules (they register via @mcp.tool())
import compteqc.mcp.tools.ledger  # noqa: F401
import compteqc.mcp.tools.categorisation  # noqa: F401
import compteqc.mcp.tools.approbation  # noqa: F401
import compteqc.mcp.tools.paie  # noqa: F401
import compteqc.mcp.tools.quebec  # noqa: F401

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "compteqc": {
      "command": "uv",
      "args": ["run", "python", "-m", "compteqc.mcp.server"],
      "env": {
        "COMPTEQC_LEDGER": "/path/to/ledger/main.beancount",
        "COMPTEQC_READONLY": "false"
      }
    }
  }
}
```

### Claude Code Configuration
```bash
claude mcp add compteqc -- uv run python -m compteqc.mcp.server
```

### Fava Extension Registration in main.beancount
```beancount
; Extensions CompteQC
2010-01-01 custom "fava-extension" "compteqc.fava_ext.approbation"
2010-01-01 custom "fava-extension" "compteqc.fava_ext.paie_qc"
2010-01-01 custom "fava-extension" "compteqc.fava_ext.taxes_qc"
2010-01-01 custom "fava-extension" "compteqc.fava_ext.dpa_qc"
2010-01-01 custom "fava-extension" "compteqc.fava_ext.pret_actionnaire"
2010-01-01 custom "fava-extension" "compteqc.fava_ext.export_cpa"
```

### MCP Tool Example: Ledger Query with Reasoning
```python
# src/compteqc/mcp/tools/ledger.py
from decimal import Decimal
from typing import Optional
from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

# Reference to the global mcp instance
from compteqc.mcp.server import mcp, AppContext


@mcp.tool()
def soldes_comptes(
    filtre: Optional[str] = None,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Afficher les soldes de tous les comptes (optionnel: filtrer par nom).

    Args:
        filtre: Sous-chaine pour filtrer les comptes (ex: "Depenses", "Actifs:Banque").
    """
    app = ctx.request_context.lifespan_context
    from compteqc.mcp.services import calculer_soldes
    soldes = calculer_soldes(app.entries)

    if filtre:
        filtre_upper = filtre.upper()
        soldes = {k: v for k, v in soldes.items() if filtre_upper in k.upper()}

    # Format for Claude
    comptes = [
        {"compte": k, "solde": str(v)}
        for k, v in sorted(soldes.items())
        if v != Decimal("0")
    ]
    return {
        "nb_comptes": len(comptes),
        "comptes": comptes[:50],  # Limit to avoid context overflow
        "tronque": len(comptes) > 50,
    }
```

### MCP Tool Example: Categorization with Reasoning
```python
# src/compteqc/mcp/tools/categorisation.py
from decimal import Decimal
from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from compteqc.mcp.server import mcp, AppContext


@mcp.tool()
def proposer_categorie(
    payee: str,
    narration: str,
    montant: str,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Proposer une categorie pour une transaction.

    Args:
        payee: Nom du beneficiaire (ex: "AMAZON", "BELL CANADA").
        narration: Description de la transaction.
        montant: Montant en CAD (ex: "45.99").
    """
    from compteqc.categorisation.pipeline import PipelineCategorisation
    # ... initialize pipeline with existing components

    resultat = pipeline.categoriser(payee, narration, Decimal(montant))

    # Build reasoning string
    if resultat.source == "regle":
        raison = f"Regle '{resultat.regle}' correspond au beneficiaire/narration"
    elif resultat.source == "ml":
        raison = f"Modele ML predit {resultat.compte} (confiance {resultat.confiance:.0%}) base sur les transactions historiques similaires"
    elif resultat.source == "llm":
        raison = f"Classification LLM: {resultat.compte} (confiance {resultat.confiance:.0%})"
    else:
        raison = "Aucun classificateur n'a pu determiner la categorie"

    return {
        "compte_propose": resultat.compte,
        "confiance": resultat.confiance,
        "source": resultat.source,
        "raison": raison,
        "est_capex": resultat.est_capex,
        "classe_dpa": resultat.classe_dpa,
        "revue_obligatoire": resultat.revue_obligatoire,
    }
```

### Fava Extension Example: Approval Queue with POST endpoint
```python
# src/compteqc/fava_ext/approbation/__init__.py
from fava.ext import FavaExtensionBase, extension_endpoint

class ApprobationExtension(FavaExtensionBase):
    report_title = "File d'approbation"

    def after_load_file(self):
        self._pending = self._charger_pending()

    def _charger_pending(self):
        from compteqc.mcp.services import lister_pending
        return lister_pending(self.ledger.all_entries)

    def pending_transactions(self):
        """Called from Jinja2 template."""
        return self._pending

    @extension_endpoint("approuver", ["POST"])
    def approuver(self):
        """POST endpoint to approve selected transactions."""
        from flask import request
        ids = request.form.getlist("ids")
        # ... approval logic
        return {"status": "ok", "approved": len(ids)}
```

## Discretion Recommendations

### Tool Granularity: Medium-Grained (10-15 tools)

**Recommendation:** Use medium-grained tools organized by domain. Not one tool per function, not one mega-tool.

Proposed tool inventory:
1. `soldes_comptes` -- query account balances with optional filter
2. `balance_verification` -- trial balance
3. `etat_resultats` -- income statement with date range
4. `bilan` -- balance sheet
5. `proposer_categorie` -- categorize a single transaction
6. `lister_pending` -- list pending transactions
7. `approuver_lot` -- batch approve transactions
8. `rejeter` -- reject a transaction (re-queues with new suggestion)
9. `calculer_paie` -- compute payroll for given gross (dry-run)
10. `lancer_paie` -- compute and write payroll to ledger
11. `sommaire_tps_tvq` -- GST/QST summary by period
12. `etat_dpa` -- CCA schedule by class
13. `etat_pret_actionnaire` -- shareholder loan status with s.15(2) deadlines

**Rationale:** Claude works best when tool names are descriptive and parameters are minimal. 13 tools is well within Claude's tool-use comfort zone. Separate read vs. write tools (calculer_paie vs lancer_paie) makes the $2,000 and confirmation guardrails easier to implement.

### Correction Flow on Reject: Re-queue with Override

**Recommendation:** When rejecting a transaction, the user (via Claude or Fava) provides the correct account. The transaction stays in `pending.beancount` with its account updated and confidence set to 1.0 + source "human". It then gets approved in the next batch. This avoids inline editing complexity.

### AI Confidence Visual Treatment: Color-Coded Badges

**Recommendation:** In Fava templates, render confidence as colored badges:
- Green (>= 95%): "regle" or high-confidence
- Yellow (80-95%): review optional
- Red (< 80%): review required
- Source tag shown as small text below the badge ("ml", "llm", "regle")

### Pending Queue: Separate Fava Page

**Recommendation:** Dedicated page via `report_title = "File d'approbation"`. The journal view should NOT be modified -- it already works well for browsing committed transactions. A separate queue page provides batch selection UI (checkboxes, select-all, approve/reject buttons).

### Dashboard Network Access: Localhost Only

**Recommendation:** Fava defaults to `127.0.0.1:5000`. Keep this default. Add a note in docs about `--host 0.0.0.0` for LAN access if needed. MCP server uses stdio (no network).

### Audit Trail: Git Auto-Commit

**Recommendation:** Rely on the existing git auto-commit mechanism from Phase 1 (`compteqc.ledger.git`). Every file write triggers a git commit with a descriptive message. This provides a complete audit trail of all mutations. No dedicated log file needed -- `git log` IS the audit trail.

### Payroll Confirmation: Always Confirm First Run, Skip for Recurring

**Recommendation:** `calculer_paie` tool always works (dry-run preview). `lancer_paie` tool writes to ledger. If the gross amount matches the previous payroll period exactly, `lancer_paie` proceeds without extra confirmation. If the amount differs, return a confirmation request (similar to the $2,000 guardrail pattern). Rationale: recurring same-salary payroll is the common case; asking for confirmation every time adds friction.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom JSON-RPC servers | MCP SDK FastMCP decorator API | 2024 | Standardized tool/resource/prompt protocol |
| SSE transport for MCP | Streamable HTTP (default) + stdio | March 2025 | HTTP is recommended for remote; stdio for local |
| Fava class `FavaExtensionBase` | Same, with `@extension_endpoint()` decorator | Fava 1.28+ | Cleaner endpoint registration |
| MCP SDK `FastMCP` constructor with transport params | Transport params moved to `run()`/`sse_app()` | MCP SDK v1.12+ | Constructor only handles identity; transport in run() |

**Deprecated/outdated:**
- `mcp.server.fastmcp.FastMCP` with transport in constructor: still works in v1.x but transport params should go in `run()` for forward compatibility
- Fava's old `endpoints` dict pattern: replaced by `@extension_endpoint()` decorator in newer versions

## Open Questions

1. **Fava extension HTMX integration**
   - What we know: Project decided "FastAPI + HTMX + Fava for web layer; no JS build toolchain". Fava extensions use Jinja2 templates.
   - What's unclear: Whether HTMX can be added to Fava extension templates without conflicting with Fava's own JavaScript. Fava uses Svelte internally.
   - Recommendation: Start with pure HTML forms (no HTMX) for the approval queue. If needed, add HTMX for partial page updates later. The approval workflow (POST form, redirect) works fine without HTMX. LOW risk item.

2. **Fava extension importability**
   - What we know: Extensions must be importable Python modules. Fava imports them by dotted name from the `custom "fava-extension"` directive.
   - What's unclear: Whether `compteqc.fava_ext.paie_qc` will resolve correctly when Fava is run as `fava ledger/main.beancount` from the project root.
   - Recommendation: Ensure `src/compteqc` is on `PYTHONPATH` or install the package in editable mode (`uv pip install -e .`). Test this early. MEDIUM risk.

3. **MCP tool response size limits**
   - What we know: Claude's context window handles tool responses. Ledger could have hundreds of transactions.
   - What's unclear: Practical limits for tool response size before Claude performance degrades.
   - Recommendation: Cap all list responses at 50 items with a `tronque` flag. Provide filter parameters (date range, account) for drill-down. LOW risk.

## Sources

### Primary (HIGH confidence)
- Context7 `/modelcontextprotocol/python-sdk` -- FastMCP API, lifespan pattern, tool decorators, transport configuration, Context injection, structured output
- Context7 `/beancount/fava` -- FavaExtensionBase, extension_endpoint, Jinja2 templates, Fava REST API, create_app options, ledger filtering

### Secondary (MEDIUM confidence)
- [PyPI mcp package](https://pypi.org/project/mcp/) -- Current version v1.26.0, confirmed v1.x/v2 split
- [PyPI fava package](https://pypi.org/project/fava/) -- Current version v1.30.11
- [Fava API docs](https://beancount.github.io/fava/api/fava.ext.html) -- FavaExtensionBase class details, hooks, attributes
- [Fava extension help](https://fava.pythonanywhere.com/example-beancount-file/help/extensions) -- Registration syntax, template naming
- [fava-dashboards](https://github.com/andreasgerstmayr/fava-dashboards) -- Reference for complex Fava extension architecture (we chose simpler Jinja2 approach)
- [MCP SDK GitHub releases](https://github.com/modelcontextprotocol/python-sdk/releases) -- Version history, migration guide

### Tertiary (LOW confidence)
- WebSearch results for Fava + HTMX integration -- no direct evidence found; treat as unvalidated

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- MCP SDK and Fava both verified via Context7 with code examples
- Architecture: HIGH -- Patterns directly from Context7 verified examples; matches existing project structure
- Pitfalls: MEDIUM -- Some pitfalls from training knowledge (concurrent writes, context size) rather than documented issues
- Discretion recommendations: MEDIUM -- Based on judgment of existing codebase patterns and MCP best practices

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable libraries, 30-day validity)
