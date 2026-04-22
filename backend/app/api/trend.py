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

from app.core.airflow_client import AirflowUnavailable, trigger_dag
from app.core.logging_conf import get_logger
from app.core.schemas import DAGTriggerResponse
from app.db.snowflake import get_db_connection

logger = get_logger("app.api.trend")
router = APIRouter()


@router.post("/rank", status_code=202, response_model=DAGTriggerResponse)
async def rank_daily_news() -> DAGTriggerResponse:
    """Schedule the trend-ranking DAG.

    The ranker runs on the VM so a long Snowflake query never blocks a Cloud
    Run request. The DAG writes results back to ``article_clusters`` which the
    /top endpoint reads directly.
    """
    logger.info("Trend ranking DAG trigger requested")
    try:
        run = await trigger_dag("trend_dag")
    except AirflowUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return DAGTriggerResponse(
        status="ACCEPTED",
        message="Trend ranking DAG scheduled.",
        dag_id="trend_dag",
        dag_run_id=run.get("dag_run_id", ""),
        state=run.get("state"),
    )


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
    date: Optional[str] = Query(
        None,
        description=(
            "Optional YYYY-MM-DD filter on the cluster's created_at. Useful "
            "for historical views: pass yesterday to see what was trending "
            "when the last batch ran."
        ),
    ),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:  # noqa: the mixed shape (total:int, results:list) would trip FastAPI's response validation under a stricter annotation.
    """Return the top-N most-trending clusters from the last ranking pass.

    Ordered by ``final_trend_score`` descending so the highest-velocity stories
    always sit at index 0. Clusters that have never been ranked (null score)
    are excluded — those are noise for the frontend. Empty list is a valid
    response when no clusters exist yet (fresh Snowflake, no ingestion yet).
    """
    logger.info("Trend read requested", limit=limit, status_filter=status)

    # A "velocity" that doesn't compare two days is dishonest — the UI used
    # to hack it from cluster_size vs score. Instead we join per-cluster
    # article counts for the selected day (curr) and the day before (prev),
    # so the frontend can show real temporal motion. If no date is given we
    # default to today so the endpoint still works for the public /trending
    # page that doesn't pick a date.
    from datetime import date as _date, timedelta

    target_day = date or _date.today().isoformat()
    prev_day = (_date.fromisoformat(target_day) - timedelta(days=1)).isoformat()

    query = """
        WITH curr_counts AS (
            SELECT cluster_id, COUNT(*) AS n
            FROM articles_raw
            WHERE CAST(fetched_at AS DATE) = %s
              AND cluster_id IS NOT NULL
            GROUP BY cluster_id
        ),
        prev_counts AS (
            SELECT cluster_id, COUNT(*) AS n
            FROM articles_raw
            WHERE CAST(fetched_at AS DATE) = %s
              AND cluster_id IS NOT NULL
            GROUP BY cluster_id
        )
        SELECT c.id,
               c.primary_title,
               c.primary_summary,
               c.trend_status,
               c.final_trend_score,
               c.cluster_size,
               c.social_popularity_score,
               c.category_weights,
               c.created_at,
               COALESCE(cc.n, 0) AS curr_day_count,
               COALESCE(pc.n, 0) AS prev_day_count
        FROM article_clusters c
        LEFT JOIN curr_counts cc ON cc.cluster_id = c.id
        LEFT JOIN prev_counts pc ON pc.cluster_id = c.id
        WHERE c.final_trend_score IS NOT NULL
    """
    params: List[Any] = [target_day, prev_day]
    if status:
        query += " AND UPPER(c.trend_status) = UPPER(%s)"
        params.append(status)
    if date:
        # created_at is a TIMESTAMP_NTZ; cast to DATE for an index-friendly compare.
        query += " AND CAST(c.created_at AS DATE) = %s"
        params.append(date)
    query += " ORDER BY c.final_trend_score DESC NULLS LAST LIMIT %s"
    params.append(limit)

    # One try/except around the entire "read + serialise" path. Previously the
    # list-comprehension sat outside the block, so any TypeError in row
    # serialisation (datetime, Decimal, VARIANT) landed in FastAPI's global
    # handler instead of the helpful HTTPException + structured log below.
    try:
        cur = db.cursor()
        cur.execute(query, tuple(params))
        cols = [c[0].lower() for c in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]

        results: List[Dict[str, Any]] = []
        for r in rows:
            created_at = r.get("created_at")
            # Snowflake TIMESTAMP_NTZ usually yields a datetime, but some driver
            # paths hand back a string — handle both without crashing.
            if hasattr(created_at, "isoformat"):
                created_iso: Optional[str] = created_at.isoformat()
            elif created_at is None:
                created_iso = None
            else:
                created_iso = str(created_at)

            results.append(
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
                    "created_at": created_iso,
                    # Real temporal velocity signal: how many articles rolled
                    # into this cluster on the target day vs the day before.
                    "curr_day_count": int(r.get("curr_day_count") or 0),
                    "prev_day_count": int(r.get("prev_day_count") or 0),
                }
            )
    except Exception as e:
        logger.error("Trend read failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    return {"total": len(results), "results": results}
