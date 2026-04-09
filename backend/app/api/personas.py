from typing import List
from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from snowflake.connector import SnowflakeConnection

from app.main import limiter
from app.core.logging_conf import get_logger
from app.core.schemas import BatchPersonaResponse
from app.services.persona_service import PersonaService
from app.db.snowflake import get_db_connection

logger = get_logger("app.api.personas")
router = APIRouter()

@router.post("/extract", response_model=BatchPersonaResponse)
@limiter.limit("5/minute")
async def extract_personas_from_files(
    request: Request,
    user_id: str = Form(..., description="The unique identifier for the user."),
    files: List[UploadFile] = File(...),
    db: SnowflakeConnection = Depends(get_db_connection)
):
    """
    Extrapolates structured user personas derived from a generic raw PDF list (Resumes/LinkedIn Exports)
    and persists the results into the Snowflake identity store.
    """
    logger.info("Batch persona extraction request initiated", user_id=user_id, file_count=len(files))
    
    # Delegate orchestration to the service layer
    return await PersonaService.process_batch(user_id, files, db)
