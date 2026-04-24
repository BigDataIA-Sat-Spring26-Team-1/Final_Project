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
                content = await file.read()
                if len(content) > 5 * 1024 * 1024:
                    return SinglePersonaExtractionResponse(
                        filename=file.filename,
                        is_success=False,
                        error="File size exceeds the 5MB production limit."
                    )
                await file.seek(0)
                
                text, parse_lat = await DocumentParserService.extract_best_text(file)
                
                linkedin_markers = ["linkedin.com/", "Top Skills", "Education"]
                doc_type = "LinkedIn PDF" if any(m.lower() in text.lower() for m in linkedin_markers) else "Resume"
                
                profile = await PersonaLLMService.extract_persona(text, doc_type)
                profile.extraction_latency_seconds += parse_lat
                profile.source_type = doc_type
                
                update_data = UserPersonaUpdate(
                    user_id=user_id,
                    linkedin_url=None, 
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