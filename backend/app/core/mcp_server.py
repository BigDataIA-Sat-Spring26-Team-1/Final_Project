"""FastMCP tool surface for CurateAI.

Exposes the same retrieval + agent primitives as the REST API so Claude
Desktop (or any MCP client) can drive the platform. Mounted at
``/api/v1/mcp`` by ``app.main`` — the transport is SSE by default.

When you add a new tool here, keep the docstring focused on the *intent*.
That string is what the MCP client shows users — it should read like a
product description, not an implementation note.
"""
from datetime import date as _date
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
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Return the top-N personalized articles for a user.

    Ordered by the persona-weighted recommendation score. ``category`` is a
    soft filter — when provided, categories matching case-insensitively bubble
    to the top without dropping the rest. Defaults to 10 (the "personalized"
    row in the daily newsletter).
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

def _read_ranked_clusters(
    db,
    *,
    limit: int,
    status: Optional[str],
    target_date: Optional[str],
) -> List[Dict[str, Any]]:
    """Shared reader for the ranked cluster snapshot."""
    cur = db.cursor()
    query = """
        SELECT id, primary_title, primary_summary, trend_status,
               final_trend_score, cluster_size, social_popularity_score,
               category_weights, created_at
        FROM article_clusters
        WHERE final_trend_score IS NOT NULL
    """
    params: list = []
    if status:
        query += " AND UPPER(trend_status) = UPPER(%s)"
        params.append(status)
    if target_date:
        query += " AND CAST(created_at AS DATE) = %s"
        params.append(target_date)
    if target_date:
        query += " ORDER BY final_trend_score DESC, cluster_size DESC NULLS LAST LIMIT %s"
    else:
        query += " ORDER BY created_at DESC, final_trend_score DESC NULLS LAST LIMIT %s"
    params.append(limit)

    cur.execute(query, tuple(params))
    cols = [c[0].lower() for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    results: List[Dict[str, Any]] = []
    for r in rows:
        created_at = r.get("created_at")
        iso = (
            created_at.isoformat() if hasattr(created_at, "isoformat")
            else (str(created_at) if created_at is not None else None)
        )
        results.append(
            {
                "cluster_id": r["id"],
                "title": r["primary_title"],
                "summary": r["primary_summary"],
                "trend_status": r["trend_status"],
                "final_trend_score": float(r["final_trend_score"] or 0.0),
                "cluster_size": int(r["cluster_size"] or 1),
                "social_popularity_score": float(r["social_popularity_score"] or 0.0),
                "created_at": iso,
            }
        )
    return results


@mcp_server.tool()
async def get_keyword_trends(
    limit: int = 10,
    status: Optional[str] = None,
    date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the top-N ranked story clusters from the latest ranking pass.

    ``status`` filters by ``trend_status`` (BREAKING, TRENDING, VIRAL, ...).
    ``date`` (YYYY-MM-DD) pins the snapshot to a historical ranking day. This
    is a read against the ranked snapshot — it does NOT recompute the ranking.
    """
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        return _read_ranked_clusters(db, limit=limit, status=status, target_date=date)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


@mcp_server.tool()
async def get_common_highlights(
    date: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Return the top-N common trending stories for a day — same for every user.

    This is the universal "headline deck" that sits above per-user
    recommendations in the daily newsletter. Ranking is by
    ``final_trend_score`` with ``cluster_size`` as the tiebreaker so
    multi-source stories outrank single-source ones at the same score.
    ``date`` defaults to today.
    """
    target = date or _date.today().isoformat()
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        return _read_ranked_clusters(db, limit=limit, status=None, target_date=target)
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
) -> Dict[str, Any]:
    """Return today's newsletter for the user — idempotent per day.

    If a newsletter already exists for today it is served as-is (no LLM call).
    Otherwise the B2C LangGraph runs and the draft is persisted. The response
    includes the HTML, the edition date, and whether this call regenerated
    anything (``already_generated``).
    """
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        response = await generate_b2c_newsletter(
            B2CNewsletterRequest(user_id=user_id, execution_mode=mode),
            db=db,
        )
        return {
            "status": response.status,
            "html_content": response.html_content,
            "edition_date": response.edition_date,
            "generated_at": response.generated_at,
            "already_generated": response.already_generated,
            "execution_path_taken": response.execution_path_taken,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("MCP newsletter generation failed", user_id=user_id, error=str(exc))
        return {"status": "ERROR", "error": str(exc)}
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


@mcp_server.tool()
async def generate_b2b_brief(
    company_id: str,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """Return today's B2B intelligence brief for a company — idempotent per day.

    Serves the existing brief for ``date`` (defaults to today) when one exists
    in Snowflake. On a miss for today, the agent runs, persists, and returns
    the fresh brief. On a miss for a past date the response is empty — past
    days are read-only.
    """
    target = date or _date.today().isoformat()
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        cur = db.cursor()
        cur.execute(
            """
            SELECT brief_content, status, urgency_tier, generated_at, brief_date
            FROM content_briefs
            WHERE company_id = %s AND brief_date = %s
            ORDER BY generated_at DESC NULLS LAST LIMIT 1
            """,
            (company_id, target),
        )
        row = cur.fetchone()
        if row and (row[0] or "").strip():
            generated_at = row[3].isoformat() if hasattr(row[3], "isoformat") else (str(row[3]) if row[3] else None)
            brief_date = row[4].isoformat() if hasattr(row[4], "isoformat") else (str(row[4]) if row[4] else target)
            return {
                "status": row[1] or "GENERATED",
                "report": row[0],
                "urgency_tier": row[2],
                "brief_date": brief_date,
                "generated_at": generated_at,
                "already_generated": True,
            }
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    # Past-date miss: don't run the agent, just surface the empty state.
    if target != _date.today().isoformat():
        return {
            "status": "NOT_FOUND",
            "report": "",
            "brief_date": target,
            "already_generated": False,
        }

    try:
        from app.api.b2b import _persist_brief  # local import to avoid cycle at import time

        graph = get_b2b_report_graph()
        state = await graph.ainvoke({"user_id": company_id})
        content = (state or {}).get("generated_content") or ""
        if not content.strip():
            return {
                "status": "EMPTY_RESULT",
                "report": "",
                "brief_date": target,
                "already_generated": False,
            }

        db_gen2 = get_db_connection()
        db2 = next(db_gen2)
        try:
            _, generated_at = _persist_brief(
                db2,
                company_id,
                target,
                content,
                (state or {}).get("urgency_tier"),
            )
        finally:
            try:
                next(db_gen2)
            except StopIteration:
                pass

        return {
            "status": "GENERATED",
            "report": content,
            "brief_date": target,
            "generated_at": generated_at or None,
            "already_generated": False,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("MCP B2B brief generation failed", company_id=company_id, error=str(exc))
        return {"status": "ERROR", "error": str(exc)}
