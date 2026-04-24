from __future__ import annotations
import re
import uuid
from typing import Any, Dict, Literal, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from snowflake.connector import SnowflakeConnection
from app.core.limiter import limiter
from app.core.logging_conf import get_logger
from app.db.snowflake import get_db_connection
from app.services.auth import (
    InvalidTokenError,
    decode_token,
    hash_password,
    issue_token,
    verify_password,
)

logger = get_logger("app.api.auth")
router = APIRouter()

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
class SignupRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: Literal["USER", "COMPANY"] = Field(
        default="USER",
        description="ADMIN cannot self-signup — seed that account server-side.",
    )
    company_name: Optional[str] = Field(default=None, max_length=255)
    company_domain: Optional[str] = Field(default=None, max_length=255)
    company_industry: Optional[str] = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def _email_format(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("email must be a valid address")
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("password must include at least one letter and one digit")
        return value

class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _lowercase(cls, value: str) -> str:
        return value.strip().lower()

class AuthUser(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    company_id: Optional[str] = None
    company_name: Optional[str] = None

class AuthEnvelope(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: AuthUser

def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: SnowflakeConnection = Depends(get_db_connection),
) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject.")

    cur = db.cursor()
    cur.execute(
        """
        SELECT u.id, u.email, u.full_name, u.role, u.company_id, c.name
        FROM users u
        LEFT JOIN companies c ON c.id = u.company_id
        WHERE u.id = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Account no longer exists.")

    return AuthUser(
        id=row[0],
        email=row[1],
        full_name=row[2],
        role=(row[3] or "USER").upper(),
        company_id=row[4],
        company_name=row[5],
    )

def require_role(*roles: str):
    allowed = {r.upper() for r in roles}

    def _checker(current: AuthUser = Depends(get_current_user)) -> AuthUser:
        if current.role not in allowed:
            raise HTTPException(status_code=403, detail="Forbidden.")
        return current

    return _checker

def _envelope(row: Any, company_name: Optional[str] = None) -> AuthEnvelope:
    user = AuthUser(
        id=row[0],
        email=row[1],
        full_name=row[2],
        role=row[3],
        company_id=row[4],
        company_name=company_name,
    )
    token = issue_token(user.id, user.role, {"email": user.email})
    return AuthEnvelope(
        access_token=token,
        expires_in=4 * 60 * 60,
        user=user,
    )

@router.post("/signup", response_model=AuthEnvelope, status_code=201)
@limiter.limit("10/minute")
async def signup(
    request: Request,
    payload: SignupRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> AuthEnvelope:
    # B2C (USER) accounts are restricted to Gmail addresses because the
    # newsletter delivery path uses Gmail SMTP and consumer inboxes on
    # other providers (Outlook / Workspace) silently filter mail from our
    # sender. Company tenants accept any email — they don't receive
    # newsletters, only admins do.
    if payload.role == "USER":
        email_norm = (payload.email or "").strip().lower()
        if not re.match(r"^[a-z0-9._%+-]+@gmail\.com$", email_norm):
            raise HTTPException(
                status_code=422,
                detail="Reader accounts must use a Gmail address (@gmail.com).",
            )

    cur = db.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (payload.email,))
    if cur.fetchone():
        raise HTTPException(status_code=409, detail="An account with that email already exists.")

    user_id = str(uuid.uuid4())
    company_id: Optional[str] = None

    if payload.role == "COMPANY":
        if not payload.company_name:
            raise HTTPException(status_code=400, detail="Company name is required for a company account.")
        company_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO companies
                (id, name, domain, industry, created_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
            """,
            (
                company_id,
                payload.company_name,
                payload.company_domain,
                payload.company_industry,
                user_id,
            ),
        )

    cur.execute(
        """
        INSERT INTO users
            (id, email, full_name, password_hash, role, company_id, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """,
        (
            user_id,
            payload.email,
            payload.full_name,
            hash_password(payload.password),
            payload.role,
            company_id,
        ),
    )
    db.commit()

    logger.info("Account created", user_id=user_id, role=payload.role)
    return _envelope(
        (user_id, payload.email, payload.full_name, payload.role, company_id),
        company_name=payload.company_name if payload.role == "COMPANY" else None,
    )

@router.post("/login", response_model=AuthEnvelope)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
) -> AuthEnvelope:
    cur = db.cursor()
    cur.execute(
        """
        SELECT u.id, u.email, u.full_name, u.role, u.company_id, u.password_hash,
               c.name
        FROM users u
        LEFT JOIN companies c ON c.id = u.company_id
        WHERE u.email = %s
        """,
        (payload.email,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No account with this email.")

    if not verify_password(payload.password, row[5] or ""):
        raise HTTPException(status_code=401, detail="Incorrect password.")

    logger.info("Login", user_id=row[0], role=row[3])
    return _envelope(row[:5], company_name=row[6])

@router.get("/me", response_model=AuthUser)
async def me(current: AuthUser = Depends(get_current_user)) -> AuthUser:
    return current
