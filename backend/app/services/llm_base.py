from pydantic import BaseModel
from litellm import acompletion
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.core.config import get_settings
from app.core.logging_conf import get_logger

from typing import Type, TypeVar, List, Dict

logger = get_logger("app.services.llm_base")

T = TypeVar("T", bound=BaseModel)

class BaseLLMService:
    """Provides a standardized gateway to LLM models with built-in retries and structured output."""
    
    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception)),
        before_sleep=before_sleep_log(logger, "info"),
        reraise=True
    )
    async def get_structured_completion(
        response_model: Type[T],
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
    ) -> T:
        """Calls the LLM and guarantees the result matches the provided Pydantic model format."""
        settings = get_settings()
        
        try:
            logger.info("Requesting structured LLM completion", model=model, response_shape=response_model.__name__)
            
            response = await acompletion(
                model=model,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
                api_key=settings.openai_api_key
            )
            
            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.error("LLM returned an invalid response object", response=str(response))
                raise ValueError("LLM returned no choices.")
                
            content_str = response.choices[0].message.content
            if not content_str:
                logger.warning("LLM response content is empty")
                raise ValueError("LLM returned an empty response content.")
                
            return response_model.model_validate_json(content_str)
            
        except Exception as e:
            logger.error("Structured LLM completion failed", model=model, error=str(e), error_type=type(e).__name__)
            raise

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=6),
        retry=retry_if_exception_type((Exception)),
        before_sleep=before_sleep_log(logger, "info"),
        reraise=True
    )
    async def get_text_completion(
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7
    ) -> str:
        """Standard text completion for freeform logic that doesn't need strict Pydantic matching."""
        settings = get_settings()
        
        try:
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                api_key=settings.openai_api_key
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM text completion failed", error=str(e))
            raise RuntimeError(f"LLM Error: {str(e)}")
