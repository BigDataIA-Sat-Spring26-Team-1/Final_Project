"""Qdrant re-sync: rebuild the ``articles`` collection from Snowflake.

The dedup pipeline upserts Qdrant points as clusters are formed, but over
time the collection drifts from Snowflake:

* cluster_ids in Qdrant may point at representative articles that have since
  been re-clustered,
* payloads carry stale urls / titles,
* fresh clusters from backfills bypass the dedup DAG entirely.

This module re-indexes every live cluster from ``article_clusters`` using
the cluster id as the Qdrant point id and a fresh OpenAI embedding of
``primary_title + primary_summary``. Running it is idempotent — existing
points are overwritten in place; the collection is *not* wiped first, so
an intermittent failure mid-run simply leaves the older points live until
the next successful run.

Entry point: ``resync_articles_collection(limit=None)`` — reusable by both
the Airflow DAG and ad-hoc ops scripts.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from qdrant_client.models import PointStruct

from app.core.logging_conf import get_logger
from app.db.qdrant import get_qdrant_client, sync_vector_collections
from app.db.snowflake import get_db_connection
from app.services.deduplication import DeduplicationService

logger = get_logger("app.services.qdrant_sync")

COLLECTION = "articles"
# OpenAI's embedding API caps at 2,048 inputs per request. Batch well below
# that to stay comfortable with per-request token limits on long summaries.
EMBED_BATCH = 64
# Qdrant Cloud rejects single requests above ~32 MB. 1,536-dim float vectors
# are ~6 KB each, so 500-point batches stay under 3 MB even with verbose
# payloads.
UPSERT_BATCH = 500


def _fetch_clusters(db, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Pull every live cluster + its representative article url/source."""
    cur = db.cursor()
    query = """
        SELECT c.id,
               c.primary_title,
               c.primary_summary,
               c.cluster_size,
               c.trend_status,
               a.url,
               a.source_name
        FROM article_clusters c
        LEFT JOIN (
            SELECT cluster_id, url, source_name,
                   ROW_NUMBER() OVER (
                       PARTITION BY cluster_id
                       ORDER BY published_at DESC NULLS LAST,
                                fetched_at DESC
                   ) AS rn
            FROM articles_raw
            WHERE cluster_id IS NOT NULL AND url IS NOT NULL AND url <> ''
        ) a ON a.cluster_id = c.id AND a.rn = 1
        WHERE c.primary_title IS NOT NULL
        ORDER BY c.created_at DESC NULLS LAST
    """
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    cur.execute(query)
    return [
        {
            "cluster_id": row[0],
            "title": row[1] or "",
            "summary": row[2] or "",
            "cluster_size": int(row[3] or 1),
            "trend_status": row[4],
            "url": row[5] or "",
            "source_name": row[6] or "",
        }
        for row in cur.fetchall()
    ]


def _embed_text_for(cluster: Dict[str, Any]) -> str:
    """Text the embedding is computed against. Title-heavy + trimmed summary."""
    title = (cluster.get("title") or "").strip()
    summary = (cluster.get("summary") or "").strip()
    if summary:
        summary = summary[:500]
    return f"{title}\n\n{summary}".strip() or "untitled cluster"


async def resync_articles_collection(
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Rebuild Qdrant points for every live cluster. Returns a summary dict."""
    sync_vector_collections()  # ensures the collection exists + right dims

    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        clusters = _fetch_clusters(db, limit=limit)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    if not clusters:
        logger.info("Qdrant resync — no clusters to index")
        return {"clusters": 0, "embedded": 0, "upserted": 0}

    logger.info("Qdrant resync starting", clusters=len(clusters))

    client = get_qdrant_client()
    embedded = 0
    upserted = 0
    errors: List[Tuple[str, str]] = []

    # Embed in bounded batches so a single OpenAI hiccup doesn't take down the
    # entire run — any failing batch is logged and skipped.
    batch: List[Dict[str, Any]] = []
    pending_points: List[PointStruct] = []

    async def _flush_embed_batch(chunk: List[Dict[str, Any]]) -> List[PointStruct]:
        texts = [_embed_text_for(c) for c in chunk]
        vectors = await DeduplicationService.get_embeddings(texts)
        points: List[PointStruct] = []
        for c, vec in zip(chunk, vectors):
            points.append(
                PointStruct(
                    id=str(c["cluster_id"]),
                    vector=vec.tolist() if hasattr(vec, "tolist") else list(vec),
                    payload={
                        "title": c["title"],
                        "summary": c["summary"],
                        "url": c["url"],
                        "source_name": c["source_name"],
                        "sources": [c["source_name"]] if c["source_name"] else [],
                        "cluster_size": c["cluster_size"],
                        "trend_status": c["trend_status"],
                    },
                )
            )
        return points

    def _flush_upsert_batch(points: List[PointStruct]) -> None:
        if not points:
            return
        client.upsert(collection_name=COLLECTION, points=points)

    for cluster in clusters:
        batch.append(cluster)
        if len(batch) >= EMBED_BATCH:
            try:
                new_points = await _flush_embed_batch(batch)
                embedded += len(new_points)
                pending_points.extend(new_points)
            except Exception as exc:  # noqa: BLE001
                logger.error("Embed batch failed; skipping", error=str(exc))
                errors.append(("embed", str(exc)[:250]))
            batch = []

            while len(pending_points) >= UPSERT_BATCH:
                chunk, pending_points = (
                    pending_points[:UPSERT_BATCH],
                    pending_points[UPSERT_BATCH:],
                )
                try:
                    _flush_upsert_batch(chunk)
                    upserted += len(chunk)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Qdrant upsert failed; skipping", error=str(exc))
                    errors.append(("upsert", str(exc)[:250]))

    # Tail flush.
    if batch:
        try:
            pending_points.extend(await _flush_embed_batch(batch))
            embedded = sum(1 for _ in pending_points)  # recount
        except Exception as exc:  # noqa: BLE001
            logger.error("Tail embed batch failed", error=str(exc))
            errors.append(("embed", str(exc)[:250]))
    for i in range(0, len(pending_points), UPSERT_BATCH):
        chunk = pending_points[i : i + UPSERT_BATCH]
        try:
            _flush_upsert_batch(chunk)
            upserted += len(chunk)
        except Exception as exc:  # noqa: BLE001
            logger.error("Tail Qdrant upsert failed", error=str(exc))
            errors.append(("upsert", str(exc)[:250]))

    logger.info(
        "Qdrant resync complete",
        clusters=len(clusters),
        embedded=embedded,
        upserted=upserted,
        errors=len(errors),
    )
    return {
        "clusters": len(clusters),
        "embedded": embedded,
        "upserted": upserted,
        "errors": errors,
    }
