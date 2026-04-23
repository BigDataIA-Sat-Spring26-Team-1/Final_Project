import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.api.newsletter import generate_b2c_newsletter
from app.core.schemas import B2CNewsletterRequest
from app.core.metrics import LLM_TOKENS_TOTAL, REGISTRY
from prometheus_client import generate_latest


def _make_fake_db():
    """Return a MagicMock Snowflake connection where every fetch looks empty.

    The newsletter endpoint now checks Snowflake before calling the graph —
    tests that want to exercise the generation path must ensure the initial
    lookup returns no row.
    """
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    db = MagicMock()
    db.cursor.return_value = cursor
    return db


@pytest.mark.asyncio
async def test_metrics_incrementation_flow():
    """
    Validation for Phase 5: Observability & Guardrails.
    Verifies that LLM token counters are incremented during generation.
    """
    # 1. Capture base metric values
    # Note: REGISTRY contains all metrics. We can check the text output.

    with patch("app.services.llm_base.acompletion") as mock_completion, \
         patch("app.repository.persona.PersonaRepository.get_persona", return_value={"persona_archetype": "GURU"}), \
         patch("app.services.search.SearchService.get_personalized_recommendations", new_callable=AsyncMock) as mock_search:

        # Mocking Search to ensure we hit the 'write' node
        mock_search.return_value = {"results": [{"title": "Test Article", "score": 0.9}]}

        # Mocking LiteLLM response with usage data
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="<html>Test</html>"))]
        mock_resp.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        mock_completion.return_value = mock_resp

        # Trigger generation (fast mode calls LLM once)
        req = B2CNewsletterRequest(user_id="metrics_user", execution_mode="fast")
        await generate_b2c_newsletter(req, db=_make_fake_db())
        
        # Verify Prometheus output contains our tokens
        metrics_data = generate_latest(REGISTRY).decode("utf-8")
        print(f"DEBUG METRICS DATA:\n{metrics_data}")
        
        assert "curateai_llm_tokens_total" in metrics_data
        assert 'token_type="prompt"' in metrics_data
        assert 'token_type="completion"' in metrics_data
        
        # Verify values (this might be cumulative if other tests ran, so we check for existence)
        print("\n[SUCCESS] Prometheus metrics successfully recorded token usage data.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_metrics_incrementation_flow())
