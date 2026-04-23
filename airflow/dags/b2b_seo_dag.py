"""B2B SEO intelligence DAG.

Fans out one brief per corporate tenant. Like the newsletter DAG, one target
company can be specified via ``dag_run.conf = {"company_id": "..."}`` for
on-demand generation.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date
from typing import Any, Dict, List

from airflow import DAG
from airflow.operators.python import PythonOperator

from _common import default_args, ensure_backend_on_path

log = logging.getLogger("airflow.task")


def resolve_companies(**context):
    """Pick companies that still need a brief for today.

    Explicit ``company_id`` in conf always wins. Otherwise we skip any company
    that already has a brief dated today — the API-triggered path (or an
    earlier DAG run) has already generated it and we don't want duplicates.
    """
    conf = context.get("dag_run").conf if context.get("dag_run") else {}
    explicit = (conf or {}).get("company_id")
    if explicit:
        return [explicit]

    ensure_backend_on_path()
    from app.db.snowflake import get_db_connection

    today = date.today().isoformat()
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        cur = db.cursor()
        cur.execute(
            """
            SELECT c.id FROM companies c
            WHERE NOT EXISTS (
                SELECT 1 FROM content_briefs b
                WHERE b.company_id = c.id AND b.brief_date = %s
            )
            """,
            (today,),
        )
        return [row[0] for row in cur.fetchall() if row[0]]
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


def generate_briefs(**context):
    ensure_backend_on_path()
    from app.db.snowflake import get_db_connection
    from app.services.b2b_agent import get_b2b_report_graph

    ti = context["ti"]
    companies: List[str] = ti.xcom_pull(task_ids="resolve_companies") or []
    if not companies:
        log.warning("No companies to brief.")
        return {"attempted": 0, "succeeded": 0}

    graph = get_b2b_report_graph()
    loop = asyncio.new_event_loop()

    db_gen = get_db_connection()
    db = next(db_gen)
    succeeded = 0
    failures: List[Dict[str, str]] = []
    try:
        cur = db.cursor()
        for cid in companies:
            try:
                # The B2B graph takes a ``user_id`` that actually carries the
                # corporate client identifier — the name is a legacy artifact.
                if hasattr(graph, "ainvoke"):
                    state = loop.run_until_complete(graph.ainvoke({"user_id": cid}))
                else:
                    state = graph.invoke({"user_id": cid})

                # The B2B graph stores its output under ``generated_content`` —
                # same convention as the B2C agent — not ``final_report``.
                brief_md = (state or {}).get("generated_content") or ""
                if not brief_md.strip():
                    raise RuntimeError("Agent returned empty brief.")

                cur.execute(
                    """
                    INSERT INTO content_briefs
                        (id, company_id, brief_date, brief_content, urgency_tier, status, generated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
                    """,
                    (
                        str(uuid.uuid4()),
                        cid,
                        date.today().isoformat(),
                        brief_md,
                        (state or {}).get("urgency_tier", "MONITOR"),
                        "GENERATED",
                    ),
                )
                db.commit()
                succeeded += 1
            except Exception as exc:
                log.error("Brief generation failed for company_id=%s: %s", cid, exc)
                failures.append({"company_id": cid, "error": str(exc)[:250]})
    finally:
        loop.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

    log.info(
        "B2B brief fan-out complete: attempted=%d succeeded=%d failed=%d",
        len(companies),
        succeeded,
        len(failures),
    )
    return {"attempted": len(companies), "succeeded": succeeded, "failures": failures}


with DAG(
    dag_id="b2b_seo_dag",
    default_args=default_args(),
    description="Generate per-company B2B intelligence briefs (manual trigger only)",
    # Briefs run on-demand from the frontend / backend; there is no daily
    # cadence. Setting schedule_interval=None keeps the DAG available in the
    # Airflow UI for manual triggers without scheduling it automatically.
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=["b2b", "seo", "curateai"],
) as dag:
    t_resolve = PythonOperator(task_id="resolve_companies", python_callable=resolve_companies)
    t_generate = PythonOperator(task_id="generate_briefs", python_callable=generate_briefs)
    t_resolve >> t_generate
