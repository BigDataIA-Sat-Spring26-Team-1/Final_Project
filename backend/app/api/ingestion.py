from fastapi import APIRouter, HTTPException, Request
from app.core.airflow_client import AirflowUnavailable, trigger_dag
from app.core.limiter import limiter
from app.core.logging_conf import get_logger
from app.core.schemas import DAGTriggerResponse

logger = get_logger("app.api.ingestion")
router = APIRouter()

@router.post("/fetch-rss", status_code=202, response_model=DAGTriggerResponse)
@limiter.limit("2/minute")
async def trigger_rss_ingestion(request: Request) -> DAGTriggerResponse:
    logger.info("RSS ingestion DAG trigger requested")

    try:
        run = await trigger_dag("ingestion_dag")
    except AirflowUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return DAGTriggerResponse(
        status="ACCEPTED",
        message="Ingestion DAG scheduled.",
        dag_id="ingestion_dag",
        dag_run_id=run.get("dag_run_id", ""),
        state=run.get("state"),
    )
