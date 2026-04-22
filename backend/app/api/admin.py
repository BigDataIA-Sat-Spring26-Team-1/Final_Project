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


@router.put("/companies/{company_id}")
async def update_company(
    company_id: str,
    payload: UpdateCompanyRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> Dict[str, str]:
    dirty = {
        k: v
        for k, v in {
            "name": payload.name,
            "domain": payload.domain,
            "industry": payload.industry,
            "description": payload.description,
            "company_size": payload.company_size,
        }.items()
        if v is not None
    }
    if not dirty:
        return {"company_id": company_id, "status": "noop"}

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
    return {"company_id": company_id, "status": "updated"}


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
    """Recent newsletters for a given user, newest first."""
    params: List[Any] = [user_id]
    query = """
        SELECT id, user_id, edition_date, status, generated_at,
               execution_path_taken, final_content, draft_content
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
               created_at, generated_at
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
    results = [
        {
            "id": r[0],
            "company_id": r[1],
            "brief_date": _iso(r[2]),
            "brief_content": r[3],
            "urgency_tier": r[4],
            "created_at": _iso(r[5]),
            "generated_at": _iso(r[6]),
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
