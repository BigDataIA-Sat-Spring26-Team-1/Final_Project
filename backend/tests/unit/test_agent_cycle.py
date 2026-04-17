import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.b2c_agent import get_b2c_newsletter_graph

@pytest.mark.asyncio
async def test_self_healing_loop_execution():
    """
    Validation for Phase 1: Core Agent Logic.
    Verifies that the LangGraph correctly handles an Editor reject -> revision sequence.
    """
    # 1. Mock the LLM to simulate a Hallucination Rejection then an Approval
    # First call: curate (not LLM)
    # Second call: generate_newsletter (LLM)
    # Third call: editor_review (LLM - REJECT)
    # Fourth call: editor_revise (LLM)
    # Fifth call: editor_review (LLM - APPROVED)
    
    mock_responses = [
        "<html>Draft with error</html>", # generate_newsletter
        "REJECT: Hallucination detected regarding Snowflake prices.", # editor_review
        "<html>Corrected Draft</html>", # editor_revise
        "APPROVED" # editor_review (second pass)
    ]
    
    with patch("app.services.agent_base.BaseAgentService.call_llm", new_callable=AsyncMock) as mock_llm, \
         patch("app.repository.persona.PersonaRepository.get_persona", return_value={"job_title": "Engineer", "seniority": "Senior", "persona_archetype": "ML_RESEARCHER"}), \
         patch("app.services.search.SearchService.get_personalized_recommendations", new_callable=AsyncMock) as mock_search:
        
        mock_llm.side_effect = mock_responses
        mock_search.return_value = {"results": [{"title": "Article 1", "score": 0.9}]}
        
        graph = get_b2c_newsletter_graph()
        
        initial_state = {
            "user_id": "test_user_123",
            "execution_mode": "polished",
            "messages": []
        }
        
        final_state = await graph.ainvoke(initial_state)
        
        # Assertions
        assert final_state["status"] == "APPROVED"
        assert "Corrected Draft" in final_state["generated_content"]
        # Total LLM calls should be 4 (generate, review1, revise, review2)
        assert mock_llm.call_count == 4
        print("\n[SUCCESS] Agent successfully self-healed after editor rejection.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_self_healing_loop_execution())
