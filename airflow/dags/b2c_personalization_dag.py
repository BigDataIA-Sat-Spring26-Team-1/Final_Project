from datetime import datetime, timedelta
import asyncio
from airflow import DAG
from airflow.operators.python import PythonOperator

def generate_personalized_recommendations():
    from app.services.search import SearchService
    from app.db.snowflake import get_db_connection
    import logging

    logger = logging.getLogger("airflow.task")
    logger.info("Starting B2C Personalization recommendations task")
    
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        # Example for one user; in practice this might fetch all active B2C users
        # and iterate. For demonstration, we leave as a single user example or 
        # assume an overarching generator wrapper for production.
        # User ID here is mocked for DAG execution demo.
        test_user_id = "test-user-id"
        result = asyncio.run(SearchService.get_personalized_recommendations(test_user_id, 10, db))
        logger.info(f"Recommendations for user {test_user_id}: {result}")
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
    'b2c_personalization_dag',
    default_args=default_args,
    description='Generates personalized recommendations using SearchService',
    schedule_interval='@daily',
    catchup=False,
) as dag:
    
    personalization_task = PythonOperator(
        task_id='personalization_task',
        python_callable=generate_personalized_recommendations
    )
