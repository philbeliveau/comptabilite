# Codebase Structure

**Analysis Date:** 2026-04-04

## Repository Layout

```
comptabilite/
├── src/
│   └── compteqc/
│       ├── cli/                    # Typer CLI entry point and subcommands
│       ├── mcp/                    # FastMCP server, shared services, tool handlers
│       ├── ingestion/              # RBC file importers and normalization
│       ├── categorisation/         # Rules, ML, LLM, CAPEX, pending/review flow
│       ├── ledger/                 # Beancount file creation, append, validation, git
│       ├── models/                 # Shared data contracts
│       ├── documents/              # Receipt/invoice extraction and Beancount links
│       ├── quebec/                 # Payroll, taxes, DPA/CCA, shareholder loan logic
│       ├── rapports/               # CPA reports and ZIP packaging
│       ├── fava_ext/               # Fava panels and UI extensions
│       ├── factures/               # Client invoice generation and recurring invoice support
│       ├── fournisseurs/           # AP/vendor tracking and journals
│       └── echeances/              # Filing deadline and reminder logic
├── ledger/                         # Plain-text Beancount corpus and attached documents
├── rules/                          # YAML configuration for categorization and tax rules
├── tests/                          # Pytest suite and fixtures
├── docs/                           # Design notes and longer-form documentation
├── research/                       # Exploratory notes and references
├── transcript/                     # Session transcripts and conversational history
├── ui/                             # UI assets/screenshots
├── screenshots/                    # Additional captured screens
├── testing-documents/              # Manual testing inputs and sample documents
├── .planning/                      # Planning state and codebase maps
├── pyproject.toml                  # Package metadata, dependencies, test/ruff config
└── uv.lock                         # Locked dependency graph
```

## Where Responsibilities Live

**`src/compteqc/cli/`**
- `app.py` wires the `cqc` root command and registers subcommands.
- `importer.py`, `paie.py`, `rapports.py`, `reviser.py`, `facture.py`, `receipt.py`, `cpa.py`, `fournisseur.py`, and `aging.py` hold the operator-facing workflows.

**`src/compteqc/mcp/`**
- `server.py` is the executable MCP entry point.
- `services.py` contains shared read helpers used by MCP tools and some UI code.
- `tools/` groups tool implementations by concern: ledger, Quebec domain, categorisation, approvals, and payroll.

**`src/compteqc/categorisation/`**
- `pipeline.py` is the orchestration layer.
- `moteur.py`, `ml.py`, and `llm.py` implement the three classification tiers.
- `pending.py` and `feedback.py` manage review state and learning from corrections.
- `capex.py` flags likely capital assets.

**`src/compteqc/ledger/`**
- `fichiers.py` handles monthly file creation, includes, and text appends.
- `validation.py` wraps Beancount validation and account discovery.
- `git.py` handles repo-side ledger commits after successful mutations.

**`src/compteqc/quebec/`**
- `rates.py` centralizes yearly rate tables.
- `paie/` handles payroll calculations and journal entries.
- `taxes/` handles GST/QST summaries and calculations.
- `dpa/` handles capital cost allowance schedules and journals.
- `pret_actionnaire/` tracks shareholder-loan state and alerts.

**`src/compteqc/documents/`**
- `extraction.py` parses receipts/invoices.
- `matching.py` suggests ledger matches.
- `upload.py` coordinates file storage and extraction.
- `beancount_link.py` writes document links back into the ledger.

**`src/compteqc/rapports/`**
- `base.py` defines the shared report interface.
- `cpa_package.py` assembles the year-end ZIP package.
- `bilan.py`, `etat_resultats.py`, `balance_verification.py`, `sommaire_*.py`, and `gifi_export.py` generate the output artifacts.
- `templates/` holds the HTML and CSS used for PDF generation.

**`src/compteqc/fava_ext/`**
- Each subpackage is a Fava extension panel with its own `__init__.py` and templates.
- `approbation/`, `recus/`, `paie_qc/`, `taxes_qc/`, `dpa_qc/`, `pret_actionnaire/`, `export_cpa/`, `echeances/`, `operations/`, `comptes_fournisseurs/`, `tableau_bord/`, `chat/`, and `theme_qc/` are the notable panels/themes.

**`ledger/`**
- `main.beancount` is the root file and Fava entry point.
- `comptes.beancount` contains the chart of accounts.
- `pending.beancount` is the review queue.
- `YYYY/MM.beancount` files hold approved monthly postings.
- `documents/` stores source PDFs and receipts, organized by date.

**`tests/`**
- Tests are grouped by feature rather than by layer.
- Fixtures live in `tests/fixtures/`.
- High-signal files include `test_pipeline.py`, `test_cotisations.py`, `test_taxes.py`, `test_documents.py`, `test_cpa_package.py`, `test_mcp_server.py`, and `test_fava_ext.py`.

## Naming And Layout Patterns

- Python modules are mostly `snake_case.py` with French domain names where the business logic is accounting-specific.
- Subpackages mirror domain boundaries rather than transport boundaries.
- Beancount monthly files use `ledger/YYYY/MM.beancount`.
- Templates always live under `templates/` inside the feature package that owns them.
- Test files follow `test_*.py` and usually map directly to the module under test.

## Contributor Hints

- Start in `src/compteqc/cli/app.py` when tracking a command path.
- Start in `src/compteqc/mcp/server.py` when tracking AI-accessible operations.
- Start in `ledger/main.beancount` when tracing what Fava can see.
- Start in `src/compteqc/rapports/cpa_package.py` when tracing year-end export output.
