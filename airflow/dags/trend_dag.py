from datetime import datetime, timedelta
import asyncio
from airflow import DAG
from airflow.operators.python import PythonOperator

def rank_daily_clusters_task():
    import sys
    if "/opt/airflow/backend" not in sys.path:
        sys.path.insert(0, "/opt/airflow/backend")
    from app.services.trend import TrendService
    from app.db.snowflake import get_db_connection
    import logging
    logger = logging.getLogger("airflow.task")
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        results = asyncio.run(TrendService.rank_daily_clusters(db))
        logger.info(f"Trend ranking complete: {results}")
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
    "trend_dag",
    default_args=default_args,
    description="Ranks clusters daily",
    schedule_interval="@daily",
    catchup=False,
) as dag:
    task = PythonOperator(
        task_id="trend_dag_task",
        python_callable=rank_daily_clusters_task,
    )