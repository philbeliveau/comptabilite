# Stack Research

**Domain:** AI-assisted accounting/bookkeeping system for Quebec IT consultant (CCPC)
**Researched:** 2026-02-18
**Confidence:** MEDIUM-HIGH

## Core Architecture Decision: Beancount + Custom Python Layer

**Recommendation:** Use **Beancount v3** as the accounting engine with a **custom Python orchestration layer** that provides MCP server, web dashboard, CLI, and Quebec-specific modules.

**Why not HLedger:** HLedger is excellent CLI software, but building Quebec tax modules in Haskell is impractical for a solo developer. The hledger-mcp npm package (by iiAtlas) is TypeScript-only and read-heavy -- it wraps CLI commands rather than providing programmatic access to the ledger internals. You would be shelling out to `hledger` for every operation, parsing text output, and maintaining two language ecosystems (Haskell/Node for hledger, Python for ML/tax/MCP). [MEDIUM confidence -- hledger-mcp verified on npm and GitHub]

**Why not PyLedger:** PyLedger (dickhfchan/pyledger) is a young project with built-in MCP+REST+CLI, SQLite backend, and GAAP compliance claims. However: no community, no ecosystem, no plugins, unknown bus factor, and you inherit someone else's schema with no migration path. Its MCP server is a thin wrapper. Building on it means betting on one developer's continued maintenance. [MEDIUM confidence -- verified on GitHub, features confirmed]

**Why not custom ledger engine:** Double-entry accounting has subtle invariants (balanced transactions, multi-currency cost basis, lot tracking). Beancount has 10+ years of battle-testing. Building from scratch wastes months on solved problems.

**Why Beancount:** Plain-text files (auditable, diffable, versionable), Python-native (plugins are Python functions), large community, Fava web UI for browsing, beangulp import framework, smart_importer ML categorization, and a plugin system that lets you add Quebec tax validation without forking. Beancount v3 made the architecture more modular (beanquery, beangulp are now separate packages). [HIGH confidence -- verified via Context7, PyPI, official docs]

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.12+ | Runtime | Required by MCP SDK; type hints, performance improvements, match statements. 3.13 for optional free-threading. [HIGH] |
| **Beancount** | 3.x (latest on PyPI) | Double-entry ledger engine | Plain-text, Python-native plugins, 10+ year track record, active maintainer (Martin Blais). v3 is modular: core is lean, imports/queries are separate packages. [HIGH] |
| **Fava** | 1.30.x | Web interface for ledger browsing | Production-quality Beancount web UI with filtering, charts, editor. Not the approval dashboard -- use for ledger exploration. [HIGH] |
| **MCP Python SDK** | 1.26.x (`mcp` on PyPI) | MCP server for Claude integration | Official Anthropic SDK. FastMCP included. Supports tools, resources, prompts, streamable-http transport. Pin to `>=1.25,<2` until v2 stabilizes. [HIGH] |
| **FastAPI** | 0.129.x | REST API + web dashboard backend | Async, Pydantic v2 validation, auto-generated OpenAPI docs, HTMX-friendly. De facto standard for Python APIs. [HIGH] |
| **SQLite** | 3.x (stdlib) | Metadata store, cache, approval queue | For storing: import batches, approval status, classification confidence, audit trail. NOT for the ledger itself (Beancount files are the source of truth). [HIGH] |
| **uv** | 0.10.x | Package/project management | 10-100x faster than pip. Handles Python version management, lockfiles, virtual envs. Replaces pip, pip-tools, pyenv, poetry. [HIGH] |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **beangulp** | latest | Beancount import framework | Replaces old `beancount.ingest`. Write importers for RBC CSV/OFX. Modular, testable. [HIGH] |
| **beanquery** | latest | SQL-like query engine for Beancount | `SELECT account, sum(amount) WHERE ...` on your ledger. Separated from core in v3. [HIGH] |
| **smart_importer** | latest | ML-based transaction categorization | Decorator for beangulp importers. Trains on historical data, predicts accounts. Use as first-pass; LLM handles edge cases. [MEDIUM -- verified on PyPI/GitHub] |
| **ofxtools** | 0.8.22 | OFX/QFX file parsing | Pure Python, no external deps, handles OFXv1 (SGML) and v2 (XML). Better maintained than ofxparse. For RBC OFX downloads. [MEDIUM] |
| **Typer** | 0.15.x | CLI framework | Built on Click, uses type hints for auto-CLI. Cleaner than raw Click for new projects. Rich terminal output. [HIGH] |
| **Rich** | latest | Terminal formatting | Tables, progress bars, syntax highlighting for CLI output. Pairs with Typer. [HIGH] |
| **Pydantic** | 2.x | Data validation/serialization | Already a FastAPI dependency. Use for all internal data models: transactions, tax calculations, payroll records. [HIGH] |
| **HTMX** | 2.x | Frontend interactivity | 14KB JS library. Server returns HTML fragments. No React/Vue/build step needed. Perfect for approval dashboard. [MEDIUM -- pattern verified, no version pinning needed] |
| **Jinja2** | 3.x | HTML templating | FastAPI native support. Server-side renders dashboard pages for HTMX. [HIGH] |
| **Tailwind CSS** | 4.x | Styling | Utility-first CSS. Use with DaisyUI for pre-built components. No custom CSS maintenance. [MEDIUM] |
| **DaisyUI** | 5.x | UI component library | Tailwind plugin. Buttons, tables, modals, alerts out of the box. [MEDIUM] |
| **sse-starlette** | latest | Server-Sent Events | Real-time dashboard updates (import progress, approval notifications). Lighter than WebSockets. [MEDIUM] |
| **Docling** | 2.70+ | Document/receipt OCR | AI-powered PDF/image parsing. Better than raw Tesseract for structured extraction from receipts/invoices. Requires Python 3.10+. [LOW -- newer tool, evaluate vs pytesseract+Claude Vision] |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **uv** | Package management, virtual envs, Python versions | `uv init`, `uv add`, `uv run`. Replaces entire pip/poetry/pyenv toolchain. |
| **Ruff** | Linting + formatting | Replaces Black, isort, flake8. Single tool, Rust-speed. |
| **pytest** | Testing | With `pytest-asyncio` for async tests, `pytest-cov` for coverage. |
| **pre-commit** | Git hooks | Ruff + type checking on commit. |
| **mypy** or **pyright** | Type checking | Pyright is faster; mypy has broader ecosystem. Pick one. |

