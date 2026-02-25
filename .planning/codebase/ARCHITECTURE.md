# Architecture

**Analysis Date:** 2026-02-25

## Pattern Overview

**Overall:** Layered Pipeline Architecture with Plain-Text Ledger Core

**Key Characteristics:**
- Beancount (plain-text double-entry) is the single source of truth — all modules read from or write to `.beancount` files
- A three-tier categorisation cascade (Rules → ML → LLM) classifies transactions before posting
- Dual access surface: a CLI (`cqc`) for operator workflows and a Fava web UI with custom extensions for review and approval
- A FastMCP server exposes ledger read/write operations to AI agents (Claude) over stdio
- All monetary values use `Decimal` throughout; `float` is actively refused at model boundaries

## Layers

**Models Layer:**
- Purpose: Shared data contracts used across ingestion, categorisation, and ledger writing
- Location: `src/compteqc/models/`
- Contains: `TransactionNormalisee` (Pydantic), `MontantDecimal` custom type
- Depends on: Nothing internal
- Used by: Ingestion, categorisation pipeline, CLI

**Ingestion Layer:**
- Purpose: Parse bank exports into normalised transactions
- Location: `src/compteqc/ingestion/`
- Contains: `RBCOfxImporter` (OFX/QFX), `RBCCarteImporter` (CSV credit card), `RBCChequesImporter` (CSV chequing), `normalisation.py` (payee cleaning, encoding detection, file archiving)
- Depends on: `beancount`, `beangulp`, `ofxtools`, models layer
- Used by: CLI `importer` subcommand, MCP tools

**Categorisation Layer:**
- Purpose: Classify transactions into chart-of-accounts using a three-tier cascade
- Location: `src/compteqc/categorisation/`
- Contains:
  - `regles.py` — YAML rule data classes (`Regle`, `ConfigRegles`, `ConditionRegle`)
  - `moteur.py` — `MoteurRegles`: regex + amount-bound rule engine (tier 1)
  - `ml.py` — `PredicteurML`: scikit-learn text classifier trained from approved transactions (tier 2)
  - `llm.py` — `ClassificateurLLM`: OpenRouter/Claude call with structured JSON output (tier 3)
  - `capex.py` — `DetecteurCAPEX`: flags potential capital expenditures by amount and description
  - `pipeline.py` — `PipelineCategorisation`: orchestrates tiers, resolves conflicts, routes to "direct/pending/revue"
  - `pending.py` — reads/writes `pending.beancount`; handles approve/reject with rollback
  - `feedback.py` — records user corrections; auto-generates YAML rules after 2 identical corrections

**Ledger Layer:**
- Purpose: Low-level file I/O for the Beancount ledger corpus
- Location: `src/compteqc/ledger/`
- Contains: `fichiers.py` (monthly file creation and include management), `git.py` (git commit after changes), `validation.py` (load-and-validate after mutations)
- Depends on: `beancount.loader`, `beancount.parser.printer`
- Used by: categorisation pending, CLI importers, MCP mutation tools

**Quebec Domain Layer:**
- Purpose: Encode all Quebec/federal tax and payroll formulas
- Location: `src/compteqc/quebec/`
- Contains:
  - `rates.py` — `TauxAnnuels` frozen dataclass with all 2026 rates (QPP, RQAP, AE, FSS, CNESST, income tax brackets)
  - `paie/` — payroll calculation engine: `cotisations.py`, `moteur.py`, `ytd.py`, `journal.py`, `impot_federal.py`, `impot_quebec.py`
  - `taxes/` — GST/QST tracking: `calcul.py`, `sommaire.py`, `traitement.py`
  - `dpa/` — CCA/DPA schedule: `classes.py`, `calcul.py`, `registre.py`, `journal.py`
  - `pret_actionnaire/` — shareholder loan movement tracking
- Depends on: `rates.py`, `beancount.core.data`
- Used by: CLI `paie` subcommand, MCP payroll tools, reports layer

**Documents Layer:**
- Purpose: Receipt/invoice ingestion and transaction linking
- Location: `src/compteqc/documents/`
- Contains: `extraction.py` (Claude Vision API → `DonneesRecu` Pydantic model), `matching.py` (score receipt vs. transactions by amount+date), `upload.py` (save file + trigger extraction), `beancount_link.py` (write `document` directive into ledger)
- Depends on: `anthropic` SDK, `beancount.core.data`
- Used by: Fava `recus` extension, CLI `recu` subcommand

