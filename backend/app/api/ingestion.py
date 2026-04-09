import time
from snowflake.connector import SnowflakeConnection
from fastapi import APIRouter, Depends, HTTPException, Request

from app.main import limiter
from app.core.logging_conf import get_logger
from app.db.snowflake import get_db_connection
from app.services.ingestion import IngestionService
from app.repository.article import ArticleRepository
from app.core.schemas import IngestionBatchResponse

logger = get_logger("app.api.ingestion")
router = APIRouter()

@router.post("/fetch-rss", response_model=IngestionBatchResponse)
@limiter.limit("2/minute") # Strict limit for heavy IO operations
async def trigger_rss_ingestion(request: Request, db: SnowflakeConnection = Depends(get_db_connection)):
    """
    Triggers a manual ingestion of all registered technology and AI RSS sources.
    Filters exclusively for content published durante the previous full calendar day.
    """
    start_perf = time.perf_counter()
    logger.info("Manual RSS ingestion trigger received")
    
    try:
        # 1. Fetch from all sources (RSS + ArXiv API + HackerNews API)
        articles = await IngestionService.fetch_all_sources()
        
        # 2. Persist to Snowflake articles_raw
        saved_count = ArticleRepository.upsert_raw_articles(db, articles)
        
        duration = time.perf_counter() - start_perf
        
        # Calculate boundaries for the response info
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
