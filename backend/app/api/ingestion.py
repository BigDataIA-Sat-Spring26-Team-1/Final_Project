import time

from snowflake.connector import SnowflakeConnection
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.limiter import limiter
from app.core.logging_conf import get_logger
from app.core.schemas import IngestionBatchResponse
from app.db.snowflake import get_db_connection
from app.services.ingestion import IngestionService
from app.repository.article import ArticleRepository
from app.core.cache import INTERNAL_CACHE

logger = get_logger("app.api.ingestion")
router = APIRouter()


@router.post("/fetch-rss", status_code=202)
@limiter.limit("2/minute")
async def trigger_rss_ingestion(request: Request):
    """Triggers the Airflow DAG for ingestion via its REST API."""
    logger.info("Manual RSS ingestion triggered via API")

    import httpx
    try:
        # Defaults to airflow docker service if run inside composed network, 
        # or localhost for local testing. We assume airflow is running.
        airflow_url = "http://localhost:8080/api/v1/dags/ingestion_dag/dagRuns"
        async with httpx.AsyncClient() as client:
            # We mock auth here assuming default admin:admin setup in dev.
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
            "message": "Ingestion DAG triggered successfully",
            "run_id": run_id
        }

    except Exception as e:
        logger.error("Ingestion endpoint failure", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger Airflow DAG: {str(e)}")
