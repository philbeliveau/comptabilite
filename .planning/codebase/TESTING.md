# Testing Patterns

**Analysis Date:** 2026-04-04

## Framework And Run Shape

The project uses `pytest` with configuration from [pyproject.toml](/Users/philippebeliveau/Desktop/Notebook/comptabilite/pyproject.toml). Tests live in the top-level [tests/](/Users/philippebeliveau/Desktop/Notebook/comptabilite/tests) directory, and the repo relies on plain `assert` statements plus `pytest.raises` instead of a separate assertion library.

Typical local commands are:
```bash
uv run pytest
uv run pytest tests/test_rates.py
uv run pytest --cov=compteqc
uv run pytest -k "TestQPP"
```

## Layout And Coverage Shape

Tests are organized by source module name: `test_rates.py`, `test_importers.py`, `test_categorisation.py`, `test_ledger.py`, `test_cli.py`, `test_mcp_server.py`, and similar files covering payroll, tax, invoices, reports, receipts, and Fava/MCP integrations. The suite is broad and mostly behavior-focused, with many small test classes grouped by domain concept.

Representative mappings:
- [src/compteqc/quebec/rates.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/quebec/rates.py) -> [tests/test_rates.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/tests/test_rates.py)
- [src/compteqc/ingestion/rbc_cheques.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/ingestion/rbc_cheques.py) -> [tests/test_importers.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/tests/test_importers.py)
- [src/compteqc/mcp/server.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/mcp/server.py) -> [tests/test_mcp_server.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/tests/test_mcp_server.py)
- [src/compteqc/cli/app.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/cli/app.py) -> [tests/test_cli.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/tests/test_cli.py)

There is no shared `conftest.py`; reusable setup tends to stay local to each test file or test class. `tests/__init__.py` exists, but fixtures are usually defined inline in the file that uses them.

## Fixtures And Helpers

The suite prefers real temp files over heavy mocking when possible. `tmp_path` is used heavily for isolated ledgers, YAML registries, generated CSV/PDF outputs, and importer inputs. Files under [tests/fixtures/](/Users/philippebeliveau/Desktop/Notebook/comptabilite/tests/fixtures) provide real-format sample data, especially RBC CSV/OFX fixtures used by importer and CLI tests.

Common helper patterns:
- Module-level constants for reusable ledger text or fixture directories, as in [tests/test_mcp_server.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/tests/test_mcp_server.py) and [tests/test_importers.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/tests/test_importers.py)
- Private helper functions prefixed with `_`, such as parser/setup helpers in [tests/test_pipeline.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/tests/test_pipeline.py)
- `@pytest.fixture` for per-file setup, often returning importer instances or temp ledger roots

## Mocking And Integration Style

`unittest.mock` is the main mocking tool. `MagicMock` and `patch` are used for LLM clients, MCP mutations, and other external boundaries, while pure calculation code is generally tested with real `Decimal` values. The suite often uses real Beancount parsing from inline ledger strings rather than mocking ledger objects.

Observed patterns:
- External APIs and expensive services are mocked
- Filesystem work uses real temp directories
- `pytest.skip(...)` appears for optional or not-yet-available modules in a few integration tests
- `patch.object(...)` is preferred in some instance-level tests

## Gaps And Notes

The suite is strong on importer, payroll, categorisation, report, and MCP coverage, but it still leans on file-level fixtures and local helpers instead of centralized shared fixtures. There is no obvious marker taxonomy or broad use of `xfail`; most skipped behavior is gated inline in specific tests.

*Testing analysis refreshed: 2026-04-04*
