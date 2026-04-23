"""Admin / tenant-management endpoints.

Frontend's admin console expects a small CRUD surface:
    * create/list users and companies
    * edit an existing user or company
    * read newsletter / brief archives
    * kick the ingestion DAG manually

None of these are exposed to unauthenticated traffic in production — the
Cloud Run service is protected by the upstream firewall / IAP. If we ever
add self-serve signups the admin routes should move behind an
``is_admin`` claim check.
"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from snowflake.connector import SnowflakeConnection

from app.core.airflow_client import AirflowUnavailable, trigger_dag
from app.core.logging_conf import get_logger
from app.core.schemas import DAGTriggerResponse
from app.db.snowflake import get_db_connection
from app.services.company_affinity import extract_company_affinity

logger = get_logger("app.api.admin")
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response shapes
# ---------------------------------------------------------------------------

class CreateUserRequest(BaseModel):
    # Pydantic-native EmailStr would be nicer but pulls in the email-validator
    # dependency — a plain regex + server-side uniqueness check is enough here.
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    full_name: Optional[str] = None


class CreateCompanyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    domain: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    company_size: Optional[str] = None


class UpdatePersonaRequest(BaseModel):
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    seniority: Optional[str] = None
    bio_summary: Optional[str] = None
    linkedin_url: Optional[str] = None


class UpdateCompanyRequest(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    company_size: Optional[str] = None
    target_audience: Optional[str] = None
    key_products: Optional[str] = None
    content_pillars: Optional[str] = None
    competitors: Optional[str] = None
    tone_of_voice: Optional[str] = None


ALLOWED_COMPANY_SIZES = {"EARLY_STAGE", "GROWTH", "MID_MARKET", "ENTERPRISE"}
ALLOWED_TONES = {
    "AUTHORITATIVE",
    "CONVERSATIONAL",
    "TECHNICAL",
    "VISIONARY",
    "PLAYFUL",
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _iso(value: Any) -> Optional[str]:
    """Render Snowflake timestamps / dates as ISO strings or None."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.post("/users", status_code=201)
