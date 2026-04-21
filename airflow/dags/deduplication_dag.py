"""Semantic deduplication DAG.

fetch_unclustered → process (URL + embedding dedup) → persist clusters + links

The original version passed a Snowflake connection into the dedup service,
which was wrong — ``DeduplicationService.process_batch`` wants a list of
article dicts. Fixed here.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from airflow import DAG
from airflow.operators.python import PythonOperator

from _common import default_args, ensure_backend_on_path

log = logging.getLogger("airflow.task")


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def fetch_unclustered(**context):
    """Pull up to N raw articles that have never been assigned a cluster.

    Batch size is env-tunable so operators can throttle without touching code."""
    ensure_backend_on_path()
    import os

    from app.db.snowflake import get_db_connection
    from app.repository.article import ArticleRepository

    batch_size = int(os.environ.get("DEDUP_BATCH_SIZE", "2000"))
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        articles = ArticleRepository.get_unclustered_articles(db, limit=batch_size)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    log.info("Fetched unclustered articles", count=len(articles))
    return articles


def cluster_articles(**context):
    """Run the dual-layer (URL + embedding) deduplicator."""
    ensure_backend_on_path()
    from app.services.deduplication import DeduplicationService

    ti = context["ti"]
    articles: List[Dict[str, Any]] = ti.xcom_pull(task_ids="fetch_unclustered") or []
    if not articles:
        log.info("Nothing to deduplicate.")
        return []

    clusters = _run_async(DeduplicationService.process_batch(articles))
    log.info("Dedup complete", clusters=len(clusters), from_articles=len(articles))

    # Return cluster synthesis output — raw cluster dicts carry embeddings that
    # are far too large to round-trip through XCom. We keep only what persist
    # needs.
    synthesized = [DeduplicationService.synthesize_story(c) for c in clusters]
    return synthesized


def persist_clusters(**context):
    """Write new clusters and link raw articles to them."""
    ensure_backend_on_path()
    from app.db.snowflake import get_db_connection
    from app.repository.article import ArticleRepository

    ti = context["ti"]
    stories: List[Dict[str, Any]] = ti.xcom_pull(task_ids="cluster_articles") or []
    if not stories:
        log.info("No clusters to persist.")
        return {"created": 0, "linked": 0}

    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        cluster_ids = ArticleRepository.create_clusters_batch(db, stories)
        linkage = [
            {"cluster_id": cid, "article_ids": story["article_ids"]}
            for cid, story in zip(cluster_ids, stories)
            if story.get("article_ids")
        ]
        ArticleRepository.link_articles_to_clusters_bulk(db, linkage)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    total_linked = sum(len(l["article_ids"]) for l in linkage)
    log.info("Clusters persisted", created=len(cluster_ids), linked=total_linked)
    return {"created": len(cluster_ids), "linked": total_linked}


with DAG(
    dag_id="deduplication_dag",
    default_args=default_args(),
    description="URL + semantic deduplication of raw articles into clusters",
    schedule_interval="@hourly",
    catchup=False,
    max_active_runs=1,
    tags=["deduplication", "curateai"],
) as dag:
    t_fetch = PythonOperator(task_id="fetch_unclustered", python_callable=fetch_unclustered)
    t_cluster = PythonOperator(task_id="cluster_articles", python_callable=cluster_articles)
    t_persist = PythonOperator(task_id="persist_clusters", python_callable=persist_clusters)

    t_fetch >> t_cluster >> t_persist
