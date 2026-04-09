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

from typing import Type, TypeVar, List, Dict, Any, Optional

logger = get_logger("app.services.llm_base")

T = TypeVar("T", bound=BaseModel)

class BaseLLMService:
    """
    Unified base class for LLM interactions using LiteLLM.
    Provides standardized methods for structured outputs and error handling.
    """
    
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
        """
        Executes an asynchronous LLM call with exponential backoff and forces the response into a Pydantic model.
        """
        settings = get_settings()
        
        try:
            logger.info("Initiating LiteLLM structured completion", model=model, response_shape=response_model.__name__)
            
            response = await acompletion(
                model=model,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
                api_key=settings.openai_api_key
            )
            
            content_str = response.choices[0].message.content
            if not content_str:
                raise ValueError("LLM returned an empty response content.")
                
            return response_model.model_validate_json(content_str)
            
        except Exception as e:
            # We log but reraise for tenacity to catch and retry if applicable
            logger.error("LiteLLM structured completion effort failed", 
                         model=model, 
                         error=str(e))
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
        """
        Standard text-based completion for non-structured tasks.
        """
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
            logger.error("LiteLLM text completion failure", error=str(e))
            raise RuntimeError(f"LLM Text Error: {str(e)}")
