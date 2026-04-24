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

@mcp_server.tool()
async def health_check_mcp() -> str:
    return "CurateAI MCP Server is linked and healthy."

@mcp_server.tool()
async def get_user_archetype(user_id: str) -> str:

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
async def filter_articles(
    user_id: str,
    category: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:

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
        results.sort(
            key=lambda r: 0 if needle in (k.lower() for k in (r.get("categories") or {}).keys()) else 1,
        )
    return results[:limit]

def _read_ranked_clusters(
    db,
    *,
    limit: int,
    status: Optional[str],
    target_date: Optional[str],
) -> List[Dict[str, Any]]:
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

@mcp_server.tool()
async def generate_user_newsletter(
    user_id: str,
    mode: Literal["fast", "polished"] = "polished",
) -> Dict[str, Any]:

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
    except Exception as exc:
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

    if target != _date.today().isoformat():
        return {
            "status": "NOT_FOUND",
            "report": "",
            "brief_date": target,
            "already_generated": False,
        }

    try:
        from app.api.b2b import _persist_brief  

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
    except Exception as exc:  
        logger.error("MCP B2B brief generation failed", company_id=company_id, error=str(exc))
        return {"status": "ERROR", "error": str(exc)}