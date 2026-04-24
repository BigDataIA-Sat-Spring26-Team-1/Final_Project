from __future__ import annotations
import uuid
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from snowflake.connector import SnowflakeConnection
from app.core.logging_conf import get_logger
from app.core.schemas import B2CNewsletterRequest, B2CNewsletterResponse
from app.db.snowflake import get_db_connection
from app.services.b2c_agent import get_b2c_newsletter_graph
from app.services.mailer import (
    get_or_render_newsletter_html,
    render_personalized_html,
    send_newsletter_email,
)

logger = get_logger("newsletter_api")
router = APIRouter()

def _iso(value) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)

def _load_existing_newsletter(
    db: SnowflakeConnection, user_id: str, edition: str
) -> Optional[Dict[str, Any]]:
    cur = db.cursor()
    cur.execute(
        """
        SELECT final_content, draft_content, status, execution_path_taken,
               generated_at, edition_date
        FROM newsletters
        WHERE user_id = %s AND edition_date = %s
        ORDER BY generated_at DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        (user_id, edition),
    )
    row = cur.fetchone()
    if not row:
        return None
    content = row[0] or row[1] or ""
    if not content.strip():
        return None
    path_raw = row[3] or ""
    path: List[str] = [p for p in path_raw.split(",") if p] if isinstance(path_raw, str) else []
    return {
        "content": content,
        "status": row[2] or "PUBLISHED",
        "execution_path_taken": path,
        "generated_at": _iso(row[4]),
        "edition_date": _iso(row[5]),
    }

def _persist_newsletter(
    db: SnowflakeConnection,
    user_id: str,
    edition: str,
    content: str,
    path: List[str],
) -> Tuple[str, str]:
    path_str = ",".join(path)[:500] if path else None
    cur = db.cursor()
    cur.execute(
        """
        MERGE INTO newsletters t
        USING (SELECT %s AS user_id, %s AS edition_date) s
        ON t.user_id = s.user_id AND t.edition_date = s.edition_date
        WHEN MATCHED THEN UPDATE SET
            final_content = %s,
            draft_content = %s,
            execution_path_taken = %s,
            status = 'PUBLISHED',
            generated_at = CURRENT_TIMESTAMP(),
            updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN INSERT
            (id, user_id, edition_date, final_content, draft_content,
             execution_path_taken, status, generated_at)
        VALUES (%s, s.user_id, s.edition_date, %s, %s, %s, 'PUBLISHED',
                CURRENT_TIMESTAMP())
        """,
        (
            user_id,
            edition,
            content,
            content,
            path_str,
            str(uuid.uuid4()),
            content,
            content,
            path_str,
        ),
    )
    db.commit()
    cur.execute(
        "SELECT generated_at FROM newsletters WHERE user_id = %s AND edition_date = %s",
        (user_id, edition),
    )
    row = cur.fetchone()
    generated_at = _iso(row[0]) if row and row[0] is not None else None
    return "PUBLISHED", generated_at or ""

@router.post("/b2c", response_model=B2CNewsletterResponse)
async def generate_b2c_newsletter(
    request: B2CNewsletterRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> B2CNewsletterResponse:
    user_id = request.user_id
    edition = date.today().isoformat()
    logger.info(
        "B2C newsletter requested",
        user_id=user_id,
        mode=request.execution_mode,
        edition=edition,
    )

    existing = _load_existing_newsletter(db, user_id, edition)
    if existing:
        logger.info("Serving existing newsletter", user_id=user_id, edition=edition)
        return B2CNewsletterResponse(
            status=existing["status"],
            html_content=existing["content"],
            execution_path_taken=existing["execution_path_taken"] or [],
            already_generated=True,
            generated_at=existing["generated_at"],
            edition_date=existing["edition_date"] or edition,
        )

    try:
        graph = get_b2c_newsletter_graph()
        final_state = await graph.ainvoke(
            {
                "user_id": user_id,
                "execution_mode": request.execution_mode,
                "status": "PENDING",
                "messages": [],
            }
        )
    except Exception as e:
        logger.error("Failed to generate B2C newsletter", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")

    content = (final_state or {}).get("generated_content") or ""
    if not content.strip():
        raise HTTPException(status_code=502, detail="Agent returned an empty newsletter.")

    raw_path = (final_state or {}).get("execution_path_taken") or [
        "init",
        "curate",
        "write",
        "editor_review",
    ]
    path = raw_path if isinstance(raw_path, list) else [str(raw_path)]

    agent_status = (final_state or {}).get("status") or "SUCCESS"
    generated_at: str = ""
    try:
        _, generated_at = _persist_newsletter(db, user_id, edition, content, path)
    except Exception as e:
        logger.error("Newsletter persistence failed; returning unsaved content", error=str(e))

    return B2CNewsletterResponse(
        status=agent_status,
        html_content=content,
        execution_path_taken=path,
        already_generated=False,
        generated_at=generated_at or None,
        edition_date=edition,
    )

class NewsletterSendRequest(BaseModel):
    user_id: str = Field(..., description="Recipient's internal user id.")
    edition_date: Optional[str] = Field(
        default=None,
        description="YYYY-MM-DD edition to send; defaults to today.",
    )


class NewsletterSendResponse(BaseModel):
    status: str = Field(
        ...,
        description="SENT, ALREADY_SENT, FAILED, MAILER_DISABLED, NO_RECIPIENT, USER_NOT_FOUND",
    )
    user_id: str
    edition_date: str
    already_sent: bool = False
    recipient: Optional[str] = None
    message_id: Optional[str] = None
    sent_at: Optional[str] = None
    detail: Optional[str] = None
    common_count: Optional[int] = None
    personal_count: Optional[int] = None

class NewsletterPreviewResponse(BaseModel):
    user_id: str
    edition_date: str
    html_content: str
    already_sent: bool
    sent_at: Optional[str] = None
    recipient: Optional[str] = None
    common_count: int = 0
    personal_count: int = 0

@router.get("/available-dates")
async def available_dates(
    user_id: str,
    limit: int = 5,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Edition dates (YYYY-MM-DD) for which this user actually has a
    generated newsletter — lets the frontend surface only real dates
    instead of a raw date picker that implies every day is available.

    Capped to 5 by default: no demo value in surfacing arbitrarily old
    editions, and content-older-than-a-week can't be reliably rendered
    anyway since the upstream cluster pool has drifted."""
    limit = max(1, min(limit, 5))
    cur = db.cursor()
    cur.execute(
        """
        SELECT DISTINCT edition_date
        FROM newsletters
        WHERE user_id = %s
          AND COALESCE(final_content, draft_content) IS NOT NULL
          AND LENGTH(TRIM(COALESCE(final_content, draft_content))) > 0
        ORDER BY edition_date DESC
        LIMIT %s
        """,
        (user_id, limit),
    )
    rows = cur.fetchall()
    dates = [_iso(r[0]) for r in rows if r and r[0] is not None]
    return {"user_id": user_id, "dates": dates}


@router.get("/preview", response_model=NewsletterPreviewResponse)
async def preview_newsletter_email(
    user_id: str,
    edition_date: Optional[str] = None,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> NewsletterPreviewResponse:
    today = date.today().isoformat()
    target = edition_date or today

    cur = db.cursor()
    cur.execute(
        """
        SELECT sent_at, delivery_recipient, final_content, draft_content
        FROM newsletters
        WHERE user_id = %s AND edition_date = %s
        ORDER BY generated_at DESC NULLS LAST, created_at DESC
        LIMIT 1
        """,
        (user_id, target),
    )
    row = cur.fetchone()
    sent_at = _iso(row[0]) if row and row[0] is not None else None
    recipient = row[1] if row else None

    # Single source of truth: stored row wins if present; otherwise for
    # today we render once and persist so subsequent loads are stable
    # across sessions/logins. Past dates with no row return 404.
    try:
        rendered = await get_or_render_newsletter_html(user_id, target, db)
    except Exception as exc:
        logger.warning(
            "Preview render failed",
            user_id=user_id,
            edition_date=target,
            error=str(exc),
        )
        rendered = None

    if not rendered:
        raise HTTPException(
            status_code=404,
            detail=f"No newsletter was generated for {target}.",
        )

    return NewsletterPreviewResponse(
        user_id=user_id,
        edition_date=target,
        html_content=rendered["html"],
        already_sent=sent_at is not None,
        sent_at=sent_at,
        recipient=recipient,
        common_count=rendered.get("common_count", 0),
        personal_count=rendered.get("personal_count", 0),
    )

@router.post("/send", response_model=NewsletterSendResponse)
async def send_single_newsletter(
    request: NewsletterSendRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> NewsletterSendResponse:
    try:
        result = await send_newsletter_email(
            user_id=request.user_id,
            edition_date=request.edition_date,
            db=db,
        )
    except Exception as exc:  
        logger.error("Unexpected send failure", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    return NewsletterSendResponse(**result)