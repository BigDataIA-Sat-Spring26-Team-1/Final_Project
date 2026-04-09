import json
from typing import List, Dict, Any
from app.core.logging_conf import get_logger
from snowflake.connector import SnowflakeConnection

logger = get_logger("app.repository.article")

class ArticleRepository:
    """
    Handles persistence and retrieval for the news ingestion feed in Snowflake.
    """

    @staticmethod
    def get_unclassified_articles(conn: SnowflakeConnection, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetches articles that have been ingested but not yet classified by the P2 AI pipeline.
        """
        query = """
        SELECT id, title, summary, extracted_full_text 
        FROM articles_raw 
        WHERE internal_category_weights IS NULL
        LIMIT %s
        """
        try:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            columns = [col[0].lower() for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error("Failed to fetch unclassified articles", error=str(e))
            return []

    @staticmethod
    def update_article_weights(conn: SnowflakeConnection, article_id: str, weights: Dict[str, float]):
        """
        Updates the internal taxonomy weights for a specific article.
        """
        weights_json = json.dumps(weights)
        query = """
        UPDATE articles_raw 
        SET internal_category_weights = PARSE_JSON(%s)
        WHERE id = %s
        """
        try:
            cursor = conn.cursor()
            cursor.execute(query, (weights_json, article_id))
            logger.info("Updated article weights", article_id=article_id)
        except Exception as e:
            logger.error("Failed to update article weights", article_id=article_id, error=str(e))
            raise

    @staticmethod
    def upsert_raw_articles(conn: SnowflakeConnection, articles: List[Dict[str, Any]]) -> int:
        """
        Performs a bulk URL-based deduplication merge into articles_raw.
        Returns the count of successfully merged records.
        """
        if not articles:
            return 0
            
        import uuid
        count = 0
        cursor = conn.cursor()
        
        # We use a merge strategy to avoid duplicates on the same URL
        # For small-medium batches, we can iterate or use a temp table.
        # Given we have 30 sources * ~5 items = 150 items, direct iteration with MERGE is safe.
        merge_query = """
        MERGE INTO articles_raw TARGET
        USING (SELECT %s AS id, %s AS source_name, %s AS source_url, %s AS title, %s AS url, %s AS summary, %s AS published_at, %s AS author, PARSE_JSON(%s) AS source_tags) SOURCE
        ON TARGET.url = SOURCE.url
        WHEN NOT MATCHED THEN
            INSERT (id, source_name, title, url, summary, published_at, source_tags, fetched_at)
            VALUES (SOURCE.id, SOURCE.source_name, SOURCE.title, SOURCE.url, SOURCE.summary, SOURCE.published_at, SOURCE.source_tags, CURRENT_TIMESTAMP())
        """
        
        for art in articles:
            try:
                cursor.execute(merge_query, (
                    str(uuid.uuid4()),
                    art['source_name'],
                    art['source_url'],
                    art['title'],
                    art['url'],
                    art['summary'],
                    art['published_at'],
                    art['author'],
                    json.dumps(art['tags'])
                ))
                count += 1
            except Exception as e:
                logger.error("Merge failed for single article", url=art.get('url'), error=str(e))
                
        return count
