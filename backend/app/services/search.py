import json
from datetime import date as _date
from typing import List, Dict, Any, Optional
from app.core.logging_conf import get_logger
from app.db.qdrant import get_qdrant_client
from app.services.deduplication import DeduplicationService
from snowflake.connector import SnowflakeConnection

logger = get_logger("app.services.search")

def _filter_by_edition_date(
    results: List[Dict[str, Any]],
    edition_date: Optional[str],
    limit: int,
    db: Optional[SnowflakeConnection] = None,
    window_days: int = 1,
) -> List[Dict[str, Any]]:
    if not edition_date or db is None:
        return results[:limit]
    try:
        _date.fromisoformat(edition_date)
    except ValueError:
        return results[:limit]
    cluster_ids = [r.get("cluster_id") for r in results if r.get("cluster_id")]
    if not cluster_ids:
        return results[:limit]

    placeholders = ",".join(["%s"] * len(cluster_ids))
    cur = db.cursor()
    try:
        cur.execute(
            f"""
            SELECT DISTINCT id, cluster_id
            FROM articles_raw
            WHERE (id IN ({placeholders}) OR cluster_id IN ({placeholders}))
              AND published_at IS NOT NULL
              AND CAST(published_at AS DATE)
                  BETWEEN DATEADD(day, -%s, %s::DATE) AND %s::DATE
            """,
            (*cluster_ids, *cluster_ids, window_days, edition_date, edition_date),
        )
        fresh_ids: set = set()
        for aid, cid in cur.fetchall():
            if aid:
                fresh_ids.add(aid)
            if cid:
                fresh_ids.add(cid)
    except Exception as exc: 
        logger.warning(
            "Edition-date filter query failed; returning unscoped top-N",
            edition_date=edition_date,
            error=str(exc),
        )
        return results[:limit]

    scoped = [r for r in results if r.get("cluster_id") in fresh_ids]
    return scoped[:limit]

