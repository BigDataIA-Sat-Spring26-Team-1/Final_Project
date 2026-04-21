"""Trend endpoints.

Two shapes:
  * POST /rank  — triggers the ranker over every cluster (admin/cron action).
  * GET  /top   — reads the latest ranked snapshot for the frontend. Thin
                  query, no ranking done at read-time; whoever calls /rank
                  owns freshness.
"""
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from snowflake.connector import SnowflakeConnection

from app.core.logging_conf import get_logger
from app.db.snowflake import get_db_connection
from app.services.trend import TrendService

logger = get_logger("app.api.trend")
router = APIRouter()


@router.post("/rank", status_code=202)
async def rank_daily_news(db: SnowflakeConnection = Depends(get_db_connection)):
    """Ranks all story clusters by editorial density and social signals.

    Aggregates category weights from individual articles into cluster-level
    intelligence, then assigns BREAKING / TRENDING / REGULAR status based on
    how many independent sources confirmed the story.
    """
    logger.info("Trend ranking requested")
    try:
        results = await TrendService.rank_daily_clusters(db)
        return {
            "status": "success",
            "message": f"Ranked {results['processed']} story clusters.",
            "latency_seconds": results.get("latency", 0),
        }
    except Exception as e:
        logger.error("Trend ranking failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


def _safe_json(raw: Any) -> Optional[Dict[str, float]]:
    """Snowflake VARIANT columns come back as str OR dict depending on the driver
    setting — normalise both to a plain dict for JSON serialisation downstream."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


@router.get("/top")
async def get_top_trends(
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(
        None,
        description="Optional trend_status filter (BREAKING, TRENDING, VIRAL, …).",
    ),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, List[Dict[str, Any]]]:
    """Return the top-N most-trending clusters from the last ranking pass.

    Ordered by ``final_trend_score`` descending so the highest-velocity stories
    always sit at index 0. Clusters that have never been ranked (null score)
    are excluded — those are noise for the frontend. Empty list is a valid
    response when no clusters exist yet (fresh Snowflake, no ingestion yet).
    """
    logger.info("Trend read requested", limit=limit, status_filter=status)

    query = """
        SELECT id,
               primary_title,
               primary_summary,
               trend_status,
               final_trend_score,
               cluster_size,
               social_popularity_score,
               category_weights,
               created_at
        FROM article_clusters
        WHERE final_trend_score IS NOT NULL
    """
    params: List[Any] = []
    if status:
        query += " AND UPPER(trend_status) = UPPER(%s)"
        params.append(status)
    query += " ORDER BY final_trend_score DESC NULLS LAST LIMIT %s"
    params.append(limit)

    try:
        cur = db.cursor()
        cur.execute(query, tuple(params))
        cols = [c[0].lower() for c in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        logger.error("Trend read failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    results = [
        {
            "cluster_id": r["id"],
            "title": r["primary_title"],
            "summary": r["primary_summary"],
            "trend_status": r["trend_status"],
            "final_trend_score": float(r["final_trend_score"])
            if r["final_trend_score"] is not None
            else 0.0,
            "cluster_size": int(r["cluster_size"]) if r["cluster_size"] is not None else 1,
            "social_popularity_score": float(r["social_popularity_score"] or 0.0),
            "categories": _safe_json(r["category_weights"]) or {},
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]
    return {"total": len(results), "results": results}
