# Technology Stack

**Analysis Date:** 2026-02-25

## Languages

**Primary:**
- Python 3.12+ - All application code, CLI, Fava extensions, MCP server, ML pipeline

**Secondary:**
- Beancount DSL (plain-text accounting format) - All ledger files in `ledger/`
- HTML/Jinja2 - Report templates and Fava extension UI in `src/compteqc/rapports/templates/` and `src/compteqc/fava_ext/*/templates/`
- YAML - Categorisation rules and tax config in `rules/categorisation.yaml`, `rules/taxes.yaml`

## Runtime

**Environment:**
- Python 3.12 (minimum, required by `pyproject.toml`)
- Virtual environment managed by `uv` at `.venv/`

**Package Manager:**
- `uv` (uv_build backend)
- Lockfile: `uv.lock` present and committed

## Frameworks

**Core Ledger:**
- `beancount` >= 3.2 - Plain-text double-entry accounting engine; all financial data stored as `.beancount` files
- `beangulp` >= 0.2 - Beancount importer framework; base class for `RBCOfxImporter`, `RBCChequeImporter`, `RBCCarteImporter`
- `beanquery` >= 0.2 - SQL-like query engine over Beancount entries

**Web UI:**
- `fava` >= 1.30 - Web interface for Beancount ledger; serves the review/approval UI at `http://localhost:5000`
- `flask` (transitive via fava) - Used directly in Fava extensions for request handling (`from flask import g, request`)

**CLI:**
- `typer` >= 0.24 - CLI framework; entry point `cqc` defined in `pyproject.toml`
- `rich` - Terminal output formatting, tables, progress display

**AI / ML:**
- `anthropic` >= 0.82.0 - Direct Anthropic SDK; used in `src/compteqc/documents/extraction.py` for Claude Vision receipt OCR (model: `claude-sonnet-4-5-20250929`)
- `openai` >= 2.21.0 - OpenAI-compatible SDK; pointed at OpenRouter in `src/compteqc/categorisation/llm.py` for transaction classification (model: `anthropic/claude-sonnet-4` via OpenRouter)
- `smart-importer` >= 1.2 - ML-assisted Beancount importing (transitive dependency, sklearn integration)
- `scikit-learn` (transitive via smart-importer) - SVC + CountVectorizer pipeline in `src/compteqc/categorisation/ml.py`
- `numpy` (transitive) - Array ops in ML predictor
- `scipy` (transitive) - Dependency of scikit-learn

**MCP:**
- `mcp` >= 1.25, < 2 - Model Context Protocol server; `FastMCP` instance in `src/compteqc/mcp/server.py`, runs via stdio for Claude Desktop/Code integration

**Data Validation:**
- `pydantic` >= 2 - All data models: `DonneesRecu`, `ResultatClassificationLLM`, `Facture`, `LigneFacture`, `ConfigFacturation`, `Correspondance`

**PDF/Document Generation:**
- `weasyprint` >= 68.1 - HTML-to-PDF conversion for invoice and report generation
- `jinja2` >= 3.1.6 - HTML templates for reports (`src/compteqc/rapports/templates/`) and invoices (`src/compteqc/factures/templates/`)
- `Pillow` >= 11 - Image processing for receipt upload normalization in `src/compteqc/documents/upload.py`

**File Import:**
- `ofxtools` >= 0.9 - OFX/QFX bank file parser; used in `src/compteqc/ingestion/rbc_ofx.py`

**Date/Config:**
- `python-dateutil` >= 2.9 - Date parsing for CSV importers
- `pyyaml` - YAML config loading for categorisation rules
- `python-dotenv` >= 1.2.1 - `.env` file loading in `src/compteqc/categorisation/llm.py` and `src/compteqc/documents/extraction.py`

**Testing:**
- `pytest` - Test runner; config in `pyproject.toml` (`testpaths = ["tests"]`)
- `pytest-cov` - Coverage reporting
- `freezegun` >= 1.5.5 - Time freezing for date-sensitive payroll/tax tests

**Build/Dev:**
- `ruff` - Linter and formatter; `line-length = 100`, `target-version = "py312"`, rules `E, F, I, W`
- `mypy` - Static type checking
- `uv_build` >= 0.8.5 - Build backend

**Model Persistence:**
- `joblib` (transitive) - ML model serialization in `cqc retrain` command; saves to `data/ml/modele.pkl`

## Key Dependencies

**Critical:**
- `beancount` >= 3.2 - The entire ledger persistence layer; all financial data lives in `.beancount` files
- `fava` >= 1.30 - Primary review UI; Fava extensions provide all approval, payroll, tax, DPA, and CPA export screens
- `anthropic` >= 0.82.0 - Claude Vision for receipt OCR; no alternative path if unavailable
- `mcp` >= 1.25 - Enables Claude Code/Desktop to query and mutate the ledger directly

**Infrastructure:**
- `openai` >= 2.21.0 - LLM classification backbone (routed through OpenRouter, not OpenAI directly)
- `pydantic` >= 2 - All structured data contracts between modules
- `weasyprint` >= 68.1 - PDF generation for invoices and CPA package reports

## Configuration

**Environment:**
- Loaded via `python-dotenv` at module level in LLM and extraction modules
- `.env` file present at project root (contents not read)
- Key vars referenced in code:
  - `OPENROUTER_API_KEY` - Required for LLM transaction classification
  - `OPENROUTER_BASE_URL` - OpenRouter endpoint (default: `https://openrouter.ai/api/v1`)
  - `ANTHROPIC_API_KEY` - Required for Claude Vision receipt extraction
  - `COMPTEQC_LEDGER` - Path to `main.beancount` (default: `ledger/main.beancount`)
  - `COMPTEQC_READONLY` - MCP server read-only mode flag (default: `false`)

**Build:**
- `pyproject.toml` - Project metadata, dependencies, dev groups, ruff/pytest config
- `uv.lock` - Locked dependency graph
- Package installed as `compteqc` with CLI entry point `cqc`

**Ledger:**
- `ledger/main.beancount` - Root ledger file; includes `comptes.beancount`, `pending.beancount`, monthly files
- `ledger/comptes.beancount` - Chart of accounts definitions
- `rules/categorisation.yaml` - YAML-based categorisation rules (regex pattern matching)
- `rules/taxes.yaml` - Tax configuration

## Platform Requirements

**Development:**
- Python 3.12+
- `uv` package manager
- macOS (darwin 25.3.0 confirmed); no OS-specific code detected

**Production:**
- Local-only deployment (no cloud hosting detected)
- Fava web server (`fava ledger/main.beancount`) for the review UI
- MCP server (`uv run python -m compteqc.mcp.server`) for Claude integration

---

*Stack analysis: 2026-02-25*
