import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.api.newsletter import generate_b2c_newsletter
from app.core.schemas import B2CNewsletterRequest
from app.core.cache import INTERNAL_CACHE

@pytest.mark.asyncio
async def test_shared_archetype_caching_convergence():
    """
    Validation for Phase 4: Archetype-First Caching.
    Verifies that two different users sharing the same archetype hit the cache.
    """
    INTERNAL_CACHE.clear() # Reset cache
    
    # Mock return for the LangGraph execution
    mock_graph_result = {
        "status": "APPROVED",
        "generated_content": "<html>Cached Content</html>"
    }

    # We need to mock:
    # 1. The Persona Repository (to return same archetype for different users)
    # 2. The LangGraph ainvoke call
    
    with patch("app.core.cache.PersonaRepository.get_persona") as mock_get_persona, \
         patch("app.api.newsletter.get_b2c_newsletter_graph") as mock_get_graph:
        
        # Mocking the Graph Object and its ainvoke method
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=mock_graph_result)
        mock_get_graph.return_value = mock_graph
        
        # Scenario: Two users, both ML_RESEARCHER
        mock_get_persona.side_effect = [
            {"persona_archetype": "ML_RESEARCHER"},
            {"persona_archetype": "ML_RESEARCHER"}
        ]
        
        req1 = B2CNewsletterRequest(user_id="user_1", execution_mode="fast")
        req2 = B2CNewsletterRequest(user_id="user_2", execution_mode="fast")
        
        # First call (Cold)
        res1 = await generate_b2c_newsletter(req1)
        
        # Second call (Should be Cache Hit)
        res2 = await generate_b2c_newsletter(req2)
        
        # Assertions
        assert res1.html_content == "<html>Cached Content</html>"
        assert res2.html_content == "<html>Cached Content</html>"
        
        # The graph (LLM) should have been called EXACTLY ONCE
        assert mock_graph.ainvoke.call_count == 1
        print("\n[SUCCESS] Archetype caching confirmed. User B successfully hit User A's cached result.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_shared_archetype_caching_convergence())
