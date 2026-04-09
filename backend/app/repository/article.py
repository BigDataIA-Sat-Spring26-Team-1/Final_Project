import json
import uuid
import pandas as pd
from typing import List, Dict, Any
from app.core.logging_conf import get_logger
from snowflake.connector import SnowflakeConnection
from snowflake.connector.pandas_tools import write_pandas

logger = get_logger("app.repository.article")

class ArticleRepository:
    """Handles persistence and retrieval for news articles and semantic clusters in Snowflake."""

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
            conn.commit()
            logger.info("Updated article weights", article_id=article_id)
        except Exception as e:
            logger.error("Failed to update article weights", article_id=article_id, error=str(e))
            raise

    @staticmethod
    def upsert_raw_articles(conn: SnowflakeConnection, articles: List[Dict[str, Any]]) -> int:
        """Performs high-performance chunked batch MERGE into articles_raw.

        Args:
            conn: Active Snowflake connection.
            articles: List of article dictionaries to ingest.

        Returns:
            int: Number of articles processed across all chunks.
        """
        if not articles:
            return 0
            
        cursor = conn.cursor()
        total_counts = 0
        chunk_size = 50
        
        for i in range(0, len(articles), chunk_size):
            chunk = articles[i : i + chunk_size]
            value_templates = []
            params = []
            
            for art in chunk:
                value_templates.append("(%s, %s, %s, %s, %s, %s, %s, %s, %s)")
                params.extend([
                    str(uuid.uuid4()),
                    art.get('source_name', 'Unknown'),
                    art.get('source_url', ''),
                    art.get('title', 'No Title')[:500],
                    art.get('url', '')[:2000],
                    art.get('summary', ''),
                    art.get('published_at'),
                    art.get('author', '')[:100],
                    json.dumps(art.get('tags', []))
                ])
                
            values_str = ",".join(value_templates)
            merge_query = f"""
            MERGE INTO articles_raw TARGET
            USING (
                SELECT COLUMN1 as id, COLUMN2 as source_name, COLUMN3 as source_url, 
                       COLUMN4 as title, COLUMN5 as url, COLUMN6 as summary, 
                       COLUMN7 as published_at, COLUMN8 as author, PARSE_JSON(COLUMN9) as source_tags
                FROM VALUES {values_str}
            ) SOURCE
            ON TARGET.url = SOURCE.url
            WHEN NOT MATCHED THEN
                INSERT (id, source_name, title, url, summary, published_at, source_tags, fetched_at)
                VALUES (SOURCE.id, SOURCE.source_name, SOURCE.title, SOURCE.url, SOURCE.summary, SOURCE.published_at, SOURCE.source_tags, CURRENT_TIMESTAMP())
            """
            
            try:
                cursor.execute(merge_query, params)
                conn.commit()
                total_counts += len(chunk)
            except Exception as e:
                logger.error("Chunk merge failed", error=str(e), chunk_index=i)
                
        return total_counts

    @staticmethod
    def get_unclustered_articles(conn: SnowflakeConnection, limit: int = 2000) -> List[Dict[str, Any]]:
        """
        Fetches raw articles that have not yet been assigned to a semantic cluster.
        """
        query = """
        SELECT id, title, url, summary, source_name, published_at
        FROM articles_raw 
        WHERE cluster_id IS NULL
        LIMIT %s
        """
        try:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            columns = [col[0].lower() for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error("Failed to fetch unclustered articles", error=str(e))
            return []

    @staticmethod
    def create_clusters_batch(conn: SnowflakeConnection, clusters: List[Dict[str, Any]]) -> List[str]:
        """
        Inserts multiple article clusters in a single round-trip.
        """
        if not clusters:
            return []
            
        import uuid
        cursor = conn.cursor()
        ids = []
        value_templates = []
        params = []
        
        for cluster in clusters:
            cid = str(uuid.uuid4())
            ids.append(cid)
            value_templates.append("(%s, %s, %s, %s, %s)")
            params.extend([
                cid,
                cluster['primary_title'][:500],
                cluster['primary_summary'],
                cluster.get('cluster_size', 1),
                cluster.get('trend_status', 'NEW')
            ])
            
        query = f"""
        INSERT INTO article_clusters (id, primary_title, primary_summary, cluster_size, trend_status)
        VALUES {",".join(value_templates)}
        """
        try:
            cursor.execute(query, params)
            conn.commit()
            return ids
        except Exception as e:
            logger.error("Failed to batch create clusters", error=str(e))
            raise

    @staticmethod
    def link_articles_to_clusters_bulk(conn: SnowflakeConnection, linkage: List[Dict[str, Any]]) -> None:
        """Performs optimized bulk update of article cluster assignments.

        Uses write_pandas to push mapping to a temporary table and then executes
         a single server-side JOIN update for maximum performance.

        Args:
            conn: Active Snowflake connection.
            linkage: List of linkage dicts containing 'cluster_id' and 'article_ids' list.
        """
        if not linkage:
            return
            
        # Flatten the linkage data into a list of pairs
        rows = []
        for item in linkage:
            cid = item['cluster_id']
            for aid in item['article_ids']:
                rows.append({"ARTICLE_ID": aid, "CLUSTER_ID": cid})
        
        df = pd.DataFrame(rows)
        cursor = conn.cursor()
        
        # 1. Create a matching temporary table
        cursor.execute("CREATE OR REPLACE TEMPORARY TABLE linkage_tmp (ARTICLE_ID STRING, CLUSTER_ID STRING)")
        
        # 2. Use the specialized high-speed pandas uploader
        write_pandas(conn, df, table_name='LINKAGE_TMP', schema=conn.schema, database=conn.database)
        
        # 3. Perform the bulk JOIN-UPDATE
        cursor.execute("""
            UPDATE articles_raw a
            SET a.cluster_id = lt.CLUSTER_ID
            FROM linkage_tmp lt
            WHERE a.id = lt.ARTICLE_ID
        """)
        
        conn.commit()
        logger.info("Bulk article linkage complete", article_count=len(rows))

    @staticmethod
    def reset_pipeline_data(conn: SnowflakeConnection):
        """
        Wipes the database for a fresh firehose run.
        """
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE articles_raw")
        cursor.execute("TRUNCATE TABLE article_clusters")
        conn.commit()
        logger.info("Snowflake pipeline data RESET successfully.")
