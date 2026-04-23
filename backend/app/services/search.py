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

        # URL enrichment. Qdrant payloads historically stored the representative
        # article's id — look those up in articles_raw first.
        needs_url = [r for r in results if not r.get("url")]
        if needs_url and db is not None:
            try:
                missing_ids = [r["cluster_id"] for r in needs_url]
                cur = db.cursor()
                placeholders = ",".join(["%s"] * len(missing_ids))
                cur.execute(
                    f"SELECT id, url, source_name FROM articles_raw "
                    f"WHERE id IN ({placeholders})",
                    tuple(missing_ids),
                )
                by_id = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
                for r in needs_url:
                    enriched = by_id.get(r["cluster_id"])
                    if enriched:
                        r["url"] = enriched[0] or ""
                        if enriched[1] and enriched[1] not in r.get("sources", []):
                            r["sources"] = [enriched[1], *(r.get("sources") or [])]
            except Exception as e:  # noqa: BLE001
                logger.warning("Recommendation url enrichment failed", error=str(e))

        # If Qdrant's vectors are stale (a common state during demos — the
        # collection was seeded from an older ingestion), the id-based lookup
        # above returns nothing. In that case fall back to a Snowflake-native
        # recommendation driven by the user's category weights joined to the
        # trend ranking, so every card still renders with a real URL.
        if db is not None and all(not r.get("url") for r in results):
            try:
                cur = db.cursor()
                cur.execute(
                    """
                    SELECT a.id,
                           a.title,
                           a.url,
                           a.source_name,
                           a.summary,
                           c.final_trend_score,
                           c.cluster_size,
                           c.trend_status,
                           c.category_weights
                    FROM article_clusters c
                    JOIN (
                        SELECT cluster_id, id, title, url, source_name, summary,
                               ROW_NUMBER() OVER (
                                   PARTITION BY cluster_id
                                   ORDER BY published_at DESC NULLS LAST,
                                            fetched_at DESC
                               ) AS rn
                        FROM articles_raw
                        WHERE cluster_id IS NOT NULL AND url IS NOT NULL AND url <> ''
                    ) a ON a.cluster_id = c.id AND a.rn = 1
                    WHERE c.final_trend_score IS NOT NULL
                    ORDER BY c.final_trend_score DESC NULLS LAST
                    LIMIT %s
                    """,
                    (limit * 3,),
                )
                rows = cur.fetchall()

                # Rank by overlap with user's weights when available; otherwise
                # keep the raw trend ordering.
                weights_lc = {k.lower(): v for k, v in (weights or {}).items()}

                def overlap_score(cat_weights_variant) -> float:
                    if not cat_weights_variant:
                        return 0.0
                    try:
                        parsed = (
                            cat_weights_variant
                            if isinstance(cat_weights_variant, dict)
                            else json.loads(cat_weights_variant)
                        )
                    except (TypeError, ValueError, json.JSONDecodeError):
                        return 0.0
                    return sum(
                        float(v) * float(weights_lc.get(str(k).lower(), 0.0))
                        for k, v in (parsed or {}).items()
                    )

                enriched_results: list[Dict[str, Any]] = []
                for row in rows:
                    trend_score = float(row[5] or 0.0)
                    overlap = overlap_score(row[8])
                    combined = (overlap * 100.0) + trend_score
                    enriched_results.append(
                        {
                            "cluster_id": str(row[0]),
                            "score": round(combined / 200.0, 4),
                            "title": row[1] or "",
                            "url": row[2] or "",
                            "summary": row[4] or "",
                            "sources": [row[3]] if row[3] else [],
                            "cluster_size": int(row[6] or 1),
                            "trend_status": row[7],
                            "categories": (
                                row[8]
                                if isinstance(row[8], dict)
                                else (json.loads(row[8]) if row[8] else {})
                            ),
                        }
                    )

                enriched_results.sort(key=lambda r: r["score"], reverse=True)
                # Only replace the Qdrant results when the fallback actually
                # produced something — otherwise we'd nuke valid hits for a
                # test/empty-Snowflake environment.
                if enriched_results:
                    results = enriched_results[:limit]
                    logger.info(
                        "Used Snowflake fallback recommendations",
                        user_id=user_id,
                        returned=len(results),
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("Snowflake fallback recommendations failed", error=str(e))

        return {
            "user_id": user_id,
            "semantic_basis": search_query,
            "results": results
        }