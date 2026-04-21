from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

def generate_b2b_seo_report():
    import sys
    if "/opt/airflow/backend" not in sys.path:
        sys.path.insert(0, "/opt/airflow/backend")
    from app.services.b2b_agent import get_b2b_report_graph
    import logging
    logger = logging.getLogger("airflow.task")
    logger.info("Starting B2B SEO Report generation")
    graph = get_b2b_report_graph()
    logger.info("LangGraph initialized successfully.")

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
    "b2b_seo_dag",
    default_args=default_args,
    description="Generates B2B SEO Opportunity Reports",
    schedule_interval="@daily",
    catchup=False,
) as dag:
    task = PythonOperator(
        task_id="b2b_seo_task",
        python_callable=generate_b2b_seo_report,
    )