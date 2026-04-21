from app.core.logging_conf import get_logger
from app.db.snowflake import get_db_connection
from app.repository.article import ArticleRepository
from app.services.deduplication import DeduplicationService

from snowflake.connector import SnowflakeConnection
from fastapi import APIRouter, Depends, HTTPException

logger = get_logger("app.api.deduplication")
router = APIRouter()


@router.post("/process", status_code=202)
async def run_deduplication():
    """Runs the semantic deduplication DAG via Airflow."""
    logger.info("Deduplication DAG triggered via API")

    import httpx
    try:
        airflow_url = "http://localhost:8080/api/v1/dags/deduplication_dag/dagRuns"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                airflow_url, 
                json={}, 
                auth=("admin", "admin")
            )
            resp.raise_for_status()
            data = resp.json()
            run_id = data.get("dag_run_id", "unknown_run_id")

        return {
            "status": "ACCEPTED",
            "message": "Deduplication DAG triggered successfully",
            "run_id": run_id
        }

    except Exception as e:
        logger.error("Deduplication failed to trigger", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger Airflow DAG: {str(e)}")
