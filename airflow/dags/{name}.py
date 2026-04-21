from datetime import datetime, timedelta
import asyncio
from airflow import DAG
from airflow.operators.python import PythonOperator

def bootstrap_backend():
    import sys
    import subprocess
    import os
    if "/opt/airflow/backend" not in sys.path:
        sys.path.insert(0, "/opt/airflow/backend")
    
    marker = "/tmp/curateai_synced_v3"
    if not os.path.exists(marker):
        print("Syncing pinned dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "/opt/airflow/backend"])
        with open(marker, "w") as f:
            f.write("done")

def weekly_behavioral_rollup():
    bootstrap_backend()
    import logging
    logger = logging.getLogger("airflow.task")
    logger.info("Performing behavioral rollup...")

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
    "behavioral_refinement_dag",
    default_args=default_args,
    description="Weekly rollup of user feedback",
    schedule_interval="@weekly",
    catchup=False,
) as dag:
    
    task = PythonOperator(
        task_id="behavioral_refinement_dag_task",
        python_callable=weekly_behavioral_rollup
    )
