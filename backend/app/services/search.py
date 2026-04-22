import json
from typing import List, Dict, Any
from app.core.logging_conf import get_logger
from app.db.qdrant import get_qdrant_client
from app.services.deduplication import DeduplicationService
from snowflake.connector import SnowflakeConnection

logger = get_logger("app.services.search")

class SearchService:
    @staticmethod
    async def get_personalized_recommendations(
        user_id: str, 
        limit: int, 
        db: SnowflakeConnection
    ) -> Dict[str, Any]:
        """
        Logic for retrieving personalized content for a user.
        Shared by the API and the Agents.
        """
        # 1. Fetch User Weights from Snowflake. When the id doesn't match a
        # persona (e.g., B2B callers pass a company_id here) we fall back to
        # deriving a query from the company profile instead of returning None —
        # a corporate tenant should still get a semantic search even when no
        # behavioural signal is captured for them yet.
        cur = db.cursor()
        cur.execute("""
            SELECT explicit_category_weights, behavioral_category_weights
            FROM user_personas
            WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()

        explicit_w: dict = {}
        behavioral_w: dict = {}
        company_fallback: str | None = None

        if row:
            explicit_weights = row[0]
            behavioral_weights = row[1]
            if explicit_weights:
                try:
                    explicit_w = json.loads(explicit_weights)
                except (json.JSONDecodeError, TypeError):
                    pass
            if behavioral_weights:
                try:
                    behavioral_w = json.loads(behavioral_weights)
                except (json.JSONDecodeError, TypeError):
                    pass
        else:
            # Maybe this id is actually a company. Build a query from its name
            # + industry + description so the B2B agent gets real results.
            cur.execute(
                """
                SELECT name, industry, description
                FROM companies
                WHERE id = %s
                """,
                (user_id,),
            )
            company_row = cur.fetchone()
            if not company_row:
                return None
            company_fallback = " ".join(
                str(v) for v in company_row if v
            ).strip() or "enterprise AI technology"
            logger.info(
                "Persona not found; using company profile as semantic query",
                user_id=user_id,
                query=company_fallback[:120],
            )

        # P4 blend: refined = explicit × 0.8 + behavioral × 0.2
        # Categories below 0.05 are pruned as noise.
        all_categories = set(explicit_w.keys()) | set(behavioral_w.keys())
        weights = {
            cat: round(explicit_w.get(cat, 0.0) * 0.8 + behavioral_w.get(cat, 0.0) * 0.2, 4)
            for cat in all_categories
        }
        weights = {cat: w for cat, w in weights.items() if w >= 0.05}

        if company_fallback:
            search_query = company_fallback
        elif not weights:
            search_query = "latest major technology industry news"
        else:
            top_cats = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            search_query = " ".join([cat[0] for cat in top_cats])
            
        logger.info("Formulated semantic persona query", user_id=user_id, query=search_query)

        # 2. Vectorize query
        query_embeddings = await DeduplicationService.get_embeddings([search_query])
        query_vector = query_embeddings[0].tolist()

        # 3. Query Qdrant
        q_client = get_qdrant_client()
        response = q_client.query_points(
            collection_name="articles",
            query=query_vector,
            limit=limit,
        )
        
        results = []
        for hit in response.points:
            results.append({
                "cluster_id": str(hit.id),
                "score": round(hit.score, 4),
                "title": hit.payload.get("title", ""),
                "url": hit.payload.get("url", ""),
                "summary": hit.payload.get("summary", ""),
                "sources": hit.payload.get("sources", []),
                "cluster_size": hit.payload.get("cluster_size", 1)
            })
            
        return {
            "user_id": user_id,
            "semantic_basis": search_query,
            "results": results
        }