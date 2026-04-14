import json
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from snowflake.connector import SnowflakeConnection

from app.core.limiter import limiter
from app.core.logging_conf import get_logger
from app.core.schemas import (
    ArticleFeedbackRequest,
    ArticleFeedbackResponse,
    BatchPersonaResponse,
)
from app.db.snowflake import get_db_connection
from app.services.persona_service import PersonaService

logger = get_logger("app.api.personas")
router = APIRouter()

# Delta applied to behavioral weights per feedback signal.
# Scaled by each article category's own weight during application.
_FEEDBACK_DELTAS = {
    "like": 0.15,
    "dislike": -0.15,
    "skip": -0.05,
}


@router.post("/extract", response_model=BatchPersonaResponse)
@limiter.limit("5/minute")
async def extract_personas_from_files(
    request: Request,
    user_id: str = Form(..., description="The unique identifier for the user."),
    files: List[UploadFile] = File(...),
    db: SnowflakeConnection = Depends(get_db_connection)
):
    """Extracts structured user personas from uploaded PDFs (resumes, LinkedIn exports).

    Parses each file, uses an LLM to identify professional traits and expertise areas,
    then persists the resulting persona profile to Snowflake for downstream personalization.
    """
    logger.info("Persona extraction requested", user_id=user_id, file_count=len(files))
    return await PersonaService.process_batch(user_id, files, db)


@router.post("/feedback", response_model=ArticleFeedbackResponse)
@limiter.limit("30/minute")
async def record_article_feedback(
    request: Request,
    payload: ArticleFeedbackRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
):
    """Records a user's like/dislike/skip on an article and updates behavioral weights.

    Applies a weighted delta to behavioral_category_weights in Snowflake based on
    the article's category profile and the feedback signal:
      like    → +0.15 × article_category_weight
      dislike → -0.15 × article_category_weight
      skip    → -0.05 × article_category_weight

    After applying the delta the weights are clamped to [0, 1] and any category
    that falls below 0.05 is pruned as noise (P4 spec).
    """
    logger.info(
        "Article feedback received",
        user_id=payload.user_id,
        feedback=payload.feedback,
        categories=list(payload.article_categories.keys()),
    )

    # 1. Fetch existing behavioral weights from Snowflake
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

    raw_behavioral = row[0]
    behavioral_weights: dict = {}
    if raw_behavioral:
        try:
            behavioral_weights = json.loads(raw_behavioral)
        except (json.JSONDecodeError, TypeError):
            behavioral_weights = {}

    # 2. Apply delta proportionally across the article's category weights
    delta = _FEEDBACK_DELTAS[payload.feedback.value]
    for category, article_weight in payload.article_categories.items():
        current = behavioral_weights.get(category, 0.0)
        behavioral_weights[category] = current + delta * article_weight

    # 3. Clamp to [0, 1] and prune noise (< 0.05)
    behavioral_weights = {
        cat: round(max(0.0, min(1.0, weight)), 4)
        for cat, weight in behavioral_weights.items()
        if max(0.0, min(1.0, weight)) >= 0.05
    }

    # 4. Persist updated behavioral weights to Snowflake
    cur.execute(
        """
        UPDATE user_personas
        SET behavioral_category_weights = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
        """,
        (json.dumps(behavioral_weights), payload.user_id),
    )
    db.commit()

    logger.info(
        "Behavioral weights updated",
        user_id=payload.user_id,
        updated_categories=behavioral_weights,
    )

    return ArticleFeedbackResponse(
        user_id=payload.user_id,
        updated_categories=behavioral_weights,
        message=f"Behavioral weights updated based on '{payload.feedback.value}' signal.",
    )