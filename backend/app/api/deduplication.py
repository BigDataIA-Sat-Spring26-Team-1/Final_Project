from app.core.logging_conf import get_logger
from app.db.snowflake import get_db_connection
from app.repository.article import ArticleRepository
from app.services.deduplication import DeduplicationService

from snowflake.connector import SnowflakeConnection
from fastapi import APIRouter, Depends, HTTPException

logger = get_logger("app.api.deduplication")
router = APIRouter()

@router.post("/process")
async def run_deduplication(limit: int = 1000, db: SnowflakeConnection = Depends(get_db_connection)):
    """
    Triggers the deduplication pipeline:
    1. Fetches unclustered articles from Snowflake.
    2. Clusters them semantically.
    3. Persists synthesized story clusters.
    4. Links raw articles to their clusters.
    """
    logger.info("Deduplication process triggered", limit=limit)
    
    try:
        # 1. Fetch unclustered items
        raw_articles = ArticleRepository.get_unclustered_articles(db, limit=limit)
        if not raw_articles:
            return {
                "status": "SKIPPED",
                "message": "No new unclustered articles found",
                "clusters_created": 0
            }
            
        # 2. Process clusters
        raw_clusters = DeduplicationService.process_batch(raw_articles)
        
        # 3. Synthesize story objects for batch insert
        stories = [DeduplicationService.synthesize_story(c) for c in raw_clusters]
        
        # 4. Batch Create Clusters
        cluster_ids = ArticleRepository.create_clusters_batch(db, stories)
        
        # 5. Prepare and Batch Link Articles
        linkage_data = []
        for i, story in enumerate(stories):
            linkage_data.append({
                "cluster_id": cluster_ids[i],
                "article_ids": story["article_ids"]
            })
            
        ArticleRepository.link_articles_to_clusters_bulk(db, linkage_data)
        
        clusters_created = len(cluster_ids)
        articles_linked = sum(len(s["article_ids"]) for s in stories)
        
        logger.info("Batch deduplication successful", 
                    clusters_created=clusters_created, 
                    articles_linked=articles_linked)
                    
        return {
            "status": "SUCCESS",
            "clusters_created": clusters_created,
            "articles_processed": articles_linked,
            "message": f"Successfully synthesized {clusters_created} stories from {articles_linked} articles"
        }
        
    except Exception as e:
        logger.error("Deduplication failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
