from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

def generate_b2c_newsletter():
    from app.services.b2c_agent import get_b2c_newsletter_graph
    import logging

    logger = logging.getLogger("airflow.task")
    logger.info("Starting B2C Newsletter generation DAG")
    
    graph = get_b2c_newsletter_graph()
    logger.info(f"LangGraph initialized: {graph.name}")
    # Integration logic to invoke over users would go here

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
    'b2c_newsletter_dag',
    default_args=default_args,
    description='Generates personalized B2C Newsletters',
    schedule_interval='@daily',
    catchup=False,
) as dag:
    
    newsletter_task = PythonOperator(
        task_id='b2c_newsletter_task',
        python_callable=generate_b2c_newsletter
    )
