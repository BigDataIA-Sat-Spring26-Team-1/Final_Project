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

    # Day-over-day velocity is computed in a *separate* query below so a fault
    # in the join can't take down the main trends feed — this endpoint is
    # consumed by Global Trends, Keyword Velocity, Market Intelligence, and
    # the admin clusters panel, so it has to stay up even if the velocity
    # signal is temporarily unavailable.
    from datetime import date as _date, timedelta

    target_day = date or _date.today().isoformat()
    prev_day = (_date.fromisoformat(target_day) - timedelta(days=1)).isoformat()

    # LEFT JOIN the first article in each cluster so the UI can link out to a
    # real source URL (and show the source name). Using QUALIFY to pick the
    # earliest article per cluster keeps the join deterministic even when a
    # cluster spans multiple sources.
    query = """
        SELECT c.id,
               c.primary_title,
               c.primary_summary,
               c.trend_status,
               c.final_trend_score,
               c.cluster_size,
               c.social_popularity_score,
               c.category_weights,
               c.created_at,
               a.url AS representative_url,
               a.source_name AS representative_source
        FROM article_clusters c
        LEFT JOIN (
            SELECT cluster_id, url, source_name,
                   ROW_NUMBER() OVER (
                       PARTITION BY cluster_id
                       ORDER BY published_at DESC NULLS LAST, fetched_at DESC
                   ) AS rn
            FROM articles_raw
            WHERE cluster_id IS NOT NULL
        ) a ON a.cluster_id = c.id AND a.rn = 1
        WHERE c.final_trend_score IS NOT NULL
    """
    params: List[Any] = []
    if status:
        query += " AND UPPER(c.trend_status) = UPPER(%s)"
        params.append(status)
    if date:
        # created_at is a TIMESTAMP_NTZ; cast to DATE for an index-friendly compare.
        query += " AND CAST(c.created_at AS DATE) = %s"
        params.append(date)
    # When a caller pins a date we want the highest-score clusters of that day
    # first; with no date filter we bubble up the newest clusters (then score
    # as a tiebreaker within the same batch).
    if date:
        query += " ORDER BY c.final_trend_score DESC, c.cluster_size DESC NULLS LAST LIMIT %s"
    else:
        query += " ORDER BY c.created_at DESC, c.final_trend_score DESC NULLS LAST LIMIT %s"
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

        # Best-effort day-over-day counts. Isolated from the main query so a
        # schema hiccup on articles_raw (e.g. stale cluster_id refs) can't
        # 500 the whole feed — callers just see zeros for velocity.
        cluster_ids = [r["id"] for r in rows if r.get("id")]
        curr_counts: Dict[str, int] = {}
        prev_counts: Dict[str, int] = {}
        if cluster_ids:
            try:
                placeholders = ",".join(["%s"] * len(cluster_ids))
                count_sql = (
                    "SELECT cluster_id, CAST(fetched_at AS DATE) AS day, COUNT(*) AS n "
                    "FROM articles_raw "
                    f"WHERE cluster_id IN ({placeholders}) "
                    "AND CAST(fetched_at AS DATE) IN (%s, %s) "
                    "GROUP BY cluster_id, CAST(fetched_at AS DATE)"
                )
                cur.execute(count_sql, tuple(cluster_ids) + (target_day, prev_day))
                for cid, day, n in cur.fetchall():
                    day_iso = day.isoformat() if hasattr(day, "isoformat") else str(day)
                    if day_iso == target_day:
                        curr_counts[cid] = int(n)
                    elif day_iso == prev_day:
                        prev_counts[cid] = int(n)
            except Exception as ce:
                logger.warning("Day-over-day count lookup failed; returning zeros", error=str(ce))

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
                    "curr_day_count": curr_counts.get(r["id"], 0),
                    "prev_day_count": prev_counts.get(r["id"], 0),
                    "url": r.get("representative_url"),
                    "source_name": r.get("representative_source"),
                }
            )
    except Exception as e:
        logger.error("Trend read failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    return {"total": len(results), "results": results}
