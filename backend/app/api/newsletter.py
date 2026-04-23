"""B2C newsletter generation.

Idempotent per (user_id, edition_date): if a newsletter already exists for
today in Snowflake we return it as-is with `already_generated=True` and never
rerun the LangGraph. This is the contract the frontend and the DAG both rely
on — regeneration is explicitly disallowed.
"""
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
from app.services.mailer import send_newsletter_email

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
    """Upsert one newsletter row per (user_id, edition_date). Returns (status, generated_at_iso)."""
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
    # Re-read the timestamp so the response reflects what went into the column,
    # not just client-side "now".
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
    """Return today's newsletter for the user, generating it only if missing."""
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

    # Fire-and-forget email delivery on the fresh draft. `send_newsletter_email`
    # is idempotent per (user_id, edition_date) so a later admin re-send is a
    # no-op. Failures are logged but don't fail the generation — the user
    # still gets the in-app preview.
    try:
        send_result = await send_newsletter_email(user_id, edition, db)
        logger.info(
            "Auto-email attempted after newsletter generation",
            user_id=user_id,
            status=send_result.get("status"),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Auto-email after generation failed", error=str(e))

    return B2CNewsletterResponse(
        status=agent_status,
        html_content=content,
        execution_path_taken=path,
        already_generated=False,
        generated_at=generated_at or None,
        edition_date=edition,
    )


# ---------------------------------------------------------------------------
# Newsletter delivery (MailerSend)
# ---------------------------------------------------------------------------

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


@router.post("/send", response_model=NewsletterSendResponse)
async def send_single_newsletter(
    request: NewsletterSendRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> NewsletterSendResponse:
    """Dispatch one user's newsletter by email via MailerSend.

    Idempotent per ``(user_id, edition_date)`` — we never send twice for the
    same day. Errors come back as structured payloads (``FAILED``) rather than
    raising, so the frontend can surface them cleanly.
    """
    try:
        result = await send_newsletter_email(
            user_id=request.user_id,
            edition_date=request.edition_date,
            db=db,
        )
    except Exception as exc:  # noqa: BLE001 — surface any unexpected issue
        logger.error("Unexpected send failure", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return NewsletterSendResponse(**result)
