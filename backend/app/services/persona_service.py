import time
import asyncio
from typing import List
from fastapi import UploadFile
from snowflake.connector import SnowflakeConnection

from app.core.schemas import (
    PersonaExtractionResult, 
    SinglePersonaExtractionResponse, 
    BatchPersonaResponse,
    UserPersonaUpdate
)
from app.services.parser import DocumentParserService
from app.services.llm import PersonaLLMService
from app.repository.persona import PersonaRepository
from app.core.logging_conf import get_logger

logger = get_logger("app.services.persona_orchestrator")

class PersonaService:
    """
    Orchestration layer managing the end-to-end flow:
    PDF Extraction -> LLM Analysis -> Snowflake Persistence.
    """

    @classmethod
    async def process_batch(
        cls, 
        user_id: str, 
        files: List[UploadFile], 
        db: SnowflakeConnection
    ) -> BatchPersonaResponse:
        start_time = time.time()
        
        async def process_single(file: UploadFile) -> SinglePersonaExtractionResponse:
            try:
                # 1. Size Validation (Industry Standard 5MB limit)
                content = await file.read()
                if len(content) > 5 * 1024 * 1024:
                    return SinglePersonaExtractionResponse(
                        filename=file.filename,
                        is_success=False,
                        error="File size exceeds the 5MB production limit."
                    )
                await file.seek(0)
                
                # 2. Extract & Analyze
                text, parse_lat = await DocumentParserService.extract_best_text(file)
                
                # Heuristic source detection
                linkedin_markers = ["linkedin.com/", "Top Skills", "Education"]
                doc_type = "LinkedIn PDF" if any(m.lower() in text.lower() for m in linkedin_markers) else "Resume"
                
                profile = await PersonaLLMService.extract_persona(text, doc_type)
                profile.extraction_latency_seconds += parse_lat
                profile.source_type = doc_type
                
                # 3. Synchronous Push to Snowflake (At the end of successful extraction)
                # We convert CategoryWeights model to raw dict for the repo
                update_data = UserPersonaUpdate(
                    user_id=user_id,
                    linkedin_url=None, # Only if we had a field for it, currently extracted name/title
                    job_title=profile.job_title,
                    seniority=profile.seniority,
                    persona_archetype=profile.persona_archetype,
                    bio_summary=profile.bio_summary,
                    explicit_category_weights=profile.category_weights.model_dump()
                )
                
                PersonaRepository.upsert_persona(db, update_data)
                
                return SinglePersonaExtractionResponse(
                    filename=file.filename,
                    is_success=True,
                    data=profile
                )
                
            except Exception as e:
                logger.error("Batch processing individual failure", filename=file.filename, error=str(e))
                return SinglePersonaExtractionResponse(
                    filename=file.filename,
                    is_success=False,
                    error=str(e)
                )

        results = await asyncio.gather(*(process_single(f) for f in files))
        
        return BatchPersonaResponse(
            user_id=user_id,
            results=results,
            overall_latency_seconds=time.time() - start_time
        )
