import json
import time
import pandas as pd
from typing import Dict, Any
from app.core.logging_conf import get_logger
from snowflake.connector import SnowflakeConnection
from snowflake.connector.pandas_tools import write_pandas

logger = get_logger("app.services.trend")

class TrendService:
    """
    Analyzes story clusters to calculate their global trend ranking.
    Uses bulk SQL operations for near-instant performance.
    """

    BREAKING_THRESHOLD = 3
    TRENDING_THRESHOLD = 2

    @classmethod
    async def rank_daily_clusters(cls, db: SnowflakeConnection) -> Dict[str, Any]:
        """
        Bulk-ranks all clusters using a single fetch + single bulk update.
        """
        start_time = time.time()
        cur = db.cursor()

        # 1. SINGLE QUERY: Fetch all clusters with their article counts and weights in one shot
        cur.execute("""
            SELECT 
                c.id AS cluster_id,
                c.social_popularity_score,
                COUNT(a.id) AS article_count,
                ARRAY_AGG(a.internal_category_weights) AS all_weights
            FROM article_clusters c
            LEFT JOIN articles_raw a ON a.cluster_id = c.id
            GROUP BY c.id, c.social_popularity_score
        """)
        columns = [col[0].lower() for col in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]

        if not rows:
            logger.info("No clusters found for trend analysis.")
            return {"processed": 0, "latency": 0}

        # 2. Calculate scores in Python (instant)
        update_rows = []
        for row in rows:
            cluster_size = row["article_count"] or 1
            social_signal = row["social_popularity_score"] or 0.0

            # Aggregate weights from the array
            cluster_weights = cls._aggregate_weights_from_array(row.get("all_weights"))

            status, boost = cls._calculate_status_and_boost(cluster_size, social_signal)
            final_score = (cluster_size * 10) + social_signal + boost

            update_rows.append({
                "CLUSTER_ID": row["cluster_id"],
                "CATEGORY_WEIGHTS": json.dumps(cluster_weights),
                "TREND_STATUS": status,
                "FINAL_TREND_SCORE": final_score,
                "CLUSTER_SIZE": cluster_size
            })

        # 3. SINGLE BULK UPDATE via write_pandas + JOIN
        df = pd.DataFrame(update_rows)
        cur.execute("CREATE OR REPLACE TEMPORARY TABLE trend_tmp (CLUSTER_ID STRING, CATEGORY_WEIGHTS STRING, TREND_STATUS STRING, FINAL_TREND_SCORE FLOAT, CLUSTER_SIZE INT)")
        write_pandas(db, df, table_name='TREND_TMP', schema=db.schema, database=db.database)

        cur.execute("""
            UPDATE article_clusters c
            SET c.category_weights = PARSE_JSON(t.CATEGORY_WEIGHTS),
                c.trend_status = t.TREND_STATUS,
                c.final_trend_score = t.FINAL_TREND_SCORE,
                c.cluster_size = t.CLUSTER_SIZE
            FROM trend_tmp t
            WHERE c.id = t.CLUSTER_ID
        """)
        db.commit()

        latency = time.time() - start_time
        logger.info("Daily trend ranking complete",
                    clusters_processed=len(update_rows),
                    latency_sec=round(latency, 2))

        return {
            "processed": len(update_rows),
            "latency": round(latency, 2)
        }

    @staticmethod
    def _aggregate_weights_from_array(weights_array) -> Dict[str, float]:
        """Aggregates category weights from Snowflake ARRAY_AGG result."""
        if not weights_array:
            return {}

        aggregated = {}
        counts = {}

        # weights_array comes as a JSON string from Snowflake
        if isinstance(weights_array, str):
            try:
                weights_array = json.loads(weights_array)
            except Exception:
                return {}

        for item in weights_array:
            if not item:
                continue
            # Each item might be a JSON string or already a dict
            if isinstance(item, str):
                try:
                    item = json.loads(item)
                except Exception:
                    continue

            for cat, val in item.items():
                if isinstance(val, (int, float)):
                    aggregated[cat] = aggregated.get(cat, 0.0) + val
                    counts[cat] = counts.get(cat, 0) + 1

        return {cat: round(val / counts[cat], 3) for cat, val in aggregated.items() if counts.get(cat, 0) > 0}

    @classmethod
    def _calculate_status_and_boost(cls, cluster_size: int, social_signal: float) -> tuple[str, float]:
        """Status assignment logic from trend_detection_prototype.py"""
        status = "REGULAR"
        boost = 0

        if cluster_size >= cls.BREAKING_THRESHOLD:
            status = "BREAKING"
            boost += 50
        elif cluster_size >= cls.TRENDING_THRESHOLD:
            status = "TRENDING"
            boost += 20

        if social_signal >= 500:
            status = "BREAKING-VIRAL" if status == "BREAKING" else "VIRAL"
            boost += 40
        elif social_signal >= 150:
            if status == "REGULAR":
                status = "COMMUNITY-PICK"
            boost += 15

        return status, boost
