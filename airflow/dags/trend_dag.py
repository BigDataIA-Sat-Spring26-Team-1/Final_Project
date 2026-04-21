"""Daily cluster ranking DAG.

Bulk re-scores every cluster, writes back trend_status / final_trend_score.
Runs after the deduplication DAG on the same day — schedule is decoupled
though, so an operator can trigger it manually after back-filling data.
"""
from __future__ import annotations

import asyncio
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator

from _common import default_args, ensure_backend_on_path

log = logging.getLogger("airflow.task")


def rank_clusters(**context):
    ensure_backend_on_path()
    from app.db.snowflake import get_db_connection
    from app.services.trend import TrendService

    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(TrendService.rank_daily_clusters(db))
        finally:
            loop.close()
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    log.info("Trend ranking finished", **result)
    return result


with DAG(
    dag_id="trend_dag",
    default_args=default_args(),
    description="Re-rank all clusters by density + social signals",
    schedule_interval="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["trend", "curateai"],
) as dag:
    PythonOperator(task_id="rank_clusters", python_callable=rank_clusters)