## Quebec-Specific Modules (Custom Build Required)

**No existing library covers Quebec payroll/tax. This is all custom code.**

| Module | What It Calculates | Data Source | Update Frequency |
|--------|-------------------|-------------|------------------|
| **qc_payroll** | QPP (4% + 1% additional), RQAP/QPIP (0.494% employee), EI QC rate (1.31%), FSS (1.25-4.26%), CNESST | CRA T4032-QC tables, Revenu Quebec TP-1015.TR | Annual (Jan 1) |
| **gst_qst** | GST (5%) + QST (9.975%) dual tracking, ITCs, ITRs, net tax calculation | CRA/RQ rates | Rarely changes |
| **cca_engine** | Capital Cost Allowance with half-year rule, class tracking, UCC schedules | CRA T2S(8) | Annual class rate updates |
| **shareholder_loan** | S15(2) tracking, prescribed interest rate, repayment within deadline | CRA quarterly prescribed rate | Quarterly |

**Architecture for tax modules:** Implement as Beancount plugins where possible (validation, auto-tagging), with standalone Python modules for calculation logic. This lets you validate ledger data at parse time AND use the same logic from CLI/API/MCP.

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Beancount v3 | HLedger 1.51 | Haskell ecosystem friction. Cannot write Quebec tax plugins in Python. hledger-mcp is read-only TypeScript wrapper. Two-language maintenance burden. |
| Beancount v3 | PyLedger | Single-developer project, no community, unknown stability. No migration path if abandoned. SQLite schema is opaque vs. plain-text. |
| Beancount v3 | Custom ledger engine | 3-6 months of work to replicate what Beancount does. Multi-currency, cost basis, lot matching are hard. |
| Beancount v3 | GnuCash | Desktop GUI app, not headless. XML/SQLite storage, no plain-text. No MCP path. Python bindings are fragile. |
| FastAPI + HTMX | React/Next.js | Overkill for approval dashboard. Adds Node.js build toolchain. HTMX achieves same UX for this use case with zero JS build step. |
| FastAPI + HTMX | Django | Django's ORM/admin are wasted -- ledger data lives in Beancount files, not Django models. FastAPI is lighter, async-native. |
| MCP Python SDK | hledger-mcp (npm) | TypeScript, shells out to hledger CLI, read-focused. Python SDK gives native access to Beancount data structures. |
| SQLite (metadata) | PostgreSQL | Solo user, local deployment. SQLite handles the metadata/queue workload. Zero ops burden. |
| uv | Poetry / pip-tools | uv is 10-100x faster, handles Python versions, and is becoming the standard. Poetry's resolver is slow and its lock format is non-standard. |
| Typer | Click | Typer is built on Click but cleaner API via type hints. For new projects in 2026, Typer is the better starting point. |
| ofxtools | ofxparse | ofxtools is actively maintained, handles both OFXv1/v2, no external dependencies. ofxparse has stale maintenance. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Ledger-CLI (C++)** | Fewer features than hledger, harder to extend, no Python integration | Beancount (Python-native) |
| **Django** | ORM-centric framework when your data source is plain-text files | FastAPI (lightweight, async) |
| **React/Vue/Angular** | Massive JS toolchain for what amounts to a table of transactions with approve/reject buttons | HTMX + Jinja2 (server-rendered) |
| **MongoDB/PostgreSQL** | Over-provisioned for solo-user metadata storage | SQLite (zero-ops) |
| **pandas** | Tempting for financial data manipulation but wrong abstraction for double-entry | Beancount's native data structures + beanquery |
| **Celery** | Task queue is overkill for single-user batch imports | Python `asyncio` or simple background threads |
| **Docker (for dev)** | Adds complexity for a single-machine Python app | `uv` manages environments directly |
| **pytesseract (alone)** | ~80% accuracy on real receipts. Needs heavy preprocessing | Docling or Claude Vision API for receipt parsing |
| **Poetry** | Slow resolver, non-standard lock format, losing mindshare to uv | uv |

