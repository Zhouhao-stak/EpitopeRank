"""MCP (Model Context Protocol) integration for EpitopeRank.

Provides runtime access to external MCP servers for:
- Web search and information retrieval
- Gene/splicing database queries (Ensembl, UCSC)
- Literature search (PubMed, Europe PMC)
- Browser automation for data extraction
"""

from epitoperank.mcp.client import (
    MCPClient,
    MCPToolInfo,
    get_mcp_client,
    mcp_call_tool,
    mcp_list_servers,
)

__all__ = [
    "MCPClient",
    "MCPToolInfo",
    "get_mcp_client",
    "mcp_call_tool",
    "mcp_list_servers",
]
