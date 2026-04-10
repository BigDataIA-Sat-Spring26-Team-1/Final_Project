from app.core.schemas import CategoryWeights
from app.core.logging_conf import get_logger
from app.services.llm_base import BaseLLMService
from app.core.taxonomy import get_axiomatic_weights
from app.core.prompts import get_article_classification_prompt

logger = get_logger("app.services.article_intelligence")


class ArticleIntelligenceService(BaseLLMService):
    """Classifies articles into a 10-category taxonomy using a hybrid approach.

    First attempts fast keyword matching against known technical terms.
    Falls back to an LLM call only when keywords are insufficient.
    """

    @classmethod
    async def classify_article(cls, title: str, summary: str, content: str) -> CategoryWeights:
        """Maps a single article to weighted taxonomy categories.

        Args:
            title: Article headline.
            summary: Short description or RSS snippet.
            content: Full extracted text (may be empty).

        Returns:
            CategoryWeights with a 0.0-1.0 score per category.
        """
        try:
            # Try keyword-based classification first (instant, no API cost)
            search_text = f"{title} {summary}"
            axiomatic_hits = get_axiomatic_weights(search_text)

            if axiomatic_hits:
                logger.info("Keyword classification matched", title=title[:50], hits=list(axiomatic_hits.keys()))
                full_weights = {cat: 0.0 for cat in CategoryWeights.model_fields.keys()}
                full_weights.update(axiomatic_hits)
                return CategoryWeights(**full_weights)

            # No keyword match — use the LLM for deeper analysis
            logger.info("Using LLM classification", title=title[:50])

            article_content = (content or "")[:8000]
            article_summary = (summary or "")[:1000]

            prompt = get_article_classification_prompt(title, article_summary, article_content)
            messages = [
                {"role": "system", "content": "You are a professional technical content classifier for an intelligence platform."},
                {"role": "user", "content": prompt}
            ]

            result = await cls.get_structured_completion(
                response_model=CategoryWeights,
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.1
            )

            if not result:
                logger.warning("LLM returned empty result, defaulting to neutral weights", title=title[:50])
                return CategoryWeights(**{cat: 0.0 for cat in CategoryWeights.model_fields.keys()})

            return result

        except Exception as e:
            logger.error("Classification failed for article", title=title[:50], error=str(e))
            return CategoryWeights(**{cat: 0.0 for cat in CategoryWeights.model_fields.keys()})