## Stack Patterns by Variant

**If Claude Vision API is available for receipt parsing:**
- Skip Docling/Tesseract entirely
- Send receipt images directly to Claude via MCP
- Claude extracts structured data (date, vendor, amount, tax breakdown)
- Cheaper and more accurate for low-volume solo use

**If you want to keep Fava as the primary dashboard:**
- Skip the custom HTMX dashboard for ledger browsing
- Build only the approval/review UI in FastAPI+HTMX
- Fava handles exploration, reports, charts
- Custom dashboard handles: import queue, AI classification review, payroll runs

**If offline/air-gapped operation is required:**
- smart_importer (local ML) handles categorization instead of LLM
- Docling for local OCR instead of Claude Vision
- MCP server still works (Claude Desktop connects locally)

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Beancount 3.x | Python 3.12+ | v3 dropped some v2 APIs. Use beangulp for imports (not beancount.ingest). |
| Fava 1.30.x | Beancount 3.x | Ensure latest Fava for v3 compatibility. |
| smart_importer | Beancount 3.x | Verify compatibility -- some decorators may need beangulp adapter. |
| MCP SDK 1.26.x | Python 3.12+ | Pin `mcp>=1.25,<2`. v2 coming Q1 2026 with breaking changes. |
| FastAPI 0.129.x | Pydantic 2.x, Starlette 0.40+ | Supports both Pydantic v1 and v2 models simultaneously. |
| Docling 2.70+ | Python 3.10+ | Dropped 3.9 support. Heavy dependencies (torch). Consider optional. |

## Installation

```bash
# Initialize project with uv
uv init comptabilite
cd comptabilite

# Set Python version
uv python install 3.12
uv python pin 3.12

# Core: Ledger engine
uv add beancount fava beangulp beanquery

# Core: MCP server
uv add "mcp>=1.25,<2"

# Core: Web dashboard + API
uv add fastapi uvicorn[standard] jinja2 sse-starlette python-multipart

# Core: CLI
uv add typer rich

# Import/parsing
uv add ofxtools smart-importer

# Data validation
uv add pydantic

# Dev dependencies
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy pre-commit httpx
```

```bash
# Frontend (no npm needed for HTMX -- use CDN or vendor)
# In templates:
# <script src="https://unpkg.com/htmx.org@2.0.4"></script>
# <link href="https://cdn.jsdelivr.net/npm/daisyui@5/dist/full.min.css" rel="stylesheet">
# <script src="https://cdn.tailwindcss.com"></script>

# For production, vendor these files locally.
```

## Sources

- `/simonmichael/hledger` (Context7, 5647 snippets, High reputation) -- hledger CSV import, journal format
- `/websites/beancount_github_io_index` (Context7, 1910 snippets, High reputation, benchmark 86.7) -- Beancount plugin system, importing
- `/modelcontextprotocol/python-sdk` (Context7, 330 snippets, High reputation, benchmark 86.8) -- MCP server creation patterns
- `/beancount/smart_importer` (Context7, 26 snippets, Medium reputation, benchmark 84.9) -- ML categorization
- `/beancount/fava` (Context7, 131 snippets, Medium reputation) -- Fava web UI
- [hledger-mcp npm package](https://www.npmjs.com/package/@iiatlas/hledger-mcp) -- iiAtlas MCP server [MEDIUM]
- [PyLedger GitHub](https://github.com/dickhfchan/pyledger) -- Python accounting with MCP [MEDIUM]
- [MCP Python SDK on PyPI](https://pypi.org/project/mcp/) -- v1.26.0 current [HIGH]
- [FastAPI on PyPI](https://pypi.org/project/fastapi/) -- v0.129.0 current [HIGH]
- [hledger releases](https://github.com/simonmichael/hledger/releases) -- v1.51.2 current [HIGH]
- [Fava on PyPI](https://pypi.org/project/fava/) -- v1.30.11 current [HIGH]
- [ofxtools docs](https://ofxtools.readthedocs.io/en/latest/) -- v0.8.22 [MEDIUM]
- [CRA T4032-QC](https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4032-payroll-deductions-tables/t4032qc-jan.html) -- 2026 payroll tables [HIGH]
- [Revenu Quebec 2026 changes](https://www.revenuquebec.ca/en/businesses/source-deductions-and-employer-contributions/employers-kit/principal-changes-for-2026-employers-kit/) -- QPP/RQAP/FSS rates [HIGH]
- [Docling on PyPI](https://pypi.org/project/docling/) -- v2.70+ [LOW -- evaluate before committing]
- [uv on PyPI](https://pypi.org/project/uv/) -- v0.10.4 current [HIGH]

---
*Stack research for: AI-assisted accounting system (Quebec CCPC)*
*Researched: 2026-02-18*
