import time

from snowflake.connector import SnowflakeConnection
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.limiter import limiter
from app.core.logging_conf import get_logger
from app.core.schemas import IngestionBatchResponse
from app.db.snowflake import get_db_connection
from app.services.ingestion import IngestionService
from app.repository.article import ArticleRepository
from app.core.cache import INTERNAL_CACHE

logger = get_logger("app.api.ingestion")
router = APIRouter()


@router.post("/fetch-rss", response_model=IngestionBatchResponse)
@limiter.limit("2/minute")
async def trigger_rss_ingestion(request: Request, db: SnowflakeConnection = Depends(get_db_connection)):
    """Triggers a full ingestion run across all registered RSS, ArXiv, and HackerNews sources.

    Fetches articles published within the last 26 hours and persists new ones to Snowflake
    using URL-based deduplication (MERGE). Rate-limited to 2 calls per minute to protect
    against accidental repeated triggers.
    """
    start_perf = time.perf_counter()
    logger.info("Manual RSS ingestion triggered")

    try:
        articles = await IngestionService.fetch_all_sources()
        saved_count = ArticleRepository.upsert_raw_articles(db, articles)

        # Task 18: Invalidate all archetype caches since new news is available
        if saved_count > 0:
            INTERNAL_CACHE.clear()
            logger.info("Global newsletter cache invalidated due to new ingestion")

        duration = time.perf_counter() - start_perf
        y_start, y_end = IngestionService._get_yesterday_range()

        return IngestionBatchResponse(
            status="SUCCESS",
            total_found=len(articles),
            saved_count=saved_count,
            start_time=y_start.isoformat(),
            end_time=y_end.isoformat(),
            processing_time_seconds=round(duration, 2)
        )

    except Exception as e:
        logger.error("Ingestion endpoint failure", error=str(e))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
