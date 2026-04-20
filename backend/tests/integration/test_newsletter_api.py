import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app

# We use the FastAPI TestClient to test the HTTP routing and JSON serialization layers
client = TestClient(app)

def test_b2c_newsletter_api_json_mapping():
    """
    Task 10: End-to-End JSON Mapping Test
    Ensures that the FastAPI POST payload perfectly deserializes into the Pydantic request,
    simulates the LangGraph execution safely (without wasting real OpenAI tokens),
    and strictly validates the outgoing JSON structure.
    """
    
    # We mock the LangGraph heavily to prevent actual LLM/OpenAI network calls and save money
    with patch("app.api.newsletter.get_b2c_newsletter_graph") as mock_get_graph:
        
        mock_graph_instance = AsyncMock()
        mock_graph_instance.ainvoke.return_value = {
            "status": "APPROVED",
            "generated_content": "<h1>The Mocked Daily Data</h1><p>Success from graph!</p>"
        }
        mock_get_graph.return_value = mock_graph_instance
        
        # We also mock the Database lifespan hooks so the test doesn't crash 
        # just because Docker/Qdrant is currently spun down on your local machine.
        with patch("app.main.sync_database_schema"), patch("app.main.sync_vector_collections"):
            response = client.post(
                "/api/v1/newsletter/b2c",
                json={
                    "user_id": "usr_9983",
                    "execution_mode": "polished"
                }
            )

    # 1. Assert HTTP Status
    assert response.status_code == 200
    
    # 2. Extract and assert strict JSON Payload mapping
    data = response.json()
    assert data["status"] == "APPROVED"
    assert "The Mocked Daily Data" in data["html_content"]
    assert "init" in data["execution_path_taken"]
    assert "editor_review" in data["execution_path_taken"]
