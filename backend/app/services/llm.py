from app.core.schemas import PersonaExtractionResult
from app.services.llm_base import BaseLLMService
from app.core.prompts import get_persona_extraction_prompt
from app.core.logging_conf import get_logger

logger = get_logger("app.services.llm")

class PersonaLLMService(BaseLLMService):
    
    @classmethod
    async def extract_persona(cls, text: str, source_type: str) -> PersonaExtractionResult:

        logger.info("Starting persona extraction flow", source_type=source_type)
        
        prompt = get_persona_extraction_prompt(source_type, text)
        
        messages = [
            {"role": "system", "content": "You are an expert technical intelligence extractor analyzing resumes and profiles."},
            {"role": "user", "content": prompt}
        ]

        return await cls.get_structured_completion(
            response_model=PersonaExtractionResult,
            messages=messages,
            model="gpt-4o-mini"
        )