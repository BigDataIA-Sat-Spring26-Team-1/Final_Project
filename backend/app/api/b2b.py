from fastapi import APIRouter, HTTPException, Request
from app.core.limiter import limiter
from app.core.logging_conf import get_logger
from app.core.schemas import B2BReportRequest, B2BReportResponse

logger = get_logger("app.api.b2b")
router = APIRouter()


@router.post("/report", response_model=B2BReportResponse)
@limiter.limit("10/minute")
async def generate_b2b_report(
    request: Request,
    payload: B2BReportRequest,
):
    """Triggers the B2B Intelligence Agent to generate an enterprise research report."""
    logger.info("B2B report generation requested", user_id=payload.user_id)

    return B2BReportResponse(
        user_id=payload.user_id,
        report="",
        status="PENDING",
    )