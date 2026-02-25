# Codebase Structure

**Analysis Date:** 2026-02-25

## Directory Layout

```
comptabilite/                        # Project root
├── src/
│   └── compteqc/                    # Main Python package (installed as "compteqc")
│       ├── __init__.py              # Version declaration
│       ├── models/                  # Shared data contracts (TransactionNormalisee)
│       ├── ingestion/               # Bank file parsers (OFX, CSV variants)
│       ├── categorisation/          # Three-tier classification pipeline
│       ├── ledger/                  # Beancount file I/O helpers
│       ├── quebec/                  # Quebec/federal tax and payroll formulas
│       │   ├── rates.py             # TauxAnnuels frozen dataclasses
│       │   ├── paie/                # Payroll calculation engine
│       │   ├── taxes/               # GST/QST calculation and summary
│       │   ├── dpa/                 # CCA/DPA schedule engine
│       │   └── pret_actionnaire/    # Shareholder loan tracking
│       ├── documents/               # Receipt/invoice extraction and linking
│       ├── echeances/               # Fiscal deadline calendar
│       ├── factures/                # Invoice generation
│       ├── rapports/                # CPA report generators (CSV + PDF)
│       │   └── templates/           # Jinja2 HTML templates + CSS
│       ├── fava_ext/                # Fava web UI extension panels
│       │   ├── approbation/         # Transaction approval queue
│       │   ├── paie_qc/             # Payroll summary panel
│       │   ├── taxes_qc/            # GST/QST summary panel
│       │   ├── dpa_qc/              # CCA/DPA panel
│       │   ├── pret_actionnaire/    # Shareholder loan panel
│       │   ├── export_cpa/          # CPA export trigger
│       │   ├── echeances/           # Fiscal deadline panel
│       │   ├── recus/               # Receipt upload panel
│       │   └── theme_qc/            # Quebec CSS theme overrides
│       ├── mcp/                     # FastMCP server for AI agent access
│       │   └── tools/               # MCP tool implementations (5 files)
│       └── cli/                     # Typer CLI subcommand modules
├── ledger/                          # Beancount ledger corpus (source of truth)
│   ├── main.beancount               # Root file: options + includes + extension declarations
│   ├── comptes.beancount            # Chart of accounts with GIFI metadata
│   ├── pending.beancount            # AI-classified transactions awaiting review
│   ├── 2025/                        # Monthly transaction files for 2025
│   │   ├── 11.beancount
│   │   └── 12.beancount
│   ├── 2026/                        # Monthly transaction files for 2026
│   │   ├── 01.beancount
│   │   └── 02.beancount
│   ├── documents/                   # Source documents linked via Beancount directives
│   │   └── 2026/02/                 # Organised by fiscal year/month
│   └── exports/                     # CPA report output directory
├── rules/                           # Classification configuration (YAML)
│   ├── categorisation.yaml          # Payee/amount rules for tier-1 classification
│   └── taxes.yaml                   # GST/QST rate rules
├── data/                            # Runtime data (not committed except .gitkeep)
│   ├── imports/                     # Drop zone for raw bank export files
│   ├── processed/YYYY-MM-DD/        # Archived imported files + SHA-256 .meta.json
│   ├── corrections/historique.json  # User correction history for rule auto-generation
│   ├── llm_log/                     # JSONL log of all LLM classification calls
│   └── ml/modele.pkl                # Trained scikit-learn model (after cqc retrain)
├── tests/                           # Test suite (pytest, co-located by concern)
│   ├── fixtures/                    # Shared test fixtures
│   └── test_*.py                    # One test file per module
├── research/                        # Architecture notes and reference documents
├── transcript/                      # Session transcripts
├── testing-documents/               # Sample PDFs/CSVs for manual testing
├── ui/                              # UI screenshots (nascent)
├── .planning/                       # GSD planning workspace
│   ├── codebase/                    # Codebase analysis documents (this file)
│   ├── phases/                      # Long-running implementation phases
│   └── quick/                       # Quick-task planning files
├── pyproject.toml                   # Package metadata, dependencies, ruff + pytest config
├── uv.lock                          # Locked dependency tree
├── .python-version                  # Pinned Python version (3.12)
├── README.md                        # Project overview
├── ARCHITECTURE-PEDAGOGIQUE.md      # Pedagogical architecture walkthrough
├── CLI-REFERENCE.md                 # CLI command reference
└── start-cmd.md                     # How to start Fava
```

## Directory Purposes

**`src/compteqc/models/`:**
- Purpose: Shared Pydantic data contracts used at all layer boundaries
- Contains: `transaction.py` — `TransactionNormalisee`, `MontantDecimal` type alias
- Key files: `src/compteqc/models/transaction.py`

**`src/compteqc/ingestion/`:**
- Purpose: Parse bank files into normalised transactions
- Contains: One file per bank format; shared normalisation utilities
- Key files: `src/compteqc/ingestion/rbc_ofx.py`, `src/compteqc/ingestion/rbc_carte.py`, `src/compteqc/ingestion/rbc_cheques.py`, `src/compteqc/ingestion/normalisation.py`

