from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

def generate_personalization():
    import logging
    logger = logging.getLogger("airflow.task")
    logger.info("Generating personalized caches...")

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
    "b2c_personalization_dag",
    default_args=default_args,
    description="Pre-computes recommendations",
    schedule_interval="@daily",
    catchup=False,
) as dag:
    task = PythonOperator(
        task_id="b2c_personalization_dag_task",
        python_callable=generate_personalization,
    )