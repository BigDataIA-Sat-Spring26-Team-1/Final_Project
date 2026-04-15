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
from app.db.qdrant import sync_vector_collections
from app.core.config import Settings, get_settings
from app.core.limiter import limiter
from app.core.logging_conf import setup_logging, get_logger
from app.api import personas, ingestion, deduplication, trend, search
from app.db.snowflake import get_db_connection, sync_database_schema

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from starlette.exceptions import HTTPException as StarletteHTTPException

setup_logging(get_settings().app_env)
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    sync_database_schema()
    sync_vector_collections()
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


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attaches a unique request ID and client metadata to every log line."""
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


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Returns a consistent JSON error shape for HTTP errors (404, 403, etc.)."""
    logger.warning("HTTP exception", status_code=exc.status_code, detail=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=str(exc.detail)).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Returns a consistent JSON error shape for Pydantic validation failures (422)."""
    logger.warning("Request validation failed", errors=exc.errors())
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(message="Validation error", detail=str(exc.errors())).model_dump()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler to prevent raw stack traces from reaching the client."""
    logger.error("Unhandled exception", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(message="Internal server error").model_dump()
    )


# --- Route Registration ---
app.include_router(personas.router, prefix="/api/v1/personas", tags=["Personas"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Ingestion Hub"])
app.include_router(deduplication.router, prefix="/api/v1/deduplication", tags=["Deduplication"])
app.include_router(trend.router, prefix="/api/v1/trend", tags=["Trend Engine"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Retrieval"])

from app.api.newsletter import router as newsletter_router
app.include_router(newsletter_router, prefix="/api/v1/newsletter", tags=["Newsletter Delivery"])


@app.get("/api/v1/health", tags=["System"])
async def health_check(
    settings: Settings = Depends(get_settings),
    db: snowflake.connector.SnowflakeConnection = Depends(get_db_connection)
):
    """Verifies app configuration and Snowflake connectivity."""
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