**Reports Layer:**
- Purpose: Generate CPA-ready reports as CSV + PDF
- Location: `src/compteqc/rapports/`
- Contains: `base.py` (`BaseReport` ABC with Jinja2 + WeasyPrint), `bilan.py`, `etat_resultats.py`, `sommaire_dpa.py`, `sommaire_paie.py`, `sommaire_pret.py`, `sommaire_taxes.py`, `cpa_package.py` (bundles all reports), `gifi_export.py` (GIFI code mapping for T2)
- Depends on: `jinja2`, `weasyprint`, `beancount.loader`
- Used by: CLI `cpa` subcommand, Fava `export_cpa` extension

**Fava Extensions Layer:**
- Purpose: Web UI panels embedded in the Fava dashboard
- Location: `src/compteqc/fava_ext/`
- Sub-extensions (each is a `FavaExtensionBase` subclass):
  - `approbation/` — transaction approval queue with confidence badges
  - `paie_qc/` — payroll summary panel
  - `taxes_qc/` — GST/QST summary panel
  - `dpa_qc/` — CCA/DPA schedule panel
  - `pret_actionnaire/` — shareholder loan panel
  - `export_cpa/` — CPA export trigger panel
  - `echeances/` — fiscal deadline calendar panel
  - `recus/` — receipt upload (drag-and-drop) and linking panel
  - `theme_qc/` — Quebec-themed CSS overrides
- Depends on: `fava`, `flask` (request/redirect), `mcp.services`, categorisation pending module
- Used by: `ledger/main.beancount` via `custom "fava-extension"` directives

**MCP Server Layer:**
- Purpose: Expose ledger operations to AI agents (Claude Desktop / Claude Code)
- Location: `src/compteqc/mcp/`
- Contains: `server.py` (FastMCP with lifespan that loads the ledger at startup, `AppContext` dataclass), `services.py` (shared read functions: `calculer_soldes`, `lister_pending`, `charger_ledger`), `tools/` (five tool files: `ledger.py`, `quebec.py`, `categorisation.py`, `approbation.py`, `paie.py`)
- Depends on: `mcp.server.fastmcp`, `beancount.loader`, all domain layers
- Used by: Claude via stdio (`uv run python -m compteqc.mcp.server`)

**CLI Layer:**
- Purpose: Operator command-line interface
- Location: `src/compteqc/cli/`
- Entry point: `app.py` → `cqc` console script
- Subcommands: `importer`, `paie`, `rapport`, `reviser`, `facture`, `recu`, `cpa`, `echeances`, `soldes`, `revue`, `retrain`
- Depends on: `typer`, `rich`, all domain layers
- Used by: shell operator, automated scripts

## Data Flow

**Ingestion Pipeline:**

1. Operator drops CSV/OFX file into `data/imports/`
2. `cqc importer run` identifies the file via `beangulp.Importer.identify()`
3. Importer parses rows into `TransactionNormalisee` objects (Decimal amounts, cleaned payee names)
4. For each transaction, `PipelineCategorisation.categoriser()` is called:
   - Tier 1: `MoteurRegles` checks `rules/categorisation.yaml` regexes — if matched with confidence 1.0, routes to "direct"
   - Tier 2: `PredicteurML` (if trained) predicts account from `data/ml/modele.pkl`
   - Tier 3: `ClassificateurLLM` calls OpenRouter API with system prompt including Quebec context
5. `determiner_destination()` routes each result:
   - `direct` → written immediately to monthly `.beancount` file under `ledger/YYYY/MM.beancount`
   - `pending` → written to `ledger/pending.beancount` with `#pending` tag and AI metadata
   - `revue` → written to `pending.beancount` with `revue_obligatoire=True`
6. Source file archived under `data/processed/YYYY-MM-DD/` with SHA-256 `.meta.json`
7. `ajouter_include()` updates `ledger/main.beancount` if new monthly file created

**Approval Flow:**

1. User opens Fava dashboard → `ApprobationExtension` lists all `#pending` transactions
2. Confidence badges shown: elevee (≥0.95), moderee (≥0.80), revision (<0.80)
3. User selects transactions, checks confirmation for amounts >$2,000, submits POST
4. `approuver_transactions()` moves each transaction to its monthly file, validates full ledger, rolls back on error
5. Rejected transactions are removed from `pending.beancount`
6. User corrections recorded in `data/corrections/historique.json`; after 2 identical corrections, a YAML rule is auto-generated into `rules/categorisation.yaml`

**Receipt Matching Flow:**

1. User uploads PDF/image via Fava `recus` extension drag-and-drop
2. `extraire_recu()` calls Claude Vision API; returns `DonneesRecu` (fournisseur, date, montants, taxes)
3. `proposer_correspondances()` scores all ledger transactions: 60% amount match + 40% date proximity
4. Top-5 candidates shown in Fava UI; user selects match
5. `beancount_link.py` writes a `document` directive into the ledger, linking the file path to the transaction

