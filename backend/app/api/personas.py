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