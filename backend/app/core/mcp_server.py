"""FastMCP tool surface for CurateAI.

Exposes the same retrieval + agent primitives as the REST API so Claude
Desktop (or any MCP client) can drive the platform. Mounted at
``/api/v1/mcp`` by ``app.main`` — the transport is SSE by default.

When you add a new tool here, keep the docstring focused on the *intent*.
That string is what the MCP client shows users — it should read like a
product description, not an implementation note.
"""
from typing import Any, Dict, List, Literal, Optional

from mcp.server.fastmcp import FastMCP

from app.api.newsletter import generate_b2c_newsletter
from app.core.logging_conf import get_logger
from app.core.schemas import B2CNewsletterRequest
from app.db.snowflake import get_db_connection
from app.repository.persona import PersonaRepository
from app.services.b2b_agent import get_b2b_report_graph
from app.services.search import SearchService

logger = get_logger("app.mcp_server")

mcp_server = FastMCP("CurateAI Intelligence")


# ---- System --------------------------------------------------------------

@mcp_server.tool()
async def health_check_mcp() -> str:
    """Return a heartbeat string — useful as a connectivity probe from Claude."""
    return "CurateAI MCP Server is linked and healthy."


# ---- Personas ------------------------------------------------------------

@mcp_server.tool()
async def get_user_archetype(user_id: str) -> str:
    """Return the professional archetype assigned to a user at onboarding.

    Values are one of: ML_RESEARCHER, AI_SYSTEMS_ENGINEER, DATA_STRATEGIST,
    PRODUCT_LEAD_AI, POLICY_ETHICS_GURU, GENERAL_TECH_ENVELOPE.
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


# ---- Retrieval -----------------------------------------------------------

@mcp_server.tool()
async def filter_articles(
    user_id: str,
    category: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return personalized recommendations for a user, optionally filtered by category.

    ``category`` is a soft filter: when provided, results whose ``categories``
    payload contains that key (case-insensitive) bubble to the top. When
    omitted the response is a pure relevance ranking driven by the user's
    persona weights.
    """
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        result = await SearchService.get_personalized_recommendations(user_id, limit * 2, db)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    if not result:
        return []

    results = result.get("results", [])
    if category:
        needle = category.strip().lower()
        # Stable sort pushes category matches up without discarding the rest,
        # so callers can still see adjacent clusters when the filter is sparse.
        results.sort(
            key=lambda r: 0 if needle in (k.lower() for k in (r.get("categories") or {}).keys()) else 1,
        )
    return results[:limit]


# ---- Trends --------------------------------------------------------------

@mcp_server.tool()
async def get_keyword_trends(
    limit: int = 10,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the top-N ranked story clusters from the latest ranking pass.

    ``status`` filters by ``trend_status`` (BREAKING, TRENDING, VIRAL, ...).
    This is a read against the ranked snapshot — it does NOT recompute the
    ranking; use a DAG trigger for that.
    """
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        cur = db.cursor()
        query = """
            SELECT id, primary_title, trend_status, final_trend_score, cluster_size
            FROM article_clusters
            WHERE final_trend_score IS NOT NULL
        """
        params: list = []
        if status:
            query += " AND UPPER(trend_status) = UPPER(%s)"
            params.append(status)
        query += " ORDER BY final_trend_score DESC LIMIT %s"
        params.append(limit)
        cur.execute(query, tuple(params))
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


# ---- Generation ----------------------------------------------------------

@mcp_server.tool()
async def generate_user_newsletter(
    user_id: str,
    mode: Literal["fast", "polished"] = "polished",
) -> str:
    """Run the B2C LangGraph and return the rendered HTML newsletter.

    ``fast`` skips the editor review loop for demos; ``polished`` runs the
    full writer/editor cycle with revision.
    """
    try:
        response = await generate_b2c_newsletter(
            B2CNewsletterRequest(user_id=user_id, execution_mode=mode)
        )
        return response.html_content
    except Exception as exc:  # noqa: BLE001 — surfaced to the caller as a string
        logger.error("MCP newsletter generation failed", user_id=user_id, error=str(exc))
        return f"Error generating newsletter: {exc}"


@mcp_server.tool()
async def generate_b2b_brief(company_id: str) -> str:
    """Run the B2B research agent and return the Markdown intelligence brief.

    ``company_id`` is the corporate tenant identifier (``companies.id``).
    The agent retrieves cross-cluster signals, scores them with the 4-signal
    urgency algorithm, and emits a structured executive briefing.
    """
    try:
        graph = get_b2b_report_graph()
        # The agent state uses ``user_id`` for the tenant key — legacy naming
        # that predates the B2C/B2B split but it remains the contract.
        state = await graph.ainvoke({"user_id": company_id})
        content = (state or {}).get("generated_content") or ""
        return content or "Agent returned an empty brief."
    except Exception as exc:  # noqa: BLE001
        logger.error("MCP B2B brief generation failed", company_id=company_id, error=str(exc))
        return f"Error generating brief: {exc}"
