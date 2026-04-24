from __future__ import annotations
import json
import uuid
from datetime import date
from typing import Any, Dict, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from snowflake.connector import SnowflakeConnection
from app.core.limiter import limiter
from app.core.logging_conf import get_logger
from app.core.schemas import B2BReportRequest, B2BReportResponse
from app.db.snowflake import get_db_connection
from app.services.b2b_agent import get_b2b_report_graph
from app.services.keyword_velocity import compute_keyword_velocity

logger = get_logger("app.api.b2b")
router = APIRouter()

def _iso(value) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)

def _parse_variant(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None

def _load_existing_brief(
    db: SnowflakeConnection, company_id: str, brief_date: str
) -> Optional[Dict[str, Any]]:
    cur = db.cursor()
    cur.execute(
        """
        SELECT brief_content, status, urgency_tier, generated_at, brief_date,
               structured_brief
        FROM content_briefs
        WHERE company_id = %s AND brief_date = %s
        ORDER BY generated_at DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        (company_id, brief_date),
    )
    row = cur.fetchone()
    if not row:
        return None
    content = row[0] or ""
    if not content.strip():
        return None
    return {
        "content": content,
        "status": row[1] or "GENERATED",
        "urgency_tier": row[2],
        "generated_at": _iso(row[3]),
        "brief_date": _iso(row[4]) or brief_date,
        "structured_brief": _parse_variant(row[5]),
    }

def _persist_brief(
    db: SnowflakeConnection,
    company_id: str,
    brief_date: str,
    content: str,
    urgency_tier: Optional[str],
    structured_brief: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO content_briefs
            (id, company_id, brief_date, brief_content, urgency_tier,
             structured_brief, status, generated_at)
        SELECT %s, %s, %s, %s, %s, PARSE_JSON(%s), %s, CURRENT_TIMESTAMP()
        """,
        (
            str(uuid.uuid4()),
            company_id,
            brief_date,
            content,
            urgency_tier or "MONITOR",
            json.dumps(structured_brief) if structured_brief else None,
            "GENERATED",
        ),
    )
    db.commit()
    cur.execute(
        "SELECT generated_at FROM content_briefs WHERE company_id = %s AND brief_date = %s "
        "ORDER BY generated_at DESC NULLS LAST LIMIT 1",
        (company_id, brief_date),
    )
    row = cur.fetchone()
    generated_at = _iso(row[0]) if row and row[0] is not None else ""
    return "GENERATED", generated_at

@router.post("/report", response_model=B2BReportResponse)
@limiter.limit("10/minute")
async def generate_b2b_report(
    request: Request,
    payload: B2BReportRequest,
    force: bool = Query(
        default=False,
        description=(
            "When true, bypass the daily idempotency guard and re-run the "
            "agent even if today's brief is already stored. Useful after "
            "updating the company profile or upgrading the agent."
        ),
    ),
    brief_date: Optional[str] = Query(
        default=None,
        description=(
            "YYYY-MM-DD override for the brief date. Defaults to today. "
            "Used for backfilling historical briefs during demos."
        ),
    ),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> B2BReportResponse:
    company_id = payload.user_id 
    today = brief_date or date.today().isoformat()
    logger.info("B2B report requested", company_id=company_id, brief_date=today, force=force)

    if force:
        cur = db.cursor()
        cur.execute(
            "DELETE FROM content_briefs WHERE company_id = %s AND brief_date = %s",
            (company_id, today),
        )
        db.commit()

    existing = None if force else _load_existing_brief(db, company_id, today)
    if existing:
        return B2BReportResponse(
            user_id=company_id,
            report=existing["content"],
            status=existing["status"],
            already_generated=True,
            generated_at=existing["generated_at"],
            brief_date=existing["brief_date"],
            structured_brief=existing.get("structured_brief"),
            urgency_tier=existing.get("urgency_tier"),
        )

    graph = get_b2b_report_graph()
    initial_state = {
        "user_id": company_id,
        "user_persona": {},
        "search_query": "",
        "retrieved_articles": [],
        "messages": [],
        "next_step": "",
        "generated_content": "",
        "status": "PENDING",
        "metadata": {},
        "brief_date": today,
    }

    try:
        result = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("B2B report generation failed", company_id=company_id, error=str(e))
        raise HTTPException(status_code=500, detail="Report generation failed.")

    final_status = result.get("status", "UNKNOWN")
    if final_status not in ("SUCCESS", "EMPTY_RESULT"):
        raise HTTPException(
            status_code=500,
            detail=f"Agent completed with unexpected status: {final_status}",
        )

    content = result.get("generated_content", "") or ""
    metadata = result.get("metadata", {}) or {}
    structured_brief = metadata.get("structured_brief")
    urgency_tier = metadata.get("urgency_tier") or result.get("urgency_tier")
    generated_at: str = ""
    if content.strip() and final_status == "SUCCESS":
        try:
            _, generated_at = _persist_brief(
                db,
                company_id,
                today,
                content,
                urgency_tier,
                structured_brief,
            )
        except Exception as e:
            logger.error("Brief persistence failed; returning unsaved content", error=str(e))

    return B2BReportResponse(
        user_id=company_id,
        report=content,
        status=final_status,
        already_generated=False,
        generated_at=generated_at or None,
        brief_date=today,
        structured_brief=structured_brief,
        urgency_tier=urgency_tier,
    )

@router.get("/available-brief-dates")
async def available_brief_dates(
    company_id: str = Query(..., description="Tenant whose briefs to list."),
    limit: int = Query(5, ge=1, le=30),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Distinct brief_dates with real content for a company, newest first.
    Mirrors /api/v1/newsletter/available-dates for the B2B side so the UI
    only offers dates that actually have a generated brief."""
    limit = max(1, min(limit, 30))
    cur = db.cursor()
    cur.execute(
        """
        SELECT DISTINCT brief_date
        FROM content_briefs
        WHERE company_id = %s
          AND brief_content IS NOT NULL
          AND LENGTH(TRIM(brief_content)) > 0
        ORDER BY brief_date DESC
        LIMIT %s
        """,
        (company_id, limit),
    )
    dates = [_iso(r[0]) for r in cur.fetchall() if r and r[0] is not None]
    return {"company_id": company_id, "dates": dates}


@router.get("/available-velocity-dates")
async def available_velocity_dates(
    limit: int = Query(5, ge=1, le=30),
    min_articles: int = Query(5, ge=1, le=500),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Distinct published_at dates with enough articles to produce a
    meaningful keyword-velocity snapshot — avoids offering dates where
    the NER pass would come back empty."""
    limit = max(1, min(limit, 30))
    cur = db.cursor()
    cur.execute(
        """
        SELECT CAST(published_at AS DATE) AS d, COUNT(*) AS n
        FROM articles_raw
        WHERE published_at IS NOT NULL
        GROUP BY 1
        HAVING COUNT(*) >= %s
        ORDER BY d DESC
        LIMIT %s
        """,
        (min_articles, limit),
    )
    dates = [_iso(r[0]) for r in cur.fetchall() if r and r[0] is not None]
    return {"dates": dates}


@router.get("/keyword-velocity")
async def keyword_velocity(
    date: Optional[str] = Query(
        None,
        description="YYYY-MM-DD anchor for the current window (defaults to today).",
    ),
    top_n: int = Query(30, ge=1, le=100),
    min_mentions: int = Query(3, ge=1, le=50),
) -> Dict[str, Any]:

    logger.info("keyword_velocity requested", date=date, top_n=top_n)
    try:
        return compute_keyword_velocity(target_date=date, top_n=top_n, min_mentions=min_mentions)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("keyword_velocity failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