**`src/compteqc/categorisation/`:**
- Purpose: Full three-tier classification pipeline from raw transaction to routed Beancount entry
- Key files: `src/compteqc/categorisation/pipeline.py` (orchestrator), `src/compteqc/categorisation/moteur.py` (rules), `src/compteqc/categorisation/llm.py` (LLM), `src/compteqc/categorisation/pending.py` (pending queue management), `src/compteqc/categorisation/feedback.py` (correction learning)

**`src/compteqc/ledger/`:**
- Purpose: File-level Beancount I/O (monthly file creation, include injection, git commits, validation)
- Key files: `src/compteqc/ledger/fichiers.py`, `src/compteqc/ledger/validation.py`, `src/compteqc/ledger/git.py`

**`src/compteqc/quebec/`:**
- Purpose: Authoritative Quebec and federal tax/payroll domain logic, isolated for testability
- Key files: `src/compteqc/quebec/rates.py` (all rates), `src/compteqc/quebec/paie/moteur.py` (payroll engine), `src/compteqc/quebec/taxes/calcul.py` (GST/QST), `src/compteqc/quebec/dpa/calcul.py` (CCA)

**`src/compteqc/documents/`:**
- Purpose: Receipt OCR (Claude Vision), transaction matching, and Beancount document directive writing
- Key files: `src/compteqc/documents/extraction.py`, `src/compteqc/documents/matching.py`, `src/compteqc/documents/upload.py`, `src/compteqc/documents/beancount_link.py`

**`src/compteqc/rapports/`:**
- Purpose: Generate all CPA-ready reports; abstract `BaseReport` provides CSV + PDF dual output
- Key files: `src/compteqc/rapports/base.py`, `src/compteqc/rapports/cpa_package.py`, `src/compteqc/rapports/templates/`

**`src/compteqc/fava_ext/`:**
- Purpose: Inject domain panels into the Fava web dashboard via the `FavaExtensionBase` API
- Key files: `src/compteqc/fava_ext/approbation/__init__.py` (approval queue), `src/compteqc/fava_ext/recus/__init__.py` (receipt upload)

**`src/compteqc/mcp/`:**
- Purpose: FastMCP server; exposes ledger and domain operations as AI-callable tools
- Key files: `src/compteqc/mcp/server.py` (entry point), `src/compteqc/mcp/services.py` (shared read layer), `src/compteqc/mcp/tools/` (tool implementations)

**`src/compteqc/cli/`:**
- Purpose: Typer CLI application with subcommands for all operator workflows
- Key files: `src/compteqc/cli/app.py` (root app, `cqc` entry point), `src/compteqc/cli/importer.py`, `src/compteqc/cli/rapports.py`, `src/compteqc/cli/reviser.py`

**`ledger/`:**
- Purpose: The Beancount ledger corpus — the single source of truth for all financial data
- Key files: `ledger/main.beancount` (root), `ledger/comptes.beancount` (chart of accounts), `ledger/pending.beancount` (AI staging queue)

**`rules/`:**
- Purpose: User-editable YAML configuration for tier-1 classification rules
- Key files: `rules/categorisation.yaml` (auto-updated by `feedback.py` after user corrections), `rules/taxes.yaml`

**`data/`:**
- Purpose: Runtime-generated data; not committed except `.gitkeep` placeholders
- Sub-dirs: `imports/` (drop zone), `processed/` (archives), `corrections/` (history JSON), `llm_log/` (JSONL), `ml/` (model pickle)

**`tests/`:**
- Purpose: Pytest test suite with one test file per module
- Key files: `tests/test_pipeline.py`, `tests/test_categorisation.py`, `tests/test_cotisations.py`, `tests/test_taxes.py`, `tests/fixtures/`

## Key File Locations

**Entry Points:**
- `src/compteqc/cli/app.py`: CLI root — all `cqc` commands originate here
- `src/compteqc/mcp/server.py`: MCP server — `python -m compteqc.mcp.server`
- `ledger/main.beancount`: Fava entry point — declares all extensions and includes

**Configuration:**
- `pyproject.toml`: Package metadata, dependencies, ruff rules, pytest config
- `.python-version`: Python 3.12
- `rules/categorisation.yaml`: Tier-1 classification rules (editable, auto-updated)
- `rules/taxes.yaml`: Tax rate rules
- `.env`: API keys (`ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`) — never committed

**Core Logic:**
- `src/compteqc/categorisation/pipeline.py`: Central classification orchestrator
- `src/compteqc/quebec/rates.py`: All tax rates and contribution ceilings
- `src/compteqc/categorisation/pending.py`: Approval/rejection logic with rollback
- `src/compteqc/rapports/base.py`: Base class for all CPA reports

**Ledger Data:**
- `ledger/comptes.beancount`: Chart of accounts with GIFI codes — add new accounts here
- `ledger/pending.beancount`: Live pending queue — modified programmatically only
- `ledger/YYYY/MM.beancount`: Monthly approved transactions — appended by import and approval

