from fastapi import APIRouter, HTTPException, Request

from app.core.limiter import limiter
from app.core.logging_conf import get_logger
from app.core.schemas import B2BReportRequest, B2BReportResponse
from app.services.b2b_agent import get_b2b_report_graph

logger = get_logger("app.api.b2b")
router = APIRouter()


@router.post("/report", response_model=B2BReportResponse)
@limiter.limit("10/minute")
async def generate_b2b_report(
    request: Request,
    payload: B2BReportRequest,
):

    logger.info("B2B report generation requested", user_id=payload.user_id)

    graph = get_b2b_report_graph()

    initial_state = {
        "user_id": payload.user_id,
        "user_persona": {},
        "search_query": "",
        "retrieved_articles": [],
        "messages": [],
        "next_step": "",
        "generated_content": "",
        "status": "PENDING",
        "metadata": {},
    }

    try:
        result = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("B2B report generation failed", user_id=payload.user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Report generation failed.")

    final_status = result.get("status", "UNKNOWN")
    if final_status not in ("SUCCESS", "EMPTY_RESULT"):
        raise HTTPException(
            status_code=500,
            detail=f"Agent completed with unexpected status: {final_status}",
        )

    return B2BReportResponse(
        user_id=payload.user_id,
        report=result.get("generated_content", ""),
        status=final_status,
    )