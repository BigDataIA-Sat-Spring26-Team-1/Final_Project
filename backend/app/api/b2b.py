"""B2B intelligence brief generation.

Idempotent per (company_id, brief_date=today): if a brief for today exists in
Snowflake we return it unchanged with ``already_generated=True``. The agent is
only invoked on cache misses. Same contract as the B2C newsletter endpoint.
"""
from __future__ import annotations

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


def _load_existing_brief(
    db: SnowflakeConnection, company_id: str, brief_date: str
) -> Optional[Dict[str, Any]]:
    cur = db.cursor()
    cur.execute(
        """
        SELECT brief_content, status, urgency_tier, generated_at, brief_date
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
    }


def _persist_brief(
    db: SnowflakeConnection,
    company_id: str,
    brief_date: str,
    content: str,
    urgency_tier: Optional[str],
) -> Tuple[str, str]:
    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO content_briefs
            (id, company_id, brief_date, brief_content, urgency_tier, status, generated_at)
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
        """,
        (
            str(uuid.uuid4()),
            company_id,
            brief_date,
            content,
            urgency_tier or "MONITOR",
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
    db: SnowflakeConnection = Depends(get_db_connection),
) -> B2BReportResponse:
    """Return today's brief for the company, generating it only if missing."""
    company_id = payload.user_id  # legacy contract: agent state uses ``user_id``
    today = date.today().isoformat()
    logger.info("B2B report requested", company_id=company_id, brief_date=today)

    existing = _load_existing_brief(db, company_id, today)
    if existing:
        return B2BReportResponse(
            user_id=company_id,
            report=existing["content"],
            status=existing["status"],
            already_generated=True,
            generated_at=existing["generated_at"],
            brief_date=existing["brief_date"],
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
    generated_at: str = ""
    if content.strip() and final_status == "SUCCESS":
        try:
            _, generated_at = _persist_brief(
                db,
                company_id,
                today,
                content,
                result.get("urgency_tier") or result.get("metadata", {}).get("urgency_tier"),
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
    )


@router.get("/keyword-velocity")
async def keyword_velocity(
    date: Optional[str] = Query(
        None,
        description="YYYY-MM-DD anchor for the current window (defaults to today).",
    ),
    top_n: int = Query(30, ge=1, le=100),
    min_mentions: int = Query(3, ge=1, le=50),
) -> Dict[str, Any]:
    """SpaCy NER-driven velocity report.

    Discovers ORG / PRODUCT / WORK_OF_ART / PERSON entities across the last
    24h of ingested titles, compares per-entity mention counts to the prior
    day, and tags each as SURGING / STABLE / DECLINING. Response mirrors the
    shape produced by ``Temp/SEO_Prototype/s5_keyword_velocity_test.py``.
    """
    logger.info("keyword_velocity requested", date=date, top_n=top_n)
    try:
        return compute_keyword_velocity(target_date=date, top_n=top_n, min_mentions=min_mentions)
    except RuntimeError as exc:
        # Missing spaCy model — surface as a clean 503 so the UI can render a
        # helpful "install the model" banner rather than a 500.
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("keyword_velocity failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
