# External Integrations

**Analysis Date:** 2026-04-04

## AI Services

- OpenRouter is the LLM gateway for transaction categorisation.
  - Code: `src/compteqc/categorisation/llm.py`
  - SDK: `openai` client with custom `base_url`
  - Env: `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`
  - Output audit trail: `data/llm_log/categorisations.jsonl`
- Anthropic is used directly for receipt OCR / structured extraction.
  - Code: `src/compteqc/documents/extraction.py`
  - Env: `ANTHROPIC_API_KEY`
  - Called by CLI receipt upload and the Fava receipt extension
    (`src/compteqc/cli/receipt.py`, `src/compteqc/fava_ext/recus/`)

## MCP / Claude Integration

- The local MCP server is `src/compteqc/mcp/server.py`.
  - Transport: stdio
  - Run command: `uv run python -m compteqc.mcp.server`
  - Env: `COMPTEQC_LEDGER`, `COMPTEQC_READONLY`
- MCP tool modules:
  - `src/compteqc/mcp/tools/ledger.py`
  - `src/compteqc/mcp/tools/quebec.py`
  - `src/compteqc/mcp/tools/categorisation.py`
  - `src/compteqc/mcp/tools/approbation.py`
  - `src/compteqc/mcp/tools/paie.py`
  - `src/compteqc/mcp/tools/apar.py`
- The server currently exposes ledger, Quebec, categorisation, approval, payroll, and AP/AR tools directly from the Beancount file in memory.

## Bank And Financial Imports

- RBC OFX/QFX import:
  - `src/compteqc/ingestion/rbc_ofx.py`
  - Uses `ofxtools.Parser.OFXTree`
  - Matches the target account by RBC account ID and deduplicates via FITID
- RBC CSV import:
  - `src/compteqc/ingestion/rbc_cheques.py`
  - `src/compteqc/ingestion/rbc_carte.py`
  - Supports combined CSV exports containing both cheque and Visa rows
- Import orchestration:
  - `src/compteqc/cli/importer.py`
  - Adds new monthly files via `src/compteqc/ledger/fichiers.py`
  - Validates and optionally auto-commits via `src/compteqc/ledger/validation.py` and `src/compteqc/ledger/git.py`
- There are no direct bank APIs; the system expects manual CSV/OFX exports.

## Document Ingestion

- Receipt upload and storage:
  - CLI: `src/compteqc/cli/receipt.py`
  - Storage helper: `src/compteqc/documents/upload.py`
  - OCR/extraction: `src/compteqc/documents/extraction.py`
  - Matching: `src/compteqc/documents/matching.py`
  - Beancount document linking: `src/compteqc/documents/beancount_link.py`
- Receipt files are stored under `ledger/documents/YYYY/MM/` and renamed to a date/vendor slug format.
- Fava receipt endpoints are wired in `ledger/main.beancount` through `compteqc.fava_ext.recus`.
  - Visible endpoints in the extension templates use `/extension/RecusExtension/upload` and `/extension/RecusExtension/link`.

## Fava Extensions

- `ledger/main.beancount` registers 12 custom Fava extensions:
  - `compteqc.fava_ext.theme_qc`
  - `compteqc.fava_ext.tableau_bord`
  - `compteqc.fava_ext.approbation`
  - `compteqc.fava_ext.paie_qc`
  - `compteqc.fava_ext.taxes_qc`
  - `compteqc.fava_ext.dpa_qc`
  - `compteqc.fava_ext.pret_actionnaire`
  - `compteqc.fava_ext.export_cpa`
  - `compteqc.fava_ext.echeances`
  - `compteqc.fava_ext.recus`
  - `compteqc.fava_ext.operations`
  - `compteqc.fava_ext.comptes_fournisseurs`
- `src/compteqc/fava_ext/operations/__init__.py` is the main browser-side integration point for import, retrain, and journal review.
- `src/compteqc/fava_ext/export_cpa/__init__.py` and `src/compteqc/rapports/cpa_package.py` generate the accountant handoff package.

## File-Based State

- Rules, tax settings, and asset registers are all file-backed:
  - `rules/categorisation.yaml`
  - `rules/taxes.yaml`
  - `data/actifs.yaml`
- Learning and review state is persisted locally:
  - `data/corrections/historique.json`
  - `data/ml/modele.pkl`
  - `data/llm_log/categorisations.jsonl`
- Operational Beancount artifacts include:
  - `ledger/pending.beancount`
  - `ledger/fournisseurs/journal.beancount`
  - `ledger/2025/*.beancount`
  - `ledger/2026/*.beancount`

## Reporting And Export

- PDF reports are rendered from `src/compteqc/rapports/templates/` with WeasyPrint.
- CPA exports are assembled in `src/compteqc/rapports/cpa_package.py` and surfaced in Fava/CLI.
- GIFI-style exports and Beancount-linked document paths are used for the year-end package rather than any external accounting SaaS.

## External Providers Observed

- OpenRouter
- Anthropic
- RBC file exports

No other hosted provider, payment API, or cloud database integration was detected in the current codebase.
