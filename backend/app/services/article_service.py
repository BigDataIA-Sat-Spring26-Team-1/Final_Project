import time
import asyncio
from typing import List, Dict, Any
from snowflake.connector import SnowflakeConnection

from app.repository.article import ArticleRepository
from app.services.llm_articles import ArticleIntelligenceService
from app.core.logging_conf import get_logger

logger = get_logger("app.services.article_orchestrator")

class ArticleOrchestratorService:
    """
    Manages the bulk classification of the daily article feed.
    Designed for periodic execution via Airflow or Cron.
    """

    @classmethod
    async def classify_pending_articles(cls, db: SnowflakeConnection, batch_size: int = 10) -> Dict[str, Any]:
        """
        Fetches a batch of unclassified articles and runs parallel AI categorization.
        """
        start_time = time.time()
        
        # 1. Fetch unclassified candidates
        articles = ArticleRepository.get_unclassified_articles(db, limit=batch_size)
        if not articles:
            logger.info("No pending articles to classify.")
            return {"processed": 0, "latency": 0}

        logger.info(f"Starting classification for {len(articles)} articles.")

        async def process_one(article: Dict[str, Any]):
            try:
                # 2. Extract weights via AI
                weights = await ArticleIntelligenceService.classify_article(
                    title=article.get("title", ""),
                    summary=article.get("summary", ""),
                    content=article.get("extracted_full_text", "")
                )
                
                # 3. Sync to Snowflake (Sync call within repo but wrapped in async loop)
                ArticleRepository.update_article_weights(
                    conn=db,
                    article_id=article["id"],
                    weights=weights.model_dump()
                )
                return True
            except Exception as e:
                logger.error("Failed to process article in batch", article_id=article.get("id"), error=str(e))
                return False

        # 4. Execute parallel classification with concurrency control
        # Using a semaphore to avoid overloading the LLM rate limit even with retries
        semaphore = asyncio.Semaphore(5)
        
        async def sem_process(article):
            async with semaphore:
                return await process_one(article)

        results = await asyncio.gather(*(sem_process(a) for a in articles))
        
        success_count = sum(1 for r in results if r)
        duration = time.time() - start_time
        
        logger.info("Article classification batch complete", 
                    total=len(articles), 
                    success=success_count, 
                    latency=duration)
        
        return {
            "total": len(articles),
            "success": success_count,
            "latency_seconds": duration
        }
