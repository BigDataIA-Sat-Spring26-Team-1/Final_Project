"""Weekly behavioral refinement DAG (P4 rollup).

Per-event feedback (like / dislike / skip) is applied immediately via the
FastAPI /personas/feedback endpoint. This DAG handles the weekly aggregate:

1. Read the last-7-day feedback events from ``user_article_feedback``.
2. Blend them into ``user_personas.behavioral_category_weights`` with a
   decay factor so stale signals lose influence over time.
3. Clamp to [0, 1] and prune anything below the 0.05 noise floor.

If the feedback event table doesn't exist yet the DAG logs a warning and
exits cleanly — that's expected on fresh deployments.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict

from airflow import DAG
from airflow.operators.python import PythonOperator

from _common import default_args, ensure_backend_on_path

log = logging.getLogger("airflow.task")

# How much of the historical weight survives each weekly pass. 0.7 means
# last week's signal degrades to ~1% after a month without reinforcement.
DECAY_FACTOR = float(os.environ.get("BEHAVIORAL_DECAY_FACTOR", "0.7"))
NOISE_FLOOR = float(os.environ.get("BEHAVIORAL_NOISE_FLOOR", "0.05"))


def _table_exists(db, table: str) -> bool:
    cur = db.cursor()
    cur.execute(
        """
        SELECT 1 FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
          AND UPPER(TABLE_NAME) = UPPER(%s)
        """,
        (table,),
    )
    return cur.fetchone() is not None


def refine_weights(**context):
    ensure_backend_on_path()
    from app.db.snowflake import get_db_connection

    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        cur = db.cursor()

        if not _table_exists(db, "user_article_feedback"):
            log.warning("user_article_feedback table missing — nothing to roll up.")
            return {"users_touched": 0}

        # Aggregate last 7 days of feedback: net weight per (user, category).
        # Positive signals pull the weight up, negatives pull it down; the
        # FastAPI endpoint has already done the scaling, so we just sum here.
        cur.execute(
            """
            SELECT user_id, category, SUM(weight_delta) AS net_delta
            FROM user_article_feedback
            WHERE created_at >= DATEADD(day, -7, CURRENT_TIMESTAMP())
            GROUP BY user_id, category
            """
        )
        events_by_user: Dict[str, Dict[str, float]] = {}
        for user_id, category, net_delta in cur.fetchall():
            events_by_user.setdefault(user_id, {})[category] = float(net_delta or 0.0)

        if not events_by_user:
            log.info("No feedback events in the last 7 days.")
            return {"users_touched": 0}

        touched = 0
        for user_id, deltas in events_by_user.items():
            cur.execute(
                "SELECT behavioral_category_weights FROM user_personas WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                continue

            current: Dict[str, float] = {}
            if row[0]:
                try:
                    current = json.loads(row[0])
                except (json.JSONDecodeError, TypeError):
                    current = {}

            merged: Dict[str, float] = {}
            for cat, weight in current.items():
                merged[cat] = weight * DECAY_FACTOR
            for cat, delta in deltas.items():
                merged[cat] = merged.get(cat, 0.0) + delta

            cleaned = {
                cat: round(max(0.0, min(1.0, w)), 4)
                for cat, w in merged.items()
                if max(0.0, min(1.0, w)) >= NOISE_FLOOR
            }

            cur.execute(
                """
                UPDATE user_personas
                SET behavioral_category_weights = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """,
                (json.dumps(cleaned), user_id),
            )
            touched += 1

        db.commit()
        log.info("Behavioral rollup complete", users_touched=touched)
        return {"users_touched": touched}
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


with DAG(
    dag_id="behavioral_refinement_dag",
    default_args=default_args(),
    description="Weekly P4 rollup of user feedback into behavioral weights",
    schedule_interval="@weekly",
    catchup=False,
    max_active_runs=1,
    tags=["personalization", "curateai"],
) as dag:
    PythonOperator(task_id="refine_weights", python_callable=refine_weights)
