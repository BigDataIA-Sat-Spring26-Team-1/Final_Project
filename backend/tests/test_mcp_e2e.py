import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_mcp_sse_endpoint_availability():
    """
    Validation for Task 25: MCP E2E Connectivity.
    Verifies that the MCP SSE transport endpoint is mounted and responding.
    """
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Test that the MCP SSE endpoint is reachable
        response = await ac.get("/api/v1/mcp/sse")
        assert response.status_code != 404
        print(f"\n[SUCCESS] MCP SSE transport is active at /api/v1/mcp/sse (Status: {response.status_code})")

@pytest.mark.asyncio
async def test_mcp_tool_definitions():
    """
    Verifies that the MCP server correctly exports our reasoning tools.
    """
    from app.core.mcp_server import mcp_server
    
    # List tools directly from the server object to verify registration
    tools = await mcp_server.list_tools()
    tool_names = [t.name for t in tools]
    
    assert "generate_user_newsletter" in tool_names
    assert "get_user_archetype" in tool_names
    assert "health_check_mcp" in tool_names
    
    print(f"\n[SUCCESS] MCP Tool Schema exported: {tool_names}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_mcp_sse_endpoint_availability())
    asyncio.run(test_mcp_tool_definitions())
