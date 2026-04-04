# Technology Stack

**Analysis Date:** 2026-04-04

## Runtime

- Python 3.12+ is the application runtime (`pyproject.toml`).
- Local development uses `uv` with `uv.lock` committed and `uv_build` as the build backend.
- The main app entrypoint is the `cqc` console script (`src/compteqc/cli/app.py`).

## Core Stack

- Beancount 3.2 is the ledger engine and persistence format for all accounting data.
- `beangulp` powers the bank importers in `src/compteqc/ingestion/`.
- `beanquery` is available for Beancount-style querying and reports.
- Fava 1.30 provides the browser UI and extension host.
- Typer + Rich implement the CLI in `src/compteqc/cli/`.
- Pydantic v2 models the structured data contracts used across receipts, categorisation, payroll, AP/AR, and Quebec modules.
- WeasyPrint + Jinja2 generate PDF reports and invoices.
- Pillow is used for receipt image handling.
- `ofxtools` parses RBC OFX/QFX exports.
- `smart-importer` and scikit-learn back the ML categorisation layer.
- Anthropic and OpenAI SDKs are used for OCR and LLM classification.
- `mcp>=1.25,<2` provides the FastMCP server in `src/compteqc/mcp/server.py`.

## Repo Layout

- Ledger files live under `ledger/`:
  - `ledger/main.beancount` is the root include file.
  - `ledger/comptes.beancount` defines the chart of accounts.
  - `ledger/pending.beancount` stages uncategorised transactions.
  - `ledger/2025/*.beancount` and `ledger/2026/*.beancount` hold monthly entries.
  - `ledger/documents/` stores linked source documents.
- Rule/config sources live in `rules/` and `data/`:
  - `rules/categorisation.yaml`
  - `rules/taxes.yaml`
  - `data/actifs.yaml`
- Derived/runtime artifacts are file-based:
  - `data/llm_log/categorisations.jsonl`
  - `data/ml/modele.pkl`
  - `data/corrections/historique.json`
  - `data/processed/`

## UI And Reports

- Fava extensions live in `src/compteqc/fava_ext/`.
- Extension templates live beside each extension in `src/compteqc/fava_ext/*/templates/`.
- Report templates live in `src/compteqc/rapports/templates/`.
- Invoice templates live in `src/compteqc/factures/templates/`.
- The local UI is started from `ledger/main.beancount` via Fava, with the current extension set registered there.

## Tooling

- `pytest` is configured for `tests/` in `pyproject.toml`.
- `ruff` handles linting/formatting rules.
- `mypy` is available for static typing checks.
- `python-dotenv` loads `.env` values in modules that talk to external services.

## Notes

- This is a local-first stack: no database, no hosted backend, and no cloud deployment config detected.
- Most state is explicit and file-backed, which keeps the ledger and the planning docs easy to audit.
