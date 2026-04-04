# Codebase Concerns

**Analysis Date:** 2026-04-04

## Operational Risks

**MCP startup is brittle on ledger load failures**
- `src/compteqc/mcp/server.py:37-60` loads the ledger inside `app_lifespan()` and imports every tool module at import time.
- There is no fallback if `ledger/main.beancount` is missing, malformed, or one tool import fails.
- Impact: the entire MCP process can fail to start instead of degrading to read-only or partial functionality.
- Test gap: `tests/test_mcp_server.py` covers helper behavior, but explicitly does not test transport startup.

**Ledger validation assumes a repo checkout and local `uv`**
- `src/compteqc/ledger/validation.py:19-39` shells out to `uv run bean-check` and hard-codes `cwd=chemin_main.parent.parent`.
- `src/compteqc/ledger/git.py:10-29` depends on that validator before auto-commit.
- Impact: validation only works when the project layout matches the current repo and `uv`/`bean-check` are available on PATH.

**Pending writes are in-place and concurrency-unsafe**
- `src/compteqc/categorisation/pending.py:158-240` rewrites `pending.beancount` and monthly files directly, with rollback only after the fact.
- `src/compteqc/mcp/tools/approbation.py:178-257` also edits the same file when rejecting with corrections.
- Impact: Fava/MCP and CLI workflows can clobber each other if they touch pending state at the same time.
- Test gap: `tests/test_pending.py` covers happy-path round trips, not concurrent or partial-write failures.

**Pending transaction IDs can collide**
- `src/compteqc/mcp/tools/approbation.py:33-36` builds ids from `date|payee|narration[:20]`.
- Impact: two same-day transactions from the same payee with similar narrations can map to the same id, which makes approval/rejection ambiguous.

**Financial summaries assume a single clean posting stream**
- `src/compteqc/mcp/services.py:20-42` aggregates `posting.units.number` directly, and `src/compteqc/mcp/tools/ledger.py` consumes that result for balances, income, and balance-sheet reports.
- Impact: any non-CAD or malformed posting that reaches the ledger can distort reports silently because this layer does not group by currency or validate totals.

**Import deduplication is not enforced at the write layer**
- `src/compteqc/ingestion/normalisation.py:56-84` records a SHA-256 archive, but `src/compteqc/ledger/fichiers.py:53-65` only appends Beancount text.
- Impact: re-running an import can still duplicate transactions unless the caller performs its own duplicate check.
- Test gap: `tests/test_importers.py` checks archive metadata, not end-to-end duplicate prevention.
