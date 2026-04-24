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
from app.core.metrics import LLM_REQUESTS_TOTAL, LLM_TOKENS_TOTAL, LLM_COST_TOTAL

from typing import Type, TypeVar, List, Dict

logger = get_logger("app.services.llm_base")

T = TypeVar("T", bound=BaseModel)

class BaseLLMService:
    
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
        model: str = None,
        temperature: float = 0.0,
    ) -> T:
        settings = get_settings()
        if not model:
            model = settings.default_llm_model
        
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
            
            usage = getattr(response, 'usage', None)
            if usage:
                LLM_TOKENS_TOTAL.labels(model=model, token_type="prompt").inc(usage.prompt_tokens)
                LLM_TOKENS_TOTAL.labels(model=model, token_type="completion").inc(usage.completion_tokens)
                
                cost = (usage.prompt_tokens * 0.00000015) + (usage.completion_tokens * 0.0000006)
                LLM_COST_TOTAL.labels(model=model).inc(cost)

            LLM_REQUESTS_TOTAL.labels(model=model, status="success").inc()
            
            return response_model.model_validate_json(content_str)
            
        except Exception as e:
            LLM_REQUESTS_TOTAL.labels(model=model, status="error").inc()
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
        model: str = None,
        temperature: float = 0.7
    ) -> str:
        settings = get_settings()
        if not model:
            model = settings.default_llm_model
        
        try:
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                api_key=settings.openai_api_key
            )
            usage = getattr(response, 'usage', None)
            if usage:
                LLM_TOKENS_TOTAL.labels(model=model, token_type="prompt").inc(usage.prompt_tokens)
                LLM_TOKENS_TOTAL.labels(model=model, token_type="completion").inc(usage.completion_tokens)
                
                cost = (usage.prompt_tokens * 0.00000015) + (usage.completion_tokens * 0.0000006)
                LLM_COST_TOTAL.labels(model=model).inc(cost)

            LLM_REQUESTS_TOTAL.labels(model=model, status="success").inc()
            return response.choices[0].message.content or ""
            
        except Exception as e:
            LLM_REQUESTS_TOTAL.labels(model=model, status="error").inc()
            logger.error("LLM text completion failed", error=str(e))
            raise RuntimeError(f"LLM Error: {str(e)}")