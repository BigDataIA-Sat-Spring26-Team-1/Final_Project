"""Qdrant re-sync DAG.

Pipeline position (daily order, UTC — 6:30 AM EDT stagger):

    10:30   ingestion_dag         — pulls articles_raw
    hourly  deduplication_dag     — clusters raw → article_clusters (inline Qdrant upserts)
    10:50   trend_dag             — ranks article_clusters
    11:05   qdrant_sync_dag       — ← this DAG: reconciles Qdrant vs Snowflake
    11:20   b2c_personalization   — per-user daily_selections
    11:50   b2c_newsletter_dag    — reads the reconciled Qdrant for retrieval

``deduplication_dag`` already upserts Qdrant points for *new* clusters as
they're formed, but over time the collection drifts from Snowflake (merges,
stale payloads, backfills that bypass dedup). This DAG rebuilds the
``articles`` collection from ``article_clusters`` — the authoritative
source — every morning at 11:05 UTC. That slot runs *after* trend ranking
finishes and *before* the consumer DAGs (personalization + newsletter)
read Qdrant for retrieval.

The helper is idempotent (upserts in place; does NOT wipe the collection
first, so an interrupted run leaves older points live until the next
successful one). Trigger manually via ``{"limit": 500}`` in
``dag_run.conf`` to cap the scope for a smoke-test run.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

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


def resync_qdrant(**context) -> Dict[str, Any]:
    """Re-embed every live cluster and upsert into the Qdrant articles collection."""
    ensure_backend_on_path()
    from app.services.qdrant_sync import resync_articles_collection

    conf = context.get("dag_run").conf if context.get("dag_run") else {}
    limit = (conf or {}).get("limit")
    if limit is not None:
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = None

    summary = _run_async(resync_articles_collection(limit=limit))
    log.info(
        "Qdrant resync finished: clusters=%s embedded=%s upserted=%s errors=%s",
        summary.get("clusters"),
        summary.get("embedded"),
        summary.get("upserted"),
        len(summary.get("errors") or []),
    )
    # Don't fail the DAG on partial-batch errors — the summary captures them
    # for observability, and the next scheduled run will retry.
    return summary


with DAG(
    dag_id="qdrant_sync_dag",
    default_args=default_args(),
    description="Rebuild the Qdrant articles collection from Snowflake clusters",
    # 11:05 UTC — runs after trend_dag (10:50) and before b2c_personalization
    # (11:20) so consumer DAGs see a reconciled Qdrant.
    schedule_interval="5 11 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["qdrant", "curateai"],
) as dag:
    PythonOperator(task_id="resync_qdrant", python_callable=resync_qdrant)
