"""B2C newsletter generation DAG.

Two ways to trigger:

1. Scheduled (``@daily``): the DAG fans out over every user that has a
   persona on file and produces one newsletter per user.
2. Ad-hoc via ``dag_run.conf``: pass ``{"user_id": "<uuid>"}`` and only that
   user gets a newsletter. The backend uses this for on-demand generation.

Failures for one user do not fail the whole DAG — we collect per-user status
and log a summary so the scheduler can move on.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from airflow import DAG
from airflow.operators.python import PythonOperator

from _common import default_args, ensure_backend_on_path

log = logging.getLogger("airflow.task")


def _load_target_users(conf: Dict[str, Any]) -> List[str]:
    """Resolve the list of user ids to generate newsletters for.

    Explicit ``user_id`` in conf wins. Without it we pull every user that has
    a persona — no persona, no newsletter.
    """
    explicit = conf.get("user_id")
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


def resolve_users(**context):
    conf = context.get("dag_run").conf if context.get("dag_run") else {}
    users = _load_target_users(conf or {})
    log.info("Resolved %d newsletter targets", len(users))
    return users


def generate_newsletters(**context):
    ensure_backend_on_path()
    from app.services.b2c_agent import get_b2c_newsletter_graph

    ti = context["ti"]
    user_ids: List[str] = ti.xcom_pull(task_ids="resolve_users") or []
    if not user_ids:
        log.warning("No users to process.")
        return {"attempted": 0, "succeeded": 0, "failures": []}

    graph = get_b2c_newsletter_graph()
    loop = asyncio.new_event_loop()

    failures = []
    succeeded = 0
    try:
        for uid in user_ids:
            try:
                # The graph is LangGraph-based and async under the hood —
                # ``ainvoke`` if available, otherwise drop back to a sync call.
                if hasattr(graph, "ainvoke"):
                    loop.run_until_complete(
                        graph.ainvoke({"user_id": uid, "execution_mode": "polished"})
                    )
                else:
                    graph.invoke({"user_id": uid, "execution_mode": "polished"})
                succeeded += 1
            except Exception as exc:
                log.error("Newsletter generation failed", user_id=uid, error=str(exc))
                failures.append({"user_id": uid, "error": str(exc)[:250]})
    finally:
        loop.close()

    log.info(
        "Newsletter fan-out complete",
        attempted=len(user_ids),
        succeeded=succeeded,
        failed=len(failures),
    )
    return {"attempted": len(user_ids), "succeeded": succeeded, "failures": failures}


with DAG(
    dag_id="b2c_newsletter_dag",
    default_args=default_args(),
    description="Generate the daily B2C newsletter for every eligible user",
    schedule_interval="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["b2c", "newsletter", "curateai"],
) as dag:
    t_users = PythonOperator(task_id="resolve_users", python_callable=resolve_users)
    t_generate = PythonOperator(task_id="generate_newsletters", python_callable=generate_newsletters)
    t_users >> t_generate
