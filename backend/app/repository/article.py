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
