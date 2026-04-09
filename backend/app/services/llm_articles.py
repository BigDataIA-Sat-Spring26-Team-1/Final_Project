from app.core.schemas import CategoryWeights
from app.core.logging_conf import get_logger
from app.services.llm_base import BaseLLMService
from app.core.prompts import get_article_classification_prompt

logger = get_logger("app.services.article_intelligence")

class ArticleIntelligenceService(BaseLLMService):
    """
    Handles AI analysis for raw ingested articles, focusing on multi-label 
    taxonomy classification to enable vector matching.
    """

    @classmethod
    async def classify_article(cls, title: str, summary: str, content: str) -> CategoryWeights:
        """
        Takes raw article metadata and maps it to our 10-category taxonomy weights.
        """
        logger.info("Classifying article content", title=title[:50])
        
        prompt = get_article_classification_prompt(title, summary, content)
        
        messages = [
            {"role": "system", "content": "You are a professional technical content classifier for an intelligence platform."},
            {"role": "user", "content": prompt}
        ]
        
        # We target gpt-4o-mini for cost-effective bulk classification
        result = await cls.get_structured_completion(
            response_model=CategoryWeights,
            messages=messages,
            model="gpt-4o-mini",
            temperature=0.1
        )
        
        return result
