from app.core.logging_conf import get_logger
from app.services.search import SearchService
from app.db.snowflake import get_db_connection
from snowflake.connector import SnowflakeConnection
from fastapi import APIRouter, Depends, HTTPException, Query

logger = get_logger("app.api.search")
router = APIRouter()

@router.get("/recommendations")
async def get_user_recommendations(
    user_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: SnowflakeConnection = Depends(get_db_connection)
):
    """
    P3 Retrieval Router: Fetches top personalized articles for a specific user.
    """
    logger.info("Fetching personalized recommendations via API", user_id=user_id, limit=limit)
    
    try:
        results = await SearchService.get_personalized_recommendations(user_id, limit, db)
        if not results:
            raise HTTPException(status_code=404, detail="User persona not found")
            
        return {
            "status": "SUCCESS",
            **results
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Search API failure", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
