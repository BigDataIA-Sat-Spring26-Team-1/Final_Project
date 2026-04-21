from datetime import datetime, timedelta
import asyncio
from airflow import DAG
from airflow.operators.python import PythonOperator

def fetch_and_save_articles():
    import sys
    if "/opt/airflow/backend" not in sys.path:
        sys.path.insert(0, "/opt/airflow/backend")
    from app.services.ingestion import IngestionService
    from app.repository.article import ArticleRepository
    from app.db.snowflake import get_db_connection
    from app.core.cache import INTERNAL_CACHE
    import logging
    logger = logging.getLogger("airflow.task")
    articles = asyncio.run(IngestionService.fetch_all_sources())
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        saved_count = ArticleRepository.upsert_raw_articles(db, articles)
        if saved_count > 0:
            INTERNAL_CACHE.clear()
        logger.info(f"Saved {saved_count} articles.")
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
    "ingestion_dag",
    default_args=default_args,
    description="Fetches multi-source news",
    schedule_interval="@daily",
    catchup=False,
) as dag:
    task = PythonOperator(
        task_id="ingestion_dag_task",
        python_callable=fetch_and_save_articles,
    )