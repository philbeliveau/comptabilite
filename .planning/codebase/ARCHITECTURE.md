# Architecture

**Analysis Date:** 2026-04-04

## System Shape

**Overall:** Beancount-centered accounting stack with a layered Python application around it.

The repository is organized around a plain-text ledger corpus in `ledger/`, with Python code in `src/compteqc/` providing import, classification, Quebec tax/payroll logic, receipt/document handling, report generation, and AI-friendly access through MCP and Fava extensions.

## Core Layers

**1. Ingestion**
- Entry files: `src/compteqc/ingestion/rbc_ofx.py`, `src/compteqc/ingestion/rbc_carte.py`, `src/compteqc/ingestion/rbc_cheques.py`, `src/compteqc/ingestion/normalisation.py`
- Role: parse bank/credit-card exports into a normalized transaction model before anything touches the ledger.
- Boundary: inputs are external CSV/OFX files; outputs are `TransactionNormalisee`-style records and archived source files.

**2. Categorisation**
- Entry files: `src/compteqc/categorisation/pipeline.py`, `src/compteqc/categorisation/moteur.py`, `src/compteqc/categorisation/ml.py`, `src/compteqc/categorisation/llm.py`, `src/compteqc/categorisation/pending.py`, `src/compteqc/categorisation/feedback.py`
- Role: route transactions through rules, ML, then LLM; send low-confidence items to `ledger/pending.beancount`.
- Practical note: `pipeline.py` is the orchestration point, while `pending.py` handles review-state mutation and rollback on validation failure.

**3. Ledger I/O**
- Entry files: `src/compteqc/ledger/fichiers.py`, `src/compteqc/ledger/validation.py`, `src/compteqc/ledger/git.py`
- Role: create monthly files, append postings, manage `include` directives, and validate Beancount after writes.
- Source of truth: `ledger/main.beancount` includes the monthly files, `ledger/comptes.beancount`, and `ledger/pending.beancount`.

**4. Quebec Domain Logic**
- Entry files: `src/compteqc/quebec/rates.py`, `src/compteqc/quebec/paie/`, `src/compteqc/quebec/taxes/`, `src/compteqc/quebec/dpa/`, `src/compteqc/quebec/pret_actionnaire/`
- Role: isolate payroll, GST/QST, CCA/DPA, and shareholder-loan calculations from the rest of the app.
- Practical note: this is the best place for rate updates and formula tests because the modules are meant to stay deterministic and testable.

**5. Documents**
- Entry files: `src/compteqc/documents/extraction.py`, `src/compteqc/documents/matching.py`, `src/compteqc/documents/upload.py`, `src/compteqc/documents/beancount_link.py`
- Role: ingest receipts/invoices, extract fields, match them to transactions, and write Beancount document links.

**6. Reports**
- Entry files: `src/compteqc/rapports/base.py`, `src/compteqc/rapports/cpa_package.py`, `src/compteqc/rapports/bilan.py`, `src/compteqc/rapports/etat_resultats.py`, `src/compteqc/rapports/sommaire_*.py`
- Role: generate CPA-ready PDF/CSV outputs, including balance, income statement, payroll, taxes, DPA, and shareholder-loan summaries.
- Practical note: `cpa_package.py` is the top-level bundle builder and is the fastest way to understand how reports are assembled.

**7. Interfaces**
- CLI entry: `src/compteqc/cli/app.py`
- MCP entry: `src/compteqc/mcp/server.py`
- Fava entry: `ledger/main.beancount` through `custom "fava-extension"` directives that load packages under `src/compteqc/fava_ext/`
- Role: provide operator workflows, AI-accessible tools, and review UI panels without moving business logic into the UI layer.

## Data Flow

**Import and classify**
1. A user runs `cqc importer ...` from `src/compteqc/cli/app.py`.
2. `src/compteqc/cli/importer.py` detects the source format and parses it through the relevant importer in `src/compteqc/ingestion/`.
3. The categorisation pipeline evaluates rules, ML, and LLM candidates.
4. Approved entries are written to the current monthly Beancount file via `src/compteqc/ledger/fichiers.py`.
5. Ambiguous entries are staged in `ledger/pending.beancount` for review.

**Review and mutation**
1. Fava panels in `src/compteqc/fava_ext/approbation/`, `recus/`, `paie_qc/`, `taxes_qc/`, `dpa_qc/`, and `pret_actionnaire/` expose focused review actions.
2. Review actions call shared service code in `src/compteqc/mcp/services.py` or the categorisation/ledger helpers.
3. Ledger mutations are validated immediately; failed writes should roll back rather than leave the corpus half-updated.

**Documents and reports**
1. Uploaded receipts are extracted in `src/compteqc/documents/extraction.py`.
2. Matching logic in `src/compteqc/documents/matching.py` suggests ledger links.
3. CPA outputs are generated from `src/compteqc/rapports/` and packaged by `src/compteqc/rapports/cpa_package.py`.

## Boundaries And Contracts

- `src/compteqc/models/transaction.py` is the shared transaction contract between importers and downstream systems.
- `ledger/` is the only persistent source of financial truth; code should treat it as authoritative.
- `rules/` is user-editable configuration, but it should remain a thin rule layer, not a place for business logic.
- `tests/` provides the current contract for each subsystem and is the best reference for expected behavior when a module boundary is unclear.

## Practical Contributor Notes

- Prefer changing `src/compteqc/quebec/*` for formula logic, `src/compteqc/categorisation/*` for classification behavior, and `src/compteqc/ledger/*` for file mutations.
- If a change affects review or reporting, trace the impact from `ledger/pending.beancount` through `src/compteqc/fava_ext/` and `src/compteqc/rapports/`.
- When adding a new workflow surface, wire it through `src/compteqc/cli/app.py`, `src/compteqc/mcp/server.py`, or `ledger/main.beancount` rather than embedding it in ad hoc scripts.
