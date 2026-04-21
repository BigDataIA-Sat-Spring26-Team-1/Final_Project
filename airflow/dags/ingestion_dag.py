"""Daily content ingestion DAG.

Parallel fan-out across three crawlers (RSS, ArXiv, HackerNews), then a single
serialized persistence leg. Each crawler pushes its articles into XCom; the
merge task collects them and writes to Snowflake in one chunked MERGE.

If the cache invalidation task fails we still consider the run successful —
worst case stale archetype caches get served for a few hours until the next
run clears them.
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
    """Run a coroutine in a fresh event loop. Airflow tasks are synchronous;
    ``asyncio.run()`` cannot be called twice on some Python builds, so we make
    a loop explicitly."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def fetch_rss(**context):
    ensure_backend_on_path()
    from app.services.ingestion import IngestionService

    articles = _run_async(IngestionService.fetch_all_rss())
    log.info("RSS crawl produced %d articles", len(articles))
    return articles


def fetch_arxiv(**context):
    ensure_backend_on_path()
    from app.services.ingestion import IngestionService

    articles = _run_async(IngestionService.fetch_arxiv_api())
    log.info("ArXiv crawl produced %d articles", len(articles))
    return articles


def fetch_hackernews(**context):
    ensure_backend_on_path()
    from app.services.ingestion import IngestionService

    articles = _run_async(IngestionService.fetch_hn_api())
    log.info("HackerNews crawl produced %d articles", len(articles))
    return articles


def persist_articles(**context):
    """Union the three XCom payloads and MERGE into Snowflake."""
    ensure_backend_on_path()
    from app.db.snowflake import get_db_connection
    from app.repository.article import ArticleRepository

    ti = context["ti"]
    merged: List[Dict[str, Any]] = []
    for upstream in ("fetch_rss", "fetch_arxiv", "fetch_hackernews"):
        payload = ti.xcom_pull(task_ids=upstream) or []
        merged.extend(payload)

    if not merged:
        log.warning("No articles to persist — upstream crawlers returned empty.")
        return {"saved": 0, "received": 0}

    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        saved = ArticleRepository.upsert_raw_articles(db, merged)
    finally:
        # The generator wraps a try/finally that closes the connection — we
        # have to drive it to completion or the pool leaks.
        try:
            next(db_gen)
        except StopIteration:
            pass

    log.info("Persisted articles", received=len(merged), saved=saved)
    return {"saved": saved, "received": len(merged)}


def invalidate_caches(**context):
    """Drop archetype caches so new content reaches readers on the next fetch."""
    ensure_backend_on_path()
    from app.core.cache import INTERNAL_CACHE

    ti = context["ti"]
    stats = ti.xcom_pull(task_ids="persist_articles") or {"saved": 0}
    if stats.get("saved", 0) > 0:
        INTERNAL_CACHE.clear()
        log.info("Internal cache cleared after successful ingestion")
    else:
        log.info("No new articles saved — skipping cache invalidation")


with DAG(
    dag_id="ingestion_dag",
    default_args=default_args(),
    description="Parallel multi-source ingestion (RSS, ArXiv, HN) → Snowflake",
    schedule_interval="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["ingestion", "curateai"],
) as dag:
    t_rss = PythonOperator(task_id="fetch_rss", python_callable=fetch_rss)
    t_arxiv = PythonOperator(task_id="fetch_arxiv", python_callable=fetch_arxiv)
    t_hn = PythonOperator(task_id="fetch_hackernews", python_callable=fetch_hackernews)
    t_persist = PythonOperator(task_id="persist_articles", python_callable=persist_articles)
    t_invalidate = PythonOperator(task_id="invalidate_caches", python_callable=invalidate_caches)

    [t_rss, t_arxiv, t_hn] >> t_persist >> t_invalidate
