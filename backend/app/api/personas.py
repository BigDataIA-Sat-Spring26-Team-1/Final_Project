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
    UserPersonaUpdate,
)
from app.db.snowflake import get_db_connection
from app.repository.persona import PersonaRepository
from app.services.persona_service import PersonaService
from pydantic import BaseModel, Field
from typing import Dict

class ManualPersonaRequest(BaseModel):
    user_id: str
    job_title: str = Field(..., min_length=1)
    seniority: str = Field(..., min_length=1)
    bio_summary: str = ""
    persona_archetype: str = "GENERAL_TECH_ENVELOPE"
    linkedin_url: str | None = None
    explicit_category_weights: Dict[str, float] = Field(default_factory=dict)

logger = get_logger("app.api.personas")
router = APIRouter()
_FEEDBACK_DELTAS = {
    "like": 0.15,
    "dislike": -0.15,
    "skip": -0.05,
}

@router.post("/manual", status_code=201)
async def create_manual_persona(
    payload: ManualPersonaRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
):

    cleaned = {
        cat: round(max(0.0, min(1.0, float(w))), 4)
        for cat, w in (payload.explicit_category_weights or {}).items()
        if float(w) >= 0.05
    }
    update = UserPersonaUpdate(
        user_id=payload.user_id,
        linkedin_url=payload.linkedin_url,
        job_title=payload.job_title,
        seniority=payload.seniority,
        persona_archetype=payload.persona_archetype,
        bio_summary=payload.bio_summary,
        explicit_category_weights=cleaned,
    )
    persona_id = PersonaRepository.upsert_persona(db, update)
    logger.info("Manual persona created", user_id=payload.user_id, categories=list(cleaned.keys()))
    return {"user_id": payload.user_id, "persona_id": persona_id, "status": "created"}

@router.post("/extract", response_model=BatchPersonaResponse)
@limiter.limit("5/minute")
async def extract_personas_from_files(
    request: Request,
    user_id: str = Form(..., description="The unique identifier for the user."),
    files: List[UploadFile] = File(...),
    db: SnowflakeConnection = Depends(get_db_connection)
):

    logger.info("Persona extraction requested", user_id=user_id, file_count=len(files))
    return await PersonaService.process_batch(user_id, files, db)

@router.post("/feedback", response_model=ArticleFeedbackResponse)
@limiter.limit("30/minute")
async def record_article_feedback(
    request: Request,
    payload: ArticleFeedbackRequest,
    db: SnowflakeConnection = Depends(get_db_connection),
):

    logger.info(
        "Article feedback received",
        user_id=payload.user_id,
        feedback=payload.feedback,
        categories=list(payload.article_categories.keys()),
    )

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

    delta = _FEEDBACK_DELTAS[payload.feedback.value]
    for category, article_weight in payload.article_categories.items():
        current = behavioral_weights.get(category, 0.0)
        behavioral_weights[category] = current + delta * article_weight

    behavioral_weights = {
        cat: round(max(0.0, min(1.0, weight)), 4)
        for cat, weight in behavioral_weights.items()
        if max(0.0, min(1.0, weight)) >= 0.05
    }

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

@router.get("/{user_id}")
async def get_user_persona(
    user_id: str,
    db: SnowflakeConnection = Depends(get_db_connection),
):

    persona = PersonaRepository.get_persona(db, user_id)
    if not persona:
        raise HTTPException(
            status_code=404,
            detail=f"No persona found for user_id '{user_id}'.",
        )
    return {"user_id": user_id, **persona}