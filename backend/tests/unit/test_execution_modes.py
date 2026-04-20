import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.b2c_agent import get_b2c_newsletter_graph

@pytest.mark.asyncio
async def test_fast_mode_bypass():
    """
    Validation for Phase 3: Fast vs. Polished Modes.
    Verifies that 'fast' mode successfully terminates after writing, bypassing the editor.
    """
    with patch("app.services.agent_base.BaseAgentService.call_llm", new_callable=AsyncMock) as mock_llm, \
         patch("app.repository.persona.PersonaRepository.get_persona", return_value={"job_title": "Engineer", "persona_archetype": "DATA_ENGINEER"}), \
         patch("app.services.search.SearchService.get_personalized_recommendations", new_callable=AsyncMock) as mock_search:
        
        mock_llm.return_value = "<html>Fast Draft</html>"
        mock_search.return_value = {"results": [{"title": "Art1", "score": 0.5}]}
        
        graph = get_b2c_newsletter_graph()
        
        # Scenario: FAST MODE
        state_fast = {"user_id": "u1", "execution_mode": "fast", "messages": []}
        final_fast = await graph.ainvoke(state_fast)
        
        # In fast mode, status comes from generate_newsletter ("SUCCESS") and loop ends
        assert final_fast["status"] == "SUCCESS"
        # ONLY 1 LLM call (the writer)
        assert mock_llm.call_count == 1
        
        # Scenario: POLISHED MODE
        mock_llm.reset_mock()
        mock_llm.side_effect = ["<html>Fine Draft</html>", "APPROVED"]
        
        state_polished = {"user_id": "u2", "execution_mode": "polished", "messages": []}
        final_polished = await graph.ainvoke(state_polished)
        
        assert final_polished["status"] == "APPROVED"
        # Exactly 2 LLM calls (write + review)
        assert mock_llm.call_count == 2
        print("\n[SUCCESS] Routing logic correctly distinguishes between Fast and Polished modes.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_fast_mode_bypass())
