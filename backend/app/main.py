import uuid
import structlog
import snowflake.connector

from contextlib import asynccontextmanager

from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, Depends, HTTPException, Request

from app.core.errors import ErrorResponse
from app.core.config import Settings, get_settings
from app.api import personas, ingestion, deduplication
from app.core.logging_conf import setup_logging, get_logger
from app.db.snowflake import get_db_connection, sync_database_schema

from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler

from starlette.exceptions import HTTPException as StarletteHTTPException

setup_logging(get_settings().app_env)
logger = get_logger("app")

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    
    # Auto-Sync Snowflake Schema from master schema.sql
    sync_database_schema()
    
    yield
    logger.info("Application shutting down...")

app = FastAPI(
    title="CurateAI Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bind per-request context (ip, method, path, request_id) to structlog
# so every log line that fires during that request carries these fields automatically.
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        client_ip=client_ip,
        method=request.method,
        path=request.url.path,
    )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

# HTTP errors (404, 403, etc.) — return our standard shape instead of FastAPI's raw {"detail":...}
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning("HTTP exception", status_code=exc.status_code, detail=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=str(exc.detail)).model_dump()
    )

# Pydantic validation failures (422) — return our standard shape
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Request validation failed", errors=exc.errors())
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(message="Validation error", detail=str(exc.errors())).model_dump()
    )

# Catch-all for any unhandled 500s
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(message="Internal server error").model_dump()
    )

app.include_router(personas.router, prefix="/api/v1/personas", tags=["Personas"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Ingestion Hub"])
app.include_router(deduplication.router, prefix="/api/v1/deduplication", tags=["Deduplication"])

@app.get("/api/v1/health", tags=["System"])
async def health_check(
    settings: Settings = Depends(get_settings),
    db: snowflake.connector.SnowflakeConnection = Depends(get_db_connection)
):
    """Deep health check verifying app settings and Snowflake connectivity."""
    try:
        cursor = db.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")
        sf_version = cursor.fetchone()[0]

        logger.info("Health check passed", snowflake_version=sf_version)

        return {
            "status": "healthy",
            "app_name": settings.app_name,
            "version": settings.app_version,
            "snowflake_version": sf_version
        }
    except Exception:
        logger.error("Snowflake health check failed", exc_info=True)
        raise HTTPException(status_code=503, detail="Database connection failed")