async def create_user(
    payload: CreateUserRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Provision a new user row. Email must be unique."""
    user_id = str(uuid.uuid4())
    cur = db.cursor()

    try:
        cur.execute("SELECT id FROM users WHERE email = %s", (payload.email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Email already registered.")

        cur.execute(
            "INSERT INTO users (id, email, full_name) VALUES (%s, %s, %s)",
            (user_id, payload.email, payload.full_name),
        )
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("User creation failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Create failed: {exc}")

    logger.info("User created", user_id=user_id, email=payload.email)
    return {"id": user_id, "email": payload.email, "status": "created"}


@router.get("/users")
async def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Paginated directory of tenants."""
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total = int(cur.fetchone()[0])

    cur.execute(
        """
        SELECT id, email, full_name, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )
    rows = cur.fetchall()
    results = [
        {
            "id": r[0],
            "email": r[1],
            "full_name": r[2],
            "created_at": _iso(r[3]),
        }
        for r in rows
    ]
    return {"total": total, "results": results}


@router.put("/personas/{user_id}")
async def update_persona(
    user_id: str,
    payload: UpdatePersonaRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, str]:
    """Edit the editable persona fields (job title, bio, …).

    Weight columns are NOT writable from this endpoint — those belong to the
    extraction pipeline and the behavioral feedback loop.
    """
    cur = db.cursor()

    if payload.full_name is not None:
        cur.execute(
            "UPDATE users SET full_name = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (payload.full_name, user_id),
        )

    fields = {
        "job_title": payload.job_title,
        "seniority": payload.seniority,
        "bio_summary": payload.bio_summary,
        "linkedin_url": payload.linkedin_url,
    }
    dirty = {k: v for k, v in fields.items() if v is not None}
    if dirty:
        set_clause = ", ".join(f"{col} = %s" for col in dirty)
        params = list(dirty.values()) + [user_id]
        cur.execute(
            f"""
            UPDATE user_personas
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            """,
            tuple(params),
        )

    db.commit()
    logger.info("Persona updated", user_id=user_id, fields=list(dirty.keys()))
    return {"user_id": user_id, "status": "updated"}


@router.put("/personas/{user_id}/categories")
async def update_persona_categories(
    user_id: str,
    payload: Dict[str, float],
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Overwrite the explicit category weights for a user.

    This is the "pick your interests" surface — the persona page sends a
    dictionary of {category: weight}. We normalise values to [0, 1] and drop
    anything below a 0.01 noise floor so the stored taxonomy stays clean.
    """
    cleaned: Dict[str, float] = {}
    for cat, raw_weight in (payload or {}).items():
        try:
            w = float(raw_weight)
        except (TypeError, ValueError):
            continue
        if w <= 0.01:
            continue
        cleaned[cat] = round(min(1.0, w), 4)

    cur = db.cursor()
    cur.execute(
        """
        UPDATE user_personas
        SET explicit_category_weights = PARSE_JSON(%s),
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
        """,
        (json.dumps(cleaned), user_id),
    )
    db.commit()
    logger.info("Persona categories updated", user_id=user_id, categories=list(cleaned.keys()))
    return {"user_id": user_id, "explicit_category_weights": cleaned}


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

@router.post("/companies", status_code=201)
async def create_company(
    payload: CreateCompanyRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Create a corporate tenant. Name is required, everything else is optional."""
    company_id = str(uuid.uuid4())
    cur = db.cursor()

    try:
        cur.execute(
            """
            INSERT INTO companies (id, name, domain, industry, description, company_size)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                company_id,
                payload.name,
                payload.domain,
                payload.industry,
                payload.description,
                payload.company_size,
            ),
        )
        db.commit()
    except Exception as exc:
        logger.error("Company creation failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Create failed: {exc}")

    # Best-effort affinity extraction on create. Create typically has a
    # thin profile (name + maybe industry) so the vector will look
    # generic — PUT /companies/{id} re-extracts once the full profile is
    # filled in, which is when the vector becomes actually useful.
    try:
        affinity = await extract_company_affinity(
            {
                "name": payload.name,
                "industry": payload.industry,
                "description": payload.description,
                "company_size": payload.company_size,
            }
        )
        if affinity:
            cur.execute(
                "UPDATE companies SET content_affinity_weights = PARSE_JSON(%s) WHERE id = %s",
                (json.dumps(affinity), company_id),
            )
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Affinity extraction on create skipped", error=str(exc))

    logger.info("Company created", company_id=company_id, name=payload.name)
    return {"id": company_id, "name": payload.name, "status": "created"}


@router.get("/companies")
async def list_companies(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM companies")
    total = int(cur.fetchone()[0])

    cur.execute(
        """
        SELECT id, name, domain, industry, created_at
        FROM companies
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )
    rows = cur.fetchall()
    results = [
        {
            "id": r[0],
            "name": r[1],
            "domain": r[2],
            "industry": r[3],
            "created_at": _iso(r[4]),
        }
        for r in rows
    ]
    return {"total": total, "results": results}


def _parse_variant(raw: Any) -> Optional[Any]:
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None


@router.get("/companies/{company_id}")
async def get_company(
    company_id: str,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Fetch a single company by id for the company-profile edit page."""
    cur = db.cursor()
    cur.execute(
        """
        SELECT id, name, domain, industry, description, company_size,
               target_audience, key_products, content_pillars, competitors,
               tone_of_voice, content_affinity_weights, created_at, updated_at
        FROM companies
        WHERE id = %s
        """,
        (company_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Company not found.")
    return {
        "id": row[0],
        "name": row[1],
        "domain": row[2],
        "industry": row[3],
        "description": row[4],
        "company_size": row[5],
        "target_audience": row[6],
        "key_products": row[7],
        "content_pillars": row[8],
        "competitors": row[9],
        "tone_of_voice": row[10],
        "content_affinity_weights": _parse_variant(row[11]),
        "created_at": _iso(row[12]),
        "updated_at": _iso(row[13]),
    }


@router.put("/companies/{company_id}")
async def update_company(
    company_id: str,
    payload: UpdateCompanyRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, str]:
    # Every profile field is mandatory — the downstream DAGs and the
    # Strategic Brief agent rely on full context, so we reject partial
    # payloads with explicit 422s.
    required = {
        "name": payload.name,
        "domain": payload.domain,
        "industry": payload.industry,
        "description": payload.description,
        "company_size": payload.company_size,
        "target_audience": payload.target_audience,
        "key_products": payload.key_products,
        "content_pillars": payload.content_pillars,
        "competitors": payload.competitors,
        "tone_of_voice": payload.tone_of_voice,
    }
    missing = [k for k, v in required.items() if v is None or str(v).strip() == ""]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required fields: {', '.join(missing)}",
        )
    if payload.company_size not in ALLOWED_COMPANY_SIZES:
        raise HTTPException(
            status_code=422,
            detail=f"company_size must be one of {sorted(ALLOWED_COMPANY_SIZES)}",
        )
    if payload.tone_of_voice not in ALLOWED_TONES:
        raise HTTPException(
            status_code=422,
            detail=f"tone_of_voice must be one of {sorted(ALLOWED_TONES)}",
        )

    dirty = {k: v.strip() if isinstance(v, str) else v for k, v in required.items()}

    cur = db.cursor()
    set_clause = ", ".join(f"{col} = %s" for col in dirty)
    params = list(dirty.values()) + [company_id]
    cur.execute(
        f"""
        UPDATE companies
        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        tuple(params),
    )
    db.commit()
    logger.info("Company updated", company_id=company_id, fields=list(dirty.keys()))

    # Re-extract the content-affinity vector against the NEW profile —
    # the LLM's output is a pure function of the profile text so any
    # material edit should refresh the vector. Best-effort: if the call
    # fails we keep the existing vector (or leave null on create).
    affinity_updated = False
    try:
        affinity = await extract_company_affinity(dirty)
        if affinity:
            cur.execute(
                "UPDATE companies SET content_affinity_weights = PARSE_JSON(%s), "
                "updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (json.dumps(affinity), company_id),
            )
            db.commit()
            affinity_updated = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Affinity re-extract on update skipped", error=str(exc))

    return {
        "company_id": company_id,
        "status": "updated",
        "affinity_refreshed": affinity_updated,
    }


# ---------------------------------------------------------------------------
# Archive reads
# ---------------------------------------------------------------------------

@router.get("/newsletters/all")
async def newsletters_cross_tenant(
    date: Optional[str] = Query(
        None,
        description="YYYY-MM-DD. Defaults to yesterday so admins see the freshest completed batch.",
    ),
    limit: int = Query(50, ge=1, le=200),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Cross-user newsletter archive for the admin console.

    Without a date filter this returns the newsletters written *yesterday*,
    which is usually the most recent fully-generated batch at the time an
    admin is looking at the page. Pass ``date`` to look further back.
    """
    from datetime import date as _date, timedelta

    effective = date or (_date.today() - timedelta(days=1)).isoformat()

    cur = db.cursor()
    cur.execute(
        """
        SELECT n.id, n.user_id, n.edition_date, n.status, n.generated_at,
               n.execution_path_taken, u.email, u.full_name
        FROM newsletters n
        LEFT JOIN users u ON u.id = n.user_id
        WHERE n.edition_date = %s
        ORDER BY n.generated_at DESC NULLS LAST
        LIMIT %s
        """,
        (effective, limit),
    )
    rows = cur.fetchall()
    results = [
        {
            "id": r[0],
            "user_id": r[1],
            "edition_date": _iso(r[2]),
            "status": r[3],
            "generated_at": _iso(r[4]),
            "execution_path_taken": r[5],
            "user_email": r[6],
            "user_full_name": r[7],
        }
        for r in rows
    ]
    return {"date": effective, "total": len(results), "results": results}


@router.get("/briefs/all")
async def briefs_cross_tenant(
    date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Cross-company brief archive. Mirrors /newsletters/all."""
    from datetime import date as _date, timedelta

    effective = date or (_date.today() - timedelta(days=1)).isoformat()

    cur = db.cursor()
    cur.execute(
        """
        SELECT b.id, b.company_id, b.brief_date, b.urgency_tier, b.generated_at,
               LENGTH(b.brief_content), c.name, c.domain
        FROM content_briefs b
        LEFT JOIN companies c ON c.id = b.company_id
        WHERE b.brief_date = %s
        ORDER BY b.generated_at DESC NULLS LAST
        LIMIT %s
        """,
        (effective, limit),
    )
    rows = cur.fetchall()
    results = [
        {
            "id": r[0],
            "company_id": r[1],
            "brief_date": _iso(r[2]),
            "urgency_tier": r[3],
            "generated_at": _iso(r[4]),
            "content_length": int(r[5]) if r[5] is not None else 0,
            "company_name": r[6],
            "company_domain": r[7],
        }
        for r in rows
    ]
    return {"date": effective, "total": len(results), "results": results}


@router.get("/newsletters/archive")
async def newsletter_archive(
    user_id: str = Query(..., description="The user whose newsletters to load."),
    date: Optional[str] = Query(None, description="Optional YYYY-MM-DD filter."),
    limit: int = Query(10, ge=1, le=100),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Recent newsletters for a given user, newest first.

    The response surfaces delivery state (``sent_at``, ``delivery_status``,
    ``delivery_recipient``) so the admin UI can show whether today's edition
    already shipped by email and disable the send button accordingly.
    """
    params: List[Any] = [user_id]
    query = """
        SELECT id, user_id, edition_date, status, generated_at,
               execution_path_taken, final_content, draft_content,
               sent_at, delivery_status, delivery_recipient, delivery_message_id
        FROM newsletters
        WHERE user_id = %s
    """
    if date:
        query += " AND edition_date = %s"
        params.append(date)
    query += " ORDER BY edition_date DESC LIMIT %s"
    params.append(limit)

    cur = db.cursor()
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    results = [
        {
            "id": r[0],
            "user_id": r[1],
            "edition_date": _iso(r[2]),
            "status": r[3],
            "generated_at": _iso(r[4]),
            "execution_path_taken": r[5],
            "final_content": r[6],
            "draft_content": r[7],
            "sent_at": _iso(r[8]),
            "delivery_status": r[9],
            "delivery_recipient": r[10],
            "delivery_message_id": r[11],
        }
        for r in rows
    ]
    return {"total": len(results), "results": results}


@router.get("/briefs/archive")
async def brief_archive(
    company_id: str = Query(..., description="Corporate tenant id."),
    date: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    params: List[Any] = [company_id]
    query = """
        SELECT id, company_id, brief_date, brief_content, urgency_tier,
               created_at, generated_at, structured_brief
        FROM content_briefs
        WHERE company_id = %s
    """
    if date:
        query += " AND brief_date = %s"
        params.append(date)
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    cur = db.cursor()
    cur.execute(query, tuple(params))
    rows = cur.fetchall()

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

    results = [
        {
            "id": r[0],
            "company_id": r[1],
            "brief_date": _iso(r[2]),
            "brief_content": r[3],
            "urgency_tier": r[4],
            "created_at": _iso(r[5]),
            "generated_at": _iso(r[6]),
            "structured_brief": _parse_variant(r[7]),
        }
        for r in rows
    ]
    return {"total": len(results), "results": results}


# ---------------------------------------------------------------------------
# Admin DAG triggers
# ---------------------------------------------------------------------------

@router.post("/ingestion/trigger", status_code=202, response_model=DAGTriggerResponse)
async def admin_trigger_ingestion() -> DAGTriggerResponse:
    """Identical to /ingestion/fetch-rss but mounted under /admin so the
    admin console can call it without also granting rate-limited user scope."""
    try:
        run = await trigger_dag("ingestion_dag")
    except AirflowUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return DAGTriggerResponse(
        status="ACCEPTED",
        message="Ingestion DAG scheduled.",
        dag_id="ingestion_dag",
        dag_run_id=run.get("dag_run_id", ""),
        state=run.get("state"),
    )


# ---------------------------------------------------------------------------
# Newsletter delivery (MailerSend) — batch entry point
# ---------------------------------------------------------------------------

@router.post("/newsletters/send-all")
async def admin_send_newsletters_batch(
    date: Optional[str] = Query(
        None, description="YYYY-MM-DD edition to ship; defaults to today."
    ),
    user_id: Optional[str] = Query(
        None,
        description=(
            "Optional — dispatch only for this user id. When omitted we fan "
            "out across every user whose newsletter row for ``date`` has "
            "``sent_at IS NULL`` (i.e. never shipped by email before)."
        ),
    ),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """Fan out MailerSend dispatches for an edition.

    Concurrency is bounded (MailerSend's public API quota is modest) — we
    process up to 5 users in flight. Each send is idempotent per
    ``(user_id, edition_date)`` so retrying the batch is safe.
    """
    from asyncio import Semaphore, gather
    from app.services.mailer import send_newsletter_email

    from datetime import date as _date

    target = date or _date.today().isoformat()

    if user_id:
        target_users = [user_id]
    else:
        cur = db.cursor()
        cur.execute(
            """
            SELECT DISTINCT n.user_id
            FROM newsletters n
            WHERE n.edition_date = %s AND n.sent_at IS NULL
              AND (n.final_content IS NOT NULL OR n.draft_content IS NOT NULL)
            """,
            (target,),
        )
        target_users = [row[0] for row in cur.fetchall() if row[0]]

    if not target_users:
        return {"edition_date": target, "attempted": 0, "results": []}

    semaphore = Semaphore(5)

    async def _one(uid: str) -> Dict[str, Any]:
        async with semaphore:
            try:
                return await send_newsletter_email(uid, target, db)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Batch send failed for user",
                    user_id=uid,
                    error=str(exc),
                    exc_info=True,
                )
                return {
                    "status": "FAILED",
                    "user_id": uid,
                    "edition_date": target,
                    "already_sent": False,
                    "detail": str(exc),
                }

    results = await gather(*(_one(u) for u in target_users))
    sent = sum(1 for r in results if r.get("status") == "SENT")
    skipped = sum(1 for r in results if r.get("status") == "ALREADY_SENT")
    failed = sum(1 for r in results if r.get("status") == "FAILED")

    return {
        "edition_date": target,
        "attempted": len(target_users),
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }
