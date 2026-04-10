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
    """Runs the semantic deduplication pipeline on unclustered articles.

    Groups raw articles into story clusters using URL normalization and
    sentence-transformer embeddings. Each cluster represents one unique news event.
    """
    logger.info("Deduplication triggered", limit=limit)

    try:
        raw_articles = ArticleRepository.get_unclustered_articles(db, limit=limit)
        if not raw_articles:
            return {
                "status": "SKIPPED",
                "message": "No new unclustered articles found",
                "clusters_created": 0
            }

        raw_clusters = await DeduplicationService.process_batch(raw_articles)
        stories = [DeduplicationService.synthesize_story(c) for c in raw_clusters]
        cluster_ids = ArticleRepository.create_clusters_batch(db, stories)

        linkage_data = [
            {"cluster_id": cluster_ids[i], "article_ids": story["article_ids"]}
            for i, story in enumerate(stories)
        ]
        ArticleRepository.link_articles_to_clusters_bulk(db, linkage_data)

        clusters_created = len(cluster_ids)
        articles_linked = sum(len(s["article_ids"]) for s in stories)

        logger.info("Deduplication complete",
                    clusters_created=clusters_created,
                    articles_linked=articles_linked)

        return {
            "status": "SUCCESS",
            "clusters_created": clusters_created,
            "articles_processed": articles_linked,
            "message": f"Created {clusters_created} story clusters from {articles_linked} articles"
        }

    except Exception as e:
        logger.error("Deduplication failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
