from datetime import datetime, timedelta
import asyncio
from airflow import DAG
from airflow.operators.python import PythonOperator

def run_deduplication_pipeline():
    import sys
    if "/opt/airflow/backend" not in sys.path:
        sys.path.insert(0, "/opt/airflow/backend")
    from app.services.deduplication import DeduplicationService
    from app.db.snowflake import get_db_connection
    import logging
    logger = logging.getLogger("airflow.task")
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        results = asyncio.run(DeduplicationService.process_batch(db))
        logger.info(f"Deduplication complete: {results}")
    finally:
        try: next(db_gen)
        except StopIteration: pass

default_args = {
    "owner": "curateai",
    "depends_on_past": False,
    "start_date": datetime(2026, 4, 20),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "deduplication_dag",
    default_args=default_args,
    description="Clusters articles",
    schedule_interval="@hourly",
    catchup=False,
) as dag:
    task = PythonOperator(
        task_id="deduplication_dag_task",
        python_callable=run_deduplication_pipeline,
    )