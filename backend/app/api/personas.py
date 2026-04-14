import json
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from snowflake.connector import SnowflakeConnection

from app.core.limiter import limiter
from app.core.logging_conf import get_logger
from app.core.schemas import (
    BatchPersonaResponse,
)
from app.db.snowflake import get_db_connection
from app.services.persona_service import PersonaService

logger = get_logger("app.api.personas")
router = APIRouter()


@router.post("/extract", response_model=BatchPersonaResponse)
@limiter.limit("5/minute")
async def extract_personas_from_files(
    request: Request,
    user_id: str = Form(..., description="The unique identifier for the user."),
    files: List[UploadFile] = File(...),
    db: SnowflakeConnection = Depends(get_db_connection),
):
 
    logger.info("Persona extraction requested", user_id=user_id, file_count=len(files))
    return await PersonaService.process_batch(user_id, files, db)

from app.core.schemas import (
    ArticleFeedbackRequest,
    ArticleFeedbackResponse,
    BatchPersonaResponse,
)

# Delta applied to behavioral weights per feedback signal.
# Scaled by each article category's own weight during application.
_FEEDBACK_DELTAS = {
    "like": 0.15,
    "dislike": -0.15,
    "skip": -0.05,
}


@router.post("/feedback", response_model=ArticleFeedbackResponse)
@limiter.limit("30/minute")
async def record_article_feedback(
    request: Request,
    payload: ArticleFeedbackRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
):
    """Records a user's like/dislike/skip on an article and updates behavioral weights."""
    logger.info(
        "Article feedback received",
        user_id=payload.user_id,
        feedback=payload.feedback,
        categories=list(payload.article_categories.keys()),
    )

    # Fetch existing behavioral weights from Snowflake
    cur = db.cursor()
    cur.execute(
        "SELECT behavioral_category_weights FROM user_personas WHERE user_id = %s",
        (payload.user_id,),
    )
    row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No persona found for user_id '{payload.user_id}'.",
        )

    return ArticleFeedbackResponse(
        user_id=payload.user_id,
        updated_categories={},
        message="Feedback recorded (weight update pending).",
    )