class SearchService:
    @staticmethod
    async def get_personalized_recommendations(
        user_id: str,
        limit: int,
        db: SnowflakeConnection,
        edition_date: Optional[str] = None,
    ) -> Dict[str, Any]:

        cur = db.cursor()
        cur.execute(
            """
            SELECT explicit_category_weights, behavioral_category_weights,
                   job_title, seniority, persona_archetype, bio_summary
            FROM user_personas
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()

        explicit_w: dict = {}
        behavioral_w: dict = {}
        persona_text_parts: list[str] = []
        company_query: Optional[str] = None

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
            for field in row[2:6]:  
                if field and isinstance(field, str) and field.strip():
                    persona_text_parts.append(field.strip())
        else:
            cur.execute(
                """
                SELECT name, industry, description, target_audience,
                       key_products, content_pillars
                FROM companies
                WHERE id = %s
                """,
                (user_id,),
            )
            company_row = cur.fetchone()
            if not company_row:
                return None
            parts = [str(v) for v in company_row if v and str(v).strip()]
            company_query = " ".join(parts).strip() or "enterprise AI technology"
            logger.info(
                "Using company profile as semantic query",
                user_id=user_id,
                query=company_query[:180],
            )

        all_categories = set(explicit_w.keys()) | set(behavioral_w.keys())
        weights = {
            cat: round(explicit_w.get(cat, 0.0) * 0.8 + behavioral_w.get(cat, 0.0) * 0.2, 4)
            for cat in all_categories
        }
        weights = {cat: w for cat, w in weights.items() if w >= 0.05}

        if company_query:
            search_query = company_query
        else:
            top_cats = [
                cat for cat, _ in sorted(weights.items(), key=lambda x: x[1], reverse=True)
            ]

            parts: list[str] = []
            parts.extend(persona_text_parts)
            parts.extend(top_cats)
            search_query = " ".join(parts).strip() or "latest major technology industry news"

        logger.info("Formulated semantic persona query", user_id=user_id, query=search_query[:180])

        query_embeddings = await DeduplicationService.get_embeddings([search_query])
        query_vector = query_embeddings[0].tolist()

        qdrant_limit = max(limit * 5, limit) if edition_date else limit
        q_client = get_qdrant_client()
        response = q_client.query_points(
            collection_name="articles",
            query=query_vector,
            limit=qdrant_limit,
        )
        
        results = []
        for hit in response.points:
            # `categories` MUST be surfaced on every hit — the frontend
            # feedback flow multiplies user-feedback deltas by the
            # article's category weights. Missing categories → feedback
            # is a no-op (see app/api/personas.record_article_feedback),
            # which was the actual "likes aren't sticking" bug. Fall back
            # through payload keys the dedup upserter + qdrant_sync DAG
            # both write, then enrich from Snowflake below if still empty.
            payload = hit.payload or {}
            results.append({
                "cluster_id": str(hit.id),
                "score": round(hit.score, 4),
                "title": payload.get("title", ""),
                "url": payload.get("url", ""),
                "summary": payload.get("summary", ""),
                "sources": payload.get("sources", []),
                "source_name": payload.get("source_name") or "",
                "cluster_size": payload.get("cluster_size", 1),
                "trend_status": payload.get("trend_status"),
                "categories": payload.get("category_weights") or payload.get("categories") or {},
            })

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
            except Exception as e:
                logger.warning("Recommendation url enrichment failed", error=str(e))

        # Category enrichment — Qdrant payloads only gained `category_weights`
        # in the 2026-04-24 write path, so points upserted earlier come back
        # with empty `categories`. Hydrate from article_clusters so the
        # like/dislike feedback loop multiplies against real weights.
        needs_cats = [r for r in results if not (r.get("categories") or {})]
        if needs_cats and db is not None:
            try:
                cids = [r["cluster_id"] for r in needs_cats]
                cur = db.cursor()
                placeholders = ",".join(["%s"] * len(cids))
                cur.execute(
                    f"SELECT id, category_weights FROM article_clusters "
                    f"WHERE id IN ({placeholders})",
                    tuple(cids),
                )
                by_id_cats: dict = {}
                for row in cur.fetchall():
                    raw = row[1]
                    if raw is None:
                        continue
                    if isinstance(raw, dict):
                        by_id_cats[row[0]] = raw
                    else:
                        try:
                            by_id_cats[row[0]] = json.loads(raw) if isinstance(raw, str) else {}
                        except json.JSONDecodeError:
                            by_id_cats[row[0]] = {}
                for r in needs_cats:
                    cats = by_id_cats.get(r["cluster_id"])
                    if cats:
                        r["categories"] = cats
            except Exception as e:  # noqa: BLE001
                logger.warning("Category enrichment failed", error=str(e))

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
                if enriched_results:

                    try:
                        import numpy as np

                        top_pool = enriched_results[:60]
                        texts = [
                            f"{r.get('title', '')} {r.get('summary', '')}".strip()
                            or r.get("title", "")
                            for r in top_pool
                        ]
                        title_vecs = await DeduplicationService.get_embeddings(texts)
                        qv = np.asarray(query_vector, dtype=float)
                        q_norm = qv / (np.linalg.norm(qv) or 1.0)
                        for r, vec in zip(top_pool, title_vecs):
                            v = np.asarray(vec, dtype=float)
                            v_norm = v / (np.linalg.norm(v) or 1.0)
                            cos = float(np.dot(q_norm, v_norm))

                            r["score"] = round(0.7 * cos + 0.3 * r["score"], 4)
                        top_pool.sort(key=lambda r: r["score"], reverse=True)
                        results = top_pool
                        logger.info(
                            "Snowflake fallback re-ranked by query similarity",
                            user_id=user_id,
                            returned=len(results),
                            top_score=results[0]["score"] if results else None,
                        )
                    except Exception as e:  
                        logger.warning(
                            "Query-aware re-ranking failed; using trend order",
                            error=str(e),
                        )
                        results = enriched_results
            except Exception as e: 
                logger.warning("Snowflake fallback recommendations failed", error=str(e))

        results = _filter_by_edition_date(results, edition_date, limit, db=db)

        return {
            "user_id": user_id,
            "semantic_basis": search_query,
            "results": results
        }