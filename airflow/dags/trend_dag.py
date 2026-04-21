from datetime import datetime, timedelta
import asyncio
from airflow import DAG
from airflow.operators.python import PythonOperator

def rank_daily_clusters_task():
    from app.services.trend import TrendService
    from app.db.snowflake import get_db_connection
    import logging

    logger = logging.getLogger("airflow.task")
    logger.info("Starting Trend DAG task")
    
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        result = asyncio.run(TrendService.rank_daily_clusters(db))
        logger.info(f"Trend processing finished: {result}")
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

default_args = {
    'owner': 'curateai',
    'depends_on_past': False,
    'start_date': datetime(2026, 4, 20),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'trend_dag',
    default_args=default_args,
    description='Analyzes clusters to calculate global trend ranking',
    schedule_interval='@daily',
    catchup=False,
) as dag:
    
    trend_task = PythonOperator(
        task_id='trend_ranking_task',
        python_callable=rank_daily_clusters_task
    )
