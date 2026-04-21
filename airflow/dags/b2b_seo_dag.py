from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

def generate_b2b_seo_report():
    from app.services.b2b_agent import get_b2b_report_graph
    import logging

    logger = logging.getLogger("airflow.task")
    logger.info("Starting B2B SEO Report generation DAG")
    
    graph = get_b2b_report_graph()
    logger.info(f"LangGraph initialized: {graph.name}")
    # Integration logic to run over companies would go here

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
    'b2b_seo_dag',
    default_args=default_args,
    description='Generates B2B SEO Opportunity Reports',
    schedule_interval='@daily',
    catchup=False,
) as dag:
    
    seo_report_task = PythonOperator(
        task_id='b2b_seo_task',
        python_callable=generate_b2b_seo_report
    )