**Testing:**
- `tests/fixtures/`: Shared fixture files (sample CSVs, Beancount snippets)
- `tests/test_pipeline.py`: Integration tests for the three-tier cascade
- `tests/test_cotisations.py`: Payroll contribution formula accuracy tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` in French (e.g., `moteur.py`, `normalisation.py`, `cotisations.py`)
- Beancount files: `main.beancount`, `comptes.beancount`, `pending.beancount` at root; `YYYY/MM.beancount` for monthly files
- Test files: `test_{module_name}.py` corresponding to the module being tested
- YAML rules: `categorisation.yaml`, `taxes.yaml` in `rules/`
- Templates: `*.html` under `templates/` sub-directories

**Directories:**
- Python packages: `snake_case` in French (e.g., `categorisation/`, `echeances/`, `pret_actionnaire/`)
- Fava extension sub-packages: named after their panel purpose (e.g., `approbation/`, `taxes_qc/`, `dpa_qc/`)

**Variables and Functions:**
- French throughout: `resultat_regles`, `chemin_main`, `approuver_transactions`, `calculer_echeances`
- Classes: PascalCase in French (e.g., `MoteurRegles`, `PipelineCategorisation`, `TransactionNormalisee`)
- Constants: SCREAMING_SNAKE_CASE (e.g., `TAUX_2026`, `SEUIL_AUTO_APPROUVE`, `SEUIL_AUTO_REGLE`)

**Beancount Accounts:**
- French account names as declared in `ledger/comptes.beancount`
- Pattern: `Type:Sous-Type:Detail` (e.g., `Actifs:Banque:RBC:Cheques`, `Passifs:Pret-Actionnaire`, `Depenses:Bureau:Logiciels`)
- Top-level types: `Actifs`, `Passifs`, `Capital`, `Revenus`, `Depenses`

## Where to Add New Code

**New bank importer:**
- Implementation: `src/compteqc/ingestion/` — create `{bank}_{format}.py` implementing `beangulp.Importer`
- Register in: `src/compteqc/cli/importer.py`
- Tests: `tests/test_importers.py`

**New expense category / account:**
- Account declaration: `ledger/comptes.beancount` — add `open` directive with GIFI metadata
- Classification rule: `rules/categorisation.yaml` — add regex rule for the payee/pattern

**New Quebec tax formula or rate:**
- Rates: `src/compteqc/quebec/rates.py` — add field to `TauxAnnuels` or create new `TauxYYYY`
- Calculation logic: appropriate sub-module under `src/compteqc/quebec/` (e.g., `paie/`, `taxes/`, `dpa/`)
- Tests: `tests/test_cotisations.py`, `tests/test_taxes.py`, or `tests/test_rates.py`

**New CPA report:**
- Implementation: `src/compteqc/rapports/` — subclass `BaseReport` from `base.py`
- Jinja2 template: `src/compteqc/rapports/templates/`
- Bundle into package: `src/compteqc/rapports/cpa_package.py`
- CLI hook: `src/compteqc/cli/cpa.py`

**New Fava panel:**
- Implementation: `src/compteqc/fava_ext/{panel_name}/__init__.py` — subclass `FavaExtensionBase`
- Jinja2 template: `src/compteqc/fava_ext/{panel_name}/templates/`
- Register: `ledger/main.beancount` — add `custom "fava-extension" "compteqc.fava_ext.{panel_name}"` directive

**New MCP tool:**
- Implementation: `src/compteqc/mcp/tools/{domain}.py` — decorate functions with `@mcp.tool()`
- Register: `src/compteqc/mcp/server.py` — add `import compteqc.mcp.tools.{domain}`
- Use shared reads: `src/compteqc/mcp/services.py`

**Utilities and shared helpers:**
- Cross-layer helpers: `src/compteqc/mcp/services.py` (ledger read functions shared between MCP and Fava)
- Normalisation utilities: `src/compteqc/ingestion/normalisation.py`

## Special Directories

**`ledger/`:**
- Purpose: The Beancount ledger corpus; this is the primary database
- Generated: Partially (monthly files and pending.beancount are written by the tool; comptes.beancount is hand-maintained)
- Committed: Yes — full git history is the audit trail

**`data/`:**
- Purpose: Runtime working data
- Generated: Yes (by the tool during import and LLM calls)
- Committed: No (only `.gitkeep` files; data/ is in `.gitignore` except corrections)

**`.planning/`:**
- Purpose: GSD planning workspace — phases, quick tasks, codebase analysis
- Generated: By GSD commands
- Committed: Yes

**`ledger/documents/`:**
- Purpose: Source documents (PDFs, images) linked to transactions via Beancount `document` directives
- Generated: By operator uploads via Fava `recus` extension
- Committed: Yes (documents are part of the audit trail)

**`tests/fixtures/`:**
- Purpose: Static test data files (CSV samples, Beancount snippets, PDF stubs)
- Generated: No (hand-created)
- Committed: Yes

---

*Structure analysis: 2026-02-25*
