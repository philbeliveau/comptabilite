"""Permet d'executer le serveur MCP via `python -m compteqc.mcp`."""

from compteqc.mcp.server import mcp

mcp.run(transport="stdio")
