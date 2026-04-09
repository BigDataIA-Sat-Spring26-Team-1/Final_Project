import time
import asyncio
from typing import List

from app.main import limiter
from app.core.logging_conf import get_logger
from app.services.llm import PersonaLLMService
from app.core.schemas import PersonaExtractionResult
from app.services.parser import DocumentParserService

from fastapi import APIRouter, UploadFile, File, HTTPException, Request


logger = get_logger("app.api.personas")
router = APIRouter()

@router.post("/extract", response_model=List[PersonaExtractionResult])
@limiter.limit("5/minute")
async def extract_personas_from_files(request: Request, files: List[UploadFile] = File(...)):
    """
    Extrapolates structured user personas derived from a generic raw PDF list (Resumes/LinkedIn Exports).
    Runs strict parallel executions spanning parser engines and LLM calls allowing N files instantaneously.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    async def process_single_file(file: UploadFile) -> PersonaExtractionResult:
        try:
            logger.info("Processing generic persona document", filename=file.filename)
            
            # 1. Benchmark and Extract (Safely decoupled from disk via pure memory bounds)
            extracted_text, parse_latency = await DocumentParserService.extract_best_text(file)
            
            # 2. Heuristically define nature of standard file type
            linkedin_markers = ["linkedin.com/", "Experience", "Top Skills", "About", "Education"]
            score = sum(1 for m in linkedin_markers if m.lower() in extracted_text.lower())
            doc_type = "LinkedIn PDF" if score >= 3 else "Resume"
            
            # 3. Asynchronously offload intelligence extraction against explicitly strict taxonomy mappings via LiteLLM
            start_llm = time.time()
            profile = await PersonaLLMService.extract_persona(extracted_text, doc_type)
            llm_latency = time.time() - start_llm
            
            # 4. Synthesize diagnostic data for scaling monitoring
            profile.source_type = doc_type
            profile.extraction_latency_seconds = parse_latency + llm_latency
            
            logger.info("Successfully extracted structured persona pipeline", 
                        filename=file.filename, 
                        latency_metrics=profile.extraction_latency_seconds)
            
            return profile
            
        except Exception as e:
            logger.error("Failed to process document layout pipeline", filename=file.filename, error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to cleanly process {file.filename}: {str(e)}")

    # Execute across the entire list natively spawning concurrent IO bound operations avoiding GIL bottlenecks
    results = await asyncio.gather(*(process_single_file(f) for f in files))
    return results
