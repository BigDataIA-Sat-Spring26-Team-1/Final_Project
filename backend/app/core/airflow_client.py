from __future__ import annotations
import time
from typing import Any, Dict, Optional
import httpx
from app.core.config import get_settings
from app.core.logging_conf import get_logger
from app.core.metrics import DAG_TRIGGER_LATENCY, DAG_TRIGGERS_TOTAL

logger = get_logger("app.core.airflow_client")

class AirflowUnavailable(RuntimeError):
    """Raised when AIRFLOW_HOST is missing or the scheduler is unreachable.

    The API layer catches this and turns it into a 503 — we don't want a
    Snowflake outage on the VM to look like a 500 from the backend.
    """

def _require_host() -> str:
    host = get_settings().airflow_host.rstrip("/")
    if not host:
        raise AirflowUnavailable(
            "AIRFLOW_HOST is not configured — the orchestrator is disabled."
        )
    return host

async def trigger_dag(
    dag_id: str,
    conf: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    settings = get_settings()
    host = _require_host()
    url = f"{host}/api/v1/dags/{dag_id}/dagRuns"

    payload: Dict[str, Any] = {}
    if conf:
        payload["conf"] = conf

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.airflow_request_timeout_seconds) as client:
            resp = await client.post(
                url,
                json=payload,
                auth=(settings.airflow_username, settings.airflow_password),
            )
    except httpx.HTTPError as exc:
        DAG_TRIGGERS_TOTAL.labels(dag_id=dag_id, status="rejected").inc()
        logger.error("Airflow trigger failed at transport layer", dag_id=dag_id, error=str(exc))
        raise AirflowUnavailable(f"Airflow unreachable: {exc}") from exc
    finally:
        DAG_TRIGGER_LATENCY.labels(dag_id=dag_id).observe(time.perf_counter() - start)

    if resp.status_code >= 400:
        DAG_TRIGGERS_TOTAL.labels(dag_id=dag_id, status="rejected").inc()
        logger.error(
            "Airflow rejected DAG trigger",
            dag_id=dag_id,
            status=resp.status_code,
            body=resp.text[:500],
        )
        raise AirflowUnavailable(
            f"Airflow returned {resp.status_code}: {resp.text[:200]}"
        )

    DAG_TRIGGERS_TOTAL.labels(dag_id=dag_id, status="accepted").inc()
    data = resp.json()
    logger.info(
        "Airflow DAG triggered",
        dag_id=dag_id,
        dag_run_id=data.get("dag_run_id"),
        state=data.get("state"),
    )
    return data

async def get_dag_run_status(dag_id: str, dag_run_id: str) -> Dict[str, Any]:
    settings = get_settings()
    host = _require_host()
    url = f"{host}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"

    try:
        async with httpx.AsyncClient(timeout=settings.airflow_request_timeout_seconds) as client:
            resp = await client.get(
                url,
                auth=(settings.airflow_username, settings.airflow_password),
            )
    except httpx.HTTPError as exc:
        raise AirflowUnavailable(f"Airflow unreachable: {exc}") from exc

    if resp.status_code == 404:
        raise AirflowUnavailable(f"Unknown dag_run_id '{dag_run_id}' for dag '{dag_id}'.")
    if resp.status_code >= 400:
        raise AirflowUnavailable(
            f"Airflow returned {resp.status_code}: {resp.text[:200]}"
        )
    return resp.json()