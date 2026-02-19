"""Serveur MCP CompteQC -- point d'entree FastMCP avec lifespan et contexte partage.

Usage:
    uv run python -m compteqc.mcp.server          # stdio (Claude Desktop / Code)

Variables d'environnement:
    COMPTEQC_LEDGER   -- chemin vers main.beancount (default: ledger/main.beancount)
    COMPTEQC_READONLY -- mode lecture seule (default: false)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from beancount import loader
from mcp.server.fastmcp import FastMCP


@dataclass
class AppContext:
    """Contexte applicatif injecte dans chaque outil MCP via le lifespan."""

    ledger_path: str
    entries: list
    errors: list
    options: dict
    read_only: bool

    def reload(self) -> None:
        """Recharge le ledger depuis le fichier (apres une mutation)."""
        self.entries, self.errors, self.options = loader.load_file(self.ledger_path)


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Charge le ledger au demarrage du serveur et le rend disponible aux outils."""
    ledger_path = os.environ.get("COMPTEQC_LEDGER", "ledger/main.beancount")
    read_only = os.environ.get("COMPTEQC_READONLY", "false").lower() == "true"
    entries, errors, options = loader.load_file(ledger_path)
    yield AppContext(
        ledger_path=ledger_path,
        entries=entries,
        errors=errors,
        options=options,
        read_only=read_only,
    )


mcp = FastMCP("CompteQC", lifespan=app_lifespan)

# Importer les modules d'outils (ils s'enregistrent via @mcp.tool())
import compteqc.mcp.tools.ledger  # noqa: E402, F401
import compteqc.mcp.tools.quebec  # noqa: E402, F401
import compteqc.mcp.tools.categorisation  # noqa: E402, F401
import compteqc.mcp.tools.approbation  # noqa: E402, F401

if __name__ == "__main__":
    mcp.run(transport="stdio")
