from datetime import datetime, timedelta
import asyncio
from airflow import DAG
from airflow.operators.python import PythonOperator

def run_deduplication_pipeline():
    from app.services.deduplication import DeduplicationService
    from app.repository.article import ArticleRepository
    from app.db.snowflake import get_db_connection
    import logging

    logger = logging.getLogger("airflow.task")
    logger.info("Starting Deduplication DAG task")
    
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        raw_articles = ArticleRepository.get_unclustered_articles(db, limit=1000)
        if not raw_articles:
            logger.info("No unclustered articles found for deduplication task.")
            return
            
        raw_clusters = asyncio.run(DeduplicationService.process_batch(raw_articles))
        stories = [DeduplicationService.synthesize_story(c) for c in raw_clusters]
        
        cluster_ids = ArticleRepository.create_clusters_batch(db, stories)
        
        linkage_data = [
            {"cluster_id": cluster_ids[i], "article_ids": story["article_ids"]}
            for i, story in enumerate(stories)
        ]
        ArticleRepository.link_articles_to_clusters_bulk(db, linkage_data)
        logger.info(f"Deduplication complete, {len(cluster_ids)} clusters created.")
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
    'deduplication_dag',
    default_args=default_args,
    description='Runs the semantic deduplication pipeline',
    schedule_interval='@hourly',
    catchup=False,
) as dag:
    
    dedup_task = PythonOperator(
        task_id='deduplication_task',
        python_callable=run_deduplication_pipeline
    )
