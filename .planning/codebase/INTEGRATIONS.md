# External Integrations

**Analysis Date:** 2026-02-25

## APIs & External Services

**AI / LLM:**
- **OpenRouter** - LLM gateway for transaction classification
  - SDK/Client: `openai` SDK with custom `base_url`
  - Auth: `OPENROUTER_API_KEY` env var
  - Endpoint: `https://openrouter.ai/api/v1` (configurable via `OPENROUTER_BASE_URL`)
  - Model used: `anthropic/claude-sonnet-4`
  - Used in: `src/compteqc/categorisation/llm.py` (`ClassificateurLLM`)
  - Pattern: OpenAI-compatible chat completions with `response_format={"type": "json_object"}`

- **Anthropic API** - Claude Vision for receipt/document OCR
  - SDK/Client: `anthropic` SDK (direct, not via OpenRouter)
  - Auth: `ANTHROPIC_API_KEY` env var
  - Model used: `claude-sonnet-4-5-20250929`
  - Used in: `src/compteqc/documents/extraction.py` (`extraire_recu`)
  - Pattern: `messages.create()` with `tool_use` forced structured output; supports JPEG, PNG, PDF inputs via base64

**MCP (Model Context Protocol):**
- **Claude Desktop / Claude Code** - AI assistant integration
  - Server: `src/compteqc/mcp/server.py` using `FastMCP`
  - Transport: stdio (local process)
  - Tools registered: ledger queries, Quebec tax calculations, transaction categorisation, approval workflow, payroll
  - Invocation: `uv run python -m compteqc.mcp.server`
  - Config env: `COMPTEQC_LEDGER`, `COMPTEQC_READONLY`

## Data Storage

**Databases:**
- None — no SQL or NoSQL database
- All financial data stored as plain-text Beancount files under `ledger/`
  - `ledger/main.beancount` - Root entry point, includes all others
  - `ledger/comptes.beancount` - Chart of accounts
  - `ledger/pending.beancount` - Unreviewed transactions awaiting approval
  - `ledger/2026/01.beancount`, `ledger/2026/02.beancount`, etc. - Monthly transaction files
  - `ledger/2025/` - Historical year data

**File Storage:**
- Local filesystem only
- Receipts/documents stored under `ledger/documents/` organized by year/month (e.g., `ledger/documents/2026/02/`)
- Processed CSVs stored under `data/processed/`
- LLM interaction logs stored at `data/llm_log/categorisations.jsonl` (JSONL append-only audit log)
- ML model serialized to `data/ml/modele.pkl` via `joblib`
- Correction history at `data/corrections/historique.json`

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- None — single-user local tool, no authentication layer
- API keys stored in `.env` file at project root

## Bank / Financial Data Ingestion

**Royal Bank of Canada (RBC):**
- OFX/QFX files: `src/compteqc/ingestion/rbc_ofx.py` (`RBCOfxImporter`)
  - Parser: `ofxtools` library
  - Deduplication: by FITID (unique bank transaction ID)
  - Supported: chequing, savings accounts

- Credit card CSV: `src/compteqc/ingestion/rbc_carte.py` (`RBCCarteImporter`)
  - Format: RBC CSV export format

- Cheque account CSV: `src/compteqc/ingestion/rbc_cheques.py` (`RBCChequesImporter`)
  - Format: RBC chequing CSV export format

**No direct API connections** — all bank data imported via manual file export/upload.

## Monitoring & Observability

**Error Tracking:**
- None — no Sentry, Rollbar, or equivalent

**Logs:**
- Standard Python `logging` module throughout; log level not globally configured
- LLM calls: structured JSONL audit log at `data/llm_log/categorisations.jsonl`
  - Fields: timestamp, payee, narration, montant, prompt_hash, modele, compte, confiance, raisonnement, est_capex, tokens_utilises
- Fava extension audit log referenced at `logs/` directory (`.85eff129116a44980cdb3991864d331505a00edf-audit.json` detected)

## CI/CD & Deployment

**Hosting:**
- Local machine only — no cloud hosting detected

**CI Pipeline:**
- None detected — no GitHub Actions, CircleCI, or equivalent config files found

## Web UI (Fava)

**Fava Web Server:**
- Framework: Fava >= 1.30 (Flask-based)
- Serves the ledger review UI, typically at `http://localhost:5000`
- Nine custom Fava extensions registered in `ledger/main.beancount`:
  - `compteqc.fava_ext.theme_qc` - Quebec-themed UI styling
  - `compteqc.fava_ext.approbation` - Transaction approval workflow
  - `compteqc.fava_ext.paie_qc` - Quebec payroll management
  - `compteqc.fava_ext.taxes_qc` - GST/QST summaries
  - `compteqc.fava_ext.dpa_qc` - CCA (depreciation) schedule
  - `compteqc.fava_ext.pret_actionnaire` - Shareholder loan tracking
  - `compteqc.fava_ext.export_cpa` - CPA package export
  - `compteqc.fava_ext.echeances` - Tax deadline calendar
  - `compteqc.fava_ext.recus` - Receipt upload and AI extraction

**Fava Extension Endpoints (HTTP):**
- `POST /[ledger-slug]/extension/RecusExtension/upload` - Receipt file upload; triggers Claude Vision extraction
- `POST /[ledger-slug]/extension/RecusExtension/link` - Link extracted receipt to a Beancount transaction via metadata + document directive

## Report Generation

**PDF Reports:**
- Engine: WeasyPrint >= 68.1 (HTML-to-PDF)
- Templates: Jinja2 HTML in `src/compteqc/rapports/templates/`
  - `base_report.html` - Shared layout
  - `balance_verification.html` - Trial balance
  - `etat_resultats.html` - Income statement
  - `bilan.html` - Balance sheet
  - `sommaire_paie.html` - Payroll summary
  - `sommaire_dpa.html` - CCA depreciation schedule
  - `sommaire_taxes.html` - GST/QST summary
  - `sommaire_pret.html` - Shareholder loan summary
- Invoice template: `src/compteqc/factures/templates/facture.html`

**CPA Export Package:**
- Orchestrated by `src/compteqc/rapports/cpa_package.py`
- Outputs ZIP archive with all reports + GIFI S100/S125 CSV schedules
- GIFI codes embedded as Beancount metadata on account directives

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Environment Configuration

**Required env vars:**
- `OPENROUTER_API_KEY` - LLM classification (transaction categorisation)
- `ANTHROPIC_API_KEY` - Claude Vision (receipt OCR)

**Optional env vars:**
- `OPENROUTER_BASE_URL` - Default: `https://openrouter.ai/api/v1`
- `COMPTEQC_LEDGER` - Default: `ledger/main.beancount`
- `COMPTEQC_READONLY` - Default: `false`

**Secrets location:**
- `.env` file at project root (present, not committed to git per standard `.gitignore` practice)

---

*Integration audit: 2026-02-25*
