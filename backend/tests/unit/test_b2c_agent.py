import pytest
from unittest.mock import patch, AsyncMock
from app.services.b2c_agent import initialize_state, curate_content, generate_newsletter, editor_review

@pytest.mark.asyncio
async def test_part1_tasks_1_and_2_init_and_curate():
    """
    PART 1: Verifies Task 1 (initialize_state) and Task 2 (curate_content)
    """
    # ---- Test Task 1: Persona Injection ----
    mock_state_1 = {"user_id": "test_user"}
    mock_persona = {"job_title": "Data Engineer", "seniority": "Senior"}
    
    with patch("app.services.b2c_agent.get_db_connection") as mock_db, \
         patch("app.services.b2c_agent.PersonaRepository.get_persona", return_value=mock_persona):
        
        mock_db.return_value = iter(["db_instance"])
        init_result = await initialize_state(mock_state_1)
        
        assert init_result["status"] == "INITIALIZED"
        assert init_result["user_persona"]["job_title"] == "Data Engineer"

    # ---- Test Task 2: Article Curation ----
    mock_state_2 = {"user_id": "test_user"}
    mock_search_results = {"results": [{"title": "Big Data News"}], "semantic_basis": "data"}
    
    with patch("app.services.b2c_agent.get_db_connection") as mock_db, \
         patch("app.services.b2c_agent.SearchService.get_personalized_recommendations", new_callable=AsyncMock) as mock_search:
        
        mock_db.return_value = iter(["db_instance"])
        mock_search.return_value = mock_search_results
        curate_result = await curate_content(mock_state_2)
        
        assert curate_result["status"] == "RESEARCH_COMPLETE"
        assert len(curate_result["retrieved_articles"]) == 1


@pytest.mark.asyncio
async def test_part2_tasks_3_and_4_generation_and_review():
    """
    PART 2: Verifies Task 3 (generate_newsletter) and Task 4 (editor_review).
    """
    mock_state = {
        "retrieved_articles": [{"title": "AI Growth", "score": 0.9}],
        "generated_content": "This is a draft.",
        "user_persona": {"job_title": "Data Scientist"}
    }
    
    # ---- Test Task 3: Writer Prompt ----
    with patch("app.services.b2c_agent.BaseAgentService.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "<h1>Mock HTML</h1>"
        writer_result = await generate_newsletter(mock_state)
        
        assert writer_result["status"] == "SUCCESS"
        assert "Mock HTML" in writer_result["generated_content"]
        
    # ---- Test Task 4: Editor Guardrails ----
    with patch("app.services.b2c_agent.BaseAgentService.call_llm", new_callable=AsyncMock) as mock_editor_llm:
        mock_editor_llm.return_value = "REJECT: Hallucination detected."
        review_result = await editor_review(mock_state)
        
        assert review_result["status"] == "REVISION_NEEDED"
        assert "REJECT" in review_result["messages"][0]["content"]
