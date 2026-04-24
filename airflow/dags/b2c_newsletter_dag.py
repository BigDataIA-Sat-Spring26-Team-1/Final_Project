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

    Explicit ``user_id`` in conf wins (and bypasses the "already generated"
    guard — ad-hoc triggers always get served). Without it we pull every user
    that has a persona and does NOT yet have a newsletter for today. The API
    is idempotent per (user_id, edition_date), so skipping is the cheap path.
    """
    from datetime import date as _date

    explicit = conf.get("user_id")
    if explicit:
        return [explicit]

    ensure_backend_on_path()
    from app.db.snowflake import get_db_connection

    today = _date.today().isoformat()
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        cur = db.cursor()
        cur.execute(
            """
            SELECT DISTINCT p.user_id
            FROM user_personas p
            WHERE p.user_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM newsletters n
                  WHERE n.user_id = p.user_id
                    AND n.edition_date = %s
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


def resolve_users(**context):
    conf = context.get("dag_run").conf if context.get("dag_run") else {}
    users = _load_target_users(conf or {})
    log.info("Resolved %d newsletter targets", len(users))
    return users


def generate_newsletters(**context):
    ensure_backend_on_path()
    import uuid
    from datetime import date

    from app.db.snowflake import get_db_connection
    from app.services.mailer import render_personalized_html

    ti = context["ti"]
    user_ids: List[str] = ti.xcom_pull(task_ids="resolve_users") or []
    if not user_ids:
        log.warning("No users to process.")
        return {"attempted": 0, "succeeded": 0, "failures": []}

    # Use the same templated renderer as the /newsletter/preview endpoint
    # so the stored archive HTML is visually identical to what the user
    # would see on-demand (and what the send/email path produces). Before
    # this, the DAG used the b2c_agent LLM writer, which emitted raw
    # unstyled HTML — the archive looked nothing like the preview.
    loop = asyncio.new_event_loop()
    db_gen = get_db_connection()
    db = next(db_gen)
    today = date.today().isoformat()

    failures = []
    succeeded = 0
    try:
        cur = db.cursor()
        for uid in user_ids:
            try:
                rendered = loop.run_until_complete(
                    render_personalized_html(uid, today, db)
                )
                if not rendered:
                    raise RuntimeError("Renderer returned no user context.")
                html = (rendered.get("html") or "").strip()
                if not html:
                    raise RuntimeError("Renderer returned empty HTML.")

                path = "mailer.render_personalized_html"
                personal_ct = rendered.get("personal_count", 0)
                common_ct = rendered.get("common_count", 0)

                # Upsert keyed on (user_id, edition_date) so re-runs don't
                # duplicate — one newsletter per user per day.
                cur.execute(
                    """
                    MERGE INTO newsletters t
                    USING (SELECT %s AS user_id, %s AS edition_date) s
                    ON t.user_id = s.user_id AND t.edition_date = s.edition_date
                    WHEN MATCHED THEN UPDATE SET
                        final_content = %s,
                        draft_content = %s,
                        execution_path_taken = %s,
                        status = 'PUBLISHED',
                        generated_at = CURRENT_TIMESTAMP(),
                        updated_at = CURRENT_TIMESTAMP()
                    WHEN NOT MATCHED THEN INSERT
                        (id, user_id, edition_date, final_content, draft_content,
                         execution_path_taken, status, generated_at)
                    VALUES (%s, s.user_id, s.edition_date, %s, %s, %s, 'PUBLISHED',
                            CURRENT_TIMESTAMP())
                    """,
                    (
                        uid,
                        today,
                        html,
                        html,
                        path,
                        str(uuid.uuid4()),
                        html,
                        html,
                        path,
                    ),
                )
                db.commit()
                succeeded += 1
                log.info(
                    "Rendered newsletter user=%s personal=%d common=%d",
                    uid, personal_ct, common_ct,
                )
            except Exception as exc:
                log.error("Newsletter generation failed for user_id=%s: %s", uid, exc)
                failures.append({"user_id": uid, "error": str(exc)[:250]})
    finally:
        loop.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

    log.info(
        "Newsletter fan-out complete: attempted=%d succeeded=%d failed=%d",
        len(user_ids),
        succeeded,
        len(failures),
    )
    return {"attempted": len(user_ids), "succeeded": succeeded, "failures": failures}


with DAG(
    dag_id="b2c_newsletter_dag",
    default_args=default_args(),
    description="Generate the daily B2C newsletter for every eligible user",
    # 11:50 UTC — last step in the daily stagger, runs after qdrant_sync +
    # personalization finish so retrieval sees the reconciled vectors.
    schedule_interval="50 11 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["b2c", "newsletter", "curateai"],
) as dag:
    t_users = PythonOperator(task_id="resolve_users", python_callable=resolve_users)
    t_generate = PythonOperator(task_id="generate_newsletters", python_callable=generate_newsletters)
    t_users >> t_generate
