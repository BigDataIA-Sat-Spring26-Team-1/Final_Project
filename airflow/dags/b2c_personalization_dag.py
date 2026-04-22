"""B2C personalization DAG.

Pre-computes the top-N personalized cluster list per user and caches it
against their daily selection. Runs after trend ranking on the same day so
ranked scores are fresh.

Output: one row per (user_id, cluster_id) in ``daily_selections``. The
newsletter and feed endpoints read from this table instead of hitting the
Qdrant + Snowflake join on every request.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import date
from typing import Any, Dict, List

from airflow import DAG
from airflow.operators.python import PythonOperator

from _common import default_args, ensure_backend_on_path

log = logging.getLogger("airflow.task")


def resolve_users(**context):
    """Pick the users to recompute selections for."""
    conf = context.get("dag_run").conf if context.get("dag_run") else {}
    explicit = (conf or {}).get("user_id")
    if explicit:
        return [explicit]

    ensure_backend_on_path()
    from app.db.snowflake import get_db_connection

    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        cur = db.cursor()
        cur.execute("SELECT DISTINCT user_id FROM user_personas")
        return [row[0] for row in cur.fetchall() if row[0]]
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


def compute_selections(**context):
    ensure_backend_on_path()
    from app.db.snowflake import get_db_connection
    from app.services.search import SearchService

    ti = context["ti"]
    users: List[str] = ti.xcom_pull(task_ids="resolve_users") or []
    if not users:
        log.warning("Personalization has no targets.")
        return {"users_processed": 0}

    per_user_limit = int(os.environ.get("PERSONALIZATION_TOP_N", "10"))

    db_gen = get_db_connection()
    db = next(db_gen)
    loop = asyncio.new_event_loop()

    attempted = 0
    succeeded = 0
    try:
        cur = db.cursor()
        today = date.today().isoformat()

        # Wipe today's cache first so re-runs overwrite cleanly.
        cur.execute(
            "DELETE FROM daily_selections WHERE selected_date = %s AND user_id IN ("
            + ",".join(["%s"] * len(users))
            + ")",
            tuple([today] + users),
        )

        rows: List[tuple] = []
        for uid in users:
            attempted += 1
            try:
                result = loop.run_until_complete(
                    SearchService.get_personalized_recommendations(uid, per_user_limit, db)
                )
                for item in (result or {}).get("results", []):
                    rows.append(
                        (
                            str(uuid.uuid4()),
                            uid,
                            item.get("cluster_id"),
                            "GLOBAL_HIGHLIGHT",
                            float(item.get("score", 0.0)),
                            today,
                        )
                    )
                succeeded += 1
            except Exception as exc:
                log.error("Personalization failed for user_id=%s: %s", uid, exc)

        if rows:
            cur.executemany(
                """
                INSERT INTO daily_selections
                    (id, user_id, cluster_id, selection_type, match_score, selected_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
            db.commit()
    finally:
        loop.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

    log.info(
        "Personalization complete: attempted=%d succeeded=%d rows_written=%d",
        attempted,
        succeeded,
        len(rows) if "rows" in locals() else 0,
    )
    return {
        "users_processed": succeeded,
        "users_attempted": attempted,
    }


with DAG(
    dag_id="b2c_personalization_dag",
    default_args=default_args(),
    description="Pre-compute personalized daily selections per user",
    schedule_interval="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["b2c", "personalization", "curateai"],
) as dag:
    t_users = PythonOperator(task_id="resolve_users", python_callable=resolve_users)
    t_compute = PythonOperator(task_id="compute_selections", python_callable=compute_selections)
    t_users >> t_compute
