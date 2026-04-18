from typing import Literal
from mcp.server.fastmcp import FastMCP

from app.api.newsletter import generate_b2c_newsletter
from app.core.schemas import B2CNewsletterRequest
from app.db.snowflake import get_db_connection
from app.repository.persona import PersonaRepository
from app.core.logging_conf import get_logger

logger = get_logger("app.mcp_server")

# Task 23: Initialize the CurateAI MCP Server
mcp_server = FastMCP("CurateAI Intelligence")

@mcp_server.tool()
async def health_check_mcp() -> str:
    """Verifies that the MCP server is alive and responding to the ecosystem."""
    return "CurateAI MCP Server is linked and healthy."

@mcp_server.tool()
async def generate_user_newsletter(user_id: str, mode: Literal["fast", "polished"] = "polished") -> str:
    """
    Triggers the LangGraph agent to generate a personalized newsletter for a specific user.
    'fast' mode skips fact-checking; 'polished' includes the full editorial review loop.
    """
    try:
        request = B2CNewsletterRequest(user_id=user_id, execution_mode=mode)
        response = await generate_b2c_newsletter(request)
        return response.html_content
    except Exception as e:
        return f"Error generating newsletter: {str(e)}"

@mcp_server.tool()
async def get_user_archetype(user_id: str) -> str:
    """
    Queries the Snowflake user_personas table to retrieve the professional archetype 
    assigned to a specific user during onboarding.
    """
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        persona = PersonaRepository.get_persona(db, user_id)
        if not persona:
            return f"No persona found for user {user_id}"
        return f"User {user_id} is classified as: {persona.get('persona_archetype', 'UNKNOWN')}"
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

