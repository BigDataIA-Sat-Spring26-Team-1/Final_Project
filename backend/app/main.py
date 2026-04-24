import time
import uuid
from contextlib import asynccontextmanager
import snowflake.connector
import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api import admin, auth, b2b, deduplication, ingestion, personas, search, trend
from app.api.newsletter import router as newsletter_router
from app.core.config import Settings, get_settings
from app.core.errors import ErrorResponse
from app.core.limiter import limiter
from app.core.logging_conf import get_logger, setup_logging
from app.core.mcp_server import mcp_server
from app.core.metrics import HTTP_REQUEST_DURATION, REGISTRY
from app.db.qdrant import sync_vector_collections
from app.db.snowflake import get_db_connection, sync_database_schema

setup_logging(get_settings().app_env)
logger = get_logger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Application starting up")
    sync_database_schema()
    sync_vector_collections()
    yield
    logger.info("Application shutting down")

app = FastAPI(
    title="CurateAI Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=1000)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    start_time = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start_time

    HTTP_REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path,
        status=str(response.status_code),
    ).observe(duration)

    response.headers["X-Process-Time"] = f"{duration:.4f}"
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning("HTTP exception", status_code=exc.status_code, detail=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=str(exc.detail)).model_dump(),
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Request validation failed", errors=exc.errors())
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            message="Validation error", detail=str(exc.errors())
        ).model_dump(),
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):

    logger.error("Unhandled exception", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(message="Internal server error").model_dump(),
    )

app.include_router(personas.router, prefix="/api/v1/personas", tags=["Personas"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Ingestion Hub"])
app.include_router(deduplication.router, prefix="/api/v1/deduplication", tags=["Deduplication"])
app.include_router(trend.router, prefix="/api/v1/trend", tags=["Trend Engine"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Retrieval"])
app.include_router(b2b.router, prefix="/api/v1/b2b", tags=["B2B Intelligence"])
app.include_router(newsletter_router, prefix="/api/v1/newsletter", tags=["Newsletter Delivery"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

@app.get("/", tags=["System"], include_in_schema=False)
async def root():
    return {"service": "curateai-backend", "status": "ok", "docs": "/docs"}


@app.get("/livez", tags=["System"])
async def liveness():

    return {"status": "alive"}

@app.get("/api/v1/health", tags=["System"])
async def health_check(
    settings: Settings = Depends(get_settings),
    db: snowflake.connector.SnowflakeConnection = Depends(get_db_connection),
):

    try:
        cursor = db.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")
        sf_version = cursor.fetchone()[0]

        logger.info("Health check passed", snowflake_version=sf_version)
        return {
            "status": "healthy",
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "snowflake_version": sf_version,
        }
    except Exception:
        logger.error("Snowflake health check failed", exc_info=True)
        raise HTTPException(status_code=503, detail="Database connection failed")

@app.get("/metrics", tags=["System"])
async def metrics():
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/v1/metrics/summary", tags=["System"])
async def metrics_summary():
    from prometheus_client.samples import Sample

    def _collect():
        """Walk the registry once and return a {metric_name: [sample, ...]} map."""
        out: dict[str, list[Sample]] = {}
        for mf in REGISTRY.collect():
            out.setdefault(mf.name, []).extend(mf.samples)
        return out

    m = _collect()

    def _counter_sum(name: str, label: str | None = None) -> dict[str, float]:
        """Collapse a counter's samples keyed by the chosen label (or total)."""
        totals: dict[str, float] = {}
        for s in m.get(name, []):
            if not s.name.endswith("_total"):
                continue
            key = s.labels.get(label, "total") if label else "total"
            totals[key] = totals.get(key, 0.0) + float(s.value)
        return totals

    def _histogram_summary(name: str) -> dict[str, dict[str, float]]:
        """Return {label: {count, sum, avg}} for a histogram, grouped by label_name."""
        by_label: dict[str, dict[str, float]] = {}
        for s in m.get(name, []):
            if s.name.endswith("_bucket"):
                continue
            label_key = "_".join(f"{k}={v}" for k, v in s.labels.items()) or "overall"
            entry = by_label.setdefault(label_key, {"count": 0.0, "sum": 0.0})
            if s.name.endswith("_count"):
                entry["count"] = float(s.value)
            elif s.name.endswith("_sum"):
                entry["sum"] = float(s.value)
        for entry in by_label.values():
            entry["avg_seconds"] = round(entry["sum"] / entry["count"], 4) if entry["count"] else 0.0
        return by_label

    return {
        "llm": {
            "requests_by_status": _counter_sum("curateai_llm_requests", "status"),
            "tokens_by_type": _counter_sum("curateai_llm_tokens", "token_type"),
            "cost_usd_by_model": _counter_sum("curateai_llm_cost", "model"),
        },
        "agents": {
            "newsletter_rejections": sum(_counter_sum("curateai_newsletter_rejections").values()),
            "node_latency": _histogram_summary("curateai_langgraph_node_latency_seconds"),
        },
        "http": {
            "endpoint_latency": _histogram_summary("curateai_http_request_duration_seconds"),
        },
        "dags": {
            "triggers_by_outcome": _counter_sum("curateai_dag_triggers", "status"),
            "trigger_latency": _histogram_summary("curateai_dag_trigger_latency_seconds"),
        },
    }

try:
    mcp_server.mount_to(app, prefix="/api/v1/mcp")
    logger.info("MCP server mounted", prefix="/api/v1/mcp")
except AttributeError:
    try:
        app.mount("/api/v1/mcp", mcp_server.sse_app())
        logger.info("MCP server mounted via sse_app()", prefix="/api/v1/mcp")
    except Exception:
        logger.error("MCP server mount failed — REST API will still serve", exc_info=True)
except Exception:
    logger.error("MCP server mount failed — REST API will still serve", exc_info=True)