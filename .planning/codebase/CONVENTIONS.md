# Coding Conventions

**Analysis Date:** 2026-04-04

## Language And Naming

The codebase is French-first. Domain modules, classes, functions, fields, CLI labels, and error messages are usually written in French, with English mostly limited to third-party API names, package names, and a few comments/docstrings. Examples: [src/compteqc/cli/app.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/cli/app.py), [src/compteqc/models/transaction.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/models/transaction.py), [src/compteqc/categorisation/pipeline.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/categorisation/pipeline.py).

File and module names use `snake_case` and mirror business domains: `ingestion`, `categorisation`, `quebec`, `rapports`, `factures`, `documents`, `echeances`, `ledger`, `cli`, and `mcp`. Public classes stay `PascalCase` (`TransactionNormalisee`, `PipelineCategorisation`, `BaseReport`, `AppContext`), while helpers stay `snake_case` and private helpers use `_` prefixes. `__init__.py` files are mostly empty namespace markers.

## Module Organization

The repo is organized by business capability rather than technical layer. Core data flow runs through ingestion, categorisation, ledger, and reporting modules, while Quebec-specific rules live under `src/compteqc/quebec/` in payroll, taxes, DPA, and shareholder-loan subpackages. The CLI is split into small command modules under `src/compteqc/cli/`, and the MCP server registers tool modules via import side effects in `src/compteqc/mcp/server.py`.

Representative paths:
- [src/compteqc/ingestion/rbc_cheques.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/ingestion/rbc_cheques.py)
- [src/compteqc/quebec/paie/moteur.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/quebec/paie/moteur.py)
- [src/compteqc/rapports/base.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/rapports/base.py)
- [src/compteqc/mcp/server.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/mcp/server.py)

## Typing And Data Models

Pydantic v2 is used for structured DTOs and validation. The clearest example is [src/compteqc/models/transaction.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/models/transaction.py), where `TransactionNormalisee` uses `BaseModel`, explicit `Field()` metadata, and `Annotated[Decimal, BeforeValidator(...)]` to reject floats for monetary values. Immutable fiscal constants and result objects often use `@dataclass(frozen=True)`; domain modules also expose typed registries such as annual rate tables in [src/compteqc/quebec/rates.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/quebec/rates.py).

Decimal is the default for money, rates, and tax math. `Path` is the standard file-path type, and return types are explicit throughout. Union syntax uses `X | Y`, and the codebase relies on `from __future__ import annotations` in source and tests.

## CLI, Reports, And UI Patterns

Typer + Rich drive the CLI in [src/compteqc/cli/app.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/cli/app.py) and subcommands like [src/compteqc/cli/reviser.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/cli/reviser.py) and [src/compteqc/cli/aging.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/cli/aging.py). Commands generally read global ledger/regles paths from the top-level app callback, print with `Console`, and return `typer.Exit(1)` on user-facing failures.

Reports are built as small classes around [src/compteqc/rapports/base.py](/Users/philippebeliveau/Desktop/Notebook/comptabilite/src/compteqc/rapports/base.py): extract data from Beancount, render CSV, and optionally render PDF with Jinja2 + WeasyPrint. Fava extensions are separated under `src/compteqc/fava_ext/` and MCP tools are registered as import-time modules under `src/compteqc/mcp/tools/`.

## Error Handling And Logging

Modules that log create a module-level `logger = logging.getLogger(__name__)`, and logging calls use `%`-style formatting rather than f-strings. Non-fatal parsing issues are usually logged and skipped, while invalid inputs raise built-in exceptions such as `FileNotFoundError` and `ValueError` with French messages. When re-raising, the code typically preserves context with `raise ... from e`.

The common pattern is fail-fast for bad inputs, tolerate and log recoverable row-level or rule-level issues, and keep subprocess/tool calls bounded. Heavy dependencies are often imported lazily inside functions to keep module import cheap.

## Style Signals

Ruff is the formatter/linter baseline from [pyproject.toml](/Users/philippebeliveau/Desktop/Notebook/comptabilite/pyproject.toml): Python 3.12, line length 100, and `E/F/I/W` rules. Tests and application code both follow the same general shape: short helpers, small domain classes, clear module docstrings, and minimal framework abstraction.

*Convention analysis refreshed: 2026-04-04*
