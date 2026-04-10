from app.services.trend import TrendService
from app.core.logging_conf import get_logger
from app.db.snowflake import get_db_connection

from snowflake.connector import SnowflakeConnection
from fastapi import APIRouter, Depends, HTTPException

logger = get_logger("app.api.trend")
router = APIRouter()


@router.post("/rank", status_code=202)
async def rank_daily_news(db: SnowflakeConnection = Depends(get_db_connection)):
    """Ranks all story clusters by editorial density and social signals.

    Aggregates category weights from individual articles into cluster-level
    intelligence, then assigns BREAKING / TRENDING / REGULAR status based on
    how many independent sources confirmed the story.
    """
    logger.info("Trend ranking requested")
    try:
        results = await TrendService.rank_daily_clusters(db)
        return {
            "status": "success",
            "message": f"Ranked {results['processed']} story clusters.",
            "latency_seconds": results.get("latency", 0)
        }
    except Exception as e:
        logger.error("Trend ranking failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
