from mcp.server.fastmcp import FastMCP
from app.core.logging_conf import get_logger

logger = get_logger("app.mcp_server")

# Task 23: Initialize the CurateAI MCP Server
# This server allows external LLMs to interact with our specific agent tools natively.
mcp_server = FastMCP(
    "CurateAI Intelligence",
    version="1.0.0",
    description="Ecosystem Binding for CurateAI: Exposes Newsletter Generation and Research Tools."
)

@mcp_server.tool()
async def health_check_mcp() -> str:
    """Verifies that the MCP server is alive and responding to the ecosystem."""
    return "CurateAI MCP Server is linked and healthy."