**Payroll Journal Entry Flow:**

1. `cqc paie calculer` accepts gross salary and fiscal year
2. `quebec/paie/moteur.py` computes QPP, RQAP, AE (employer and employee), FSS, CNESST, income tax withholdings
3. `quebec/paie/journal.py` generates the complete double-entry Beancount transaction
4. Entry written to the appropriate monthly file; payroll deductions credited to `Passifs:*` liability accounts

**State Management:**
- Primary state: `.beancount` files on disk (plain text, git-versioned)
- Pending queue: `ledger/pending.beancount` (included in `main.beancount`)
- ML model state: `data/ml/modele.pkl` (joblib-serialised scikit-learn pipeline)
- Correction history: `data/corrections/historique.json`
- LLM call log: `data/llm_log/` (JSONL per call, for drift detection)
- Fava serves live state by reloading `main.beancount` after each mutation

## Key Abstractions

**TransactionNormalisee:**
- Purpose: Common intermediate form between any source format and Beancount
- Examples: `src/compteqc/models/transaction.py`
- Pattern: Pydantic `BaseModel` with `MontantDecimal` validator that rejects `float`

**PipelineCategorisation:**
- Purpose: Orchestrate three classification tiers and produce a routing decision
- Examples: `src/compteqc/categorisation/pipeline.py`
- Pattern: Dependency-injected `MoteurRegles`, `PredicteurML`, `ClassificateurLLM`; returns `ResultatPipeline` frozen dataclass

**BaseReport:**
- Purpose: Abstract base for all CPA-ready report generators
- Examples: `src/compteqc/rapports/base.py`
- Pattern: ABC with `extract_data()`, `csv_headers()`, `csv_rows()` abstract methods; `generate()` produces both CSV and PDF

**FavaExtensionBase subclasses:**
- Purpose: Embed domain panels (approval queue, payroll, taxes, DPA, receipts) into the Fava web UI
- Examples: `src/compteqc/fava_ext/approbation/__init__.py`, `src/compteqc/fava_ext/recus/__init__.py`
- Pattern: `after_load_file()` hook for reactive state; `@extension_endpoint(name, [method])` for Flask routes

**AppContext (MCP):**
- Purpose: Shared ledger state injected into every MCP tool via FastMCP lifespan
- Examples: `src/compteqc/mcp/server.py`
- Pattern: `@asynccontextmanager` lifespan; `AppContext.reload()` called after mutations

**TauxAnnuels:**
- Purpose: Authoritative source for all tax rates and contribution ceilings for a given year
- Examples: `src/compteqc/quebec/rates.py` → `TAUX_2026`
- Pattern: Nested frozen dataclasses; accessed via `obtenir_taux(annee)` factory function

## Entry Points

**CLI (`cqc`):**
- Location: `src/compteqc/cli/app.py` → registered as `cqc` console script in `pyproject.toml`
- Triggers: Shell invocation by operator
- Responsibilities: Route to subcommand modules; hold global `--ledger` and `--regles` path options

**Fava Web Server:**
- Location: `ledger/main.beancount` (declares extensions via `custom "fava-extension"`)
- Triggers: `fava ledger/main.beancount` (or per `start-cmd.md`)
- Responsibilities: Serve read-only ledger views and host extension endpoints for approval, receipt upload, payroll, taxes, DPA, CPA export, and deadline calendar

**MCP Server:**
- Location: `src/compteqc/mcp/server.py`
- Triggers: `uv run python -m compteqc.mcp.server` (stdio transport for Claude)
- Responsibilities: Expose 5 tool groups (ledger queries, Quebec calculations, categorisation, approval, payroll) to AI agent

## Error Handling

**Strategy:** Explicit rollback on mutation failure; warn-and-continue on classification failure

**Patterns:**
- Ledger mutations (approve/reject) use a "save original, attempt change, validate full ledger, rollback on error" pattern in `src/compteqc/categorisation/pending.py`
- LLM classification errors are caught with `except Exception` and logged via `logger.warning()`, falling through to the `non-classe` result
- Beancount validation errors are logged at `logger.error()` level with full detail before rollback
- `MontantDecimal` raises `ValueError` immediately if a `float` is passed, preventing silent precision loss

## Cross-Cutting Concerns

**Logging:** Python standard `logging` throughout; each module creates `logger = logging.getLogger(__name__)`; LLM calls additionally appended to JSONL files in `data/llm_log/`

**Validation:** `pydantic>=2` for all IO boundaries (transaction model, LLM response model, receipt extraction, document correspondence); Beancount's own `loader.load_file()` validates the full ledger after every mutation

**Authentication:** None (single-user local tool); Fava and MCP server are not exposed to the internet

---

*Architecture analysis: 2026-02-25*
