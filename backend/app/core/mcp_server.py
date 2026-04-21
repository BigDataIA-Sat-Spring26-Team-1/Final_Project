from typing import Literal
from mcp.server.fastmcp import FastMCP

from app.api.newsletter import generate_b2c_newsletter
from app.core.schemas import B2CNewsletterRequest
from app.db.snowflake import get_db_connection
from app.repository.persona import PersonaRepository
from app.core.logging_conf import get_logger
from app.services.search import SearchService
from app.services.trend import TrendService
from app.services.b2b_agent import get_b2b_report_graph

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

@mcp_server.tool()
async def filter_articles(user_id: str, category: str, limit: int = 5) -> str:
    """
    Retrieves personalized recommended articles for a user.
    'category' filter is currently advisory as search is persona-driven.
    """
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        recommendations = await SearchService.get_personalized_recommendations(user_id, limit, db)
        if not recommendations:
            return f"No recommendations found for user {user_id}"
        return f"Top recommendations for {user_id}: {str(recommendations.get('results', []))}"
    except Exception as e:
        return f"Error filtering articles: {str(e)}"
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

@mcp_server.tool()
async def get_keyword_trends(company_id: str, time_window: str = "24h") -> str:
    """
    Analyzes global cluster updates to rank breaking trends.
    'company_id' and 'time_window' are advisory for future scoped filtering.
    """
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        results = await TrendService.rank_daily_clusters(db)
        return f"Daily trend ranking complete. Processed {results.get('processed', 0)} clusters."
    except Exception as e:
        return f"Error fetching trends: {str(e)}"
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

@mcp_server.tool()
async def generate_b2b_brief(user_id: str) -> str:
    """
    Invokes the B2B Reporting LangGraph to generate an enterprise-level intelligence brief.
    """
    try:
        graph = get_b2b_report_graph()
        result = await graph.ainvoke({"user_id": user_id})
        return str(result.get("generated_content", "No content generated."))
    except Exception as e:
        return f"Error generating B2B brief: {str(e)}"

if __name__ == "__main__":
    # Allows the server to be run standalone for ecosystem debugging
    mcp_server.run()

