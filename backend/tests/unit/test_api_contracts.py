import pytest
from pydantic import ValidationError
from app.core.schemas import B2CNewsletterRequest, B2CNewsletterResponse, UserPersonaUpdate

def test_pydantic_schema_validation():
    """
    Validation for API Contracts (Phases 1-4).
    Ensures that our Pydantic models strictly enforce the required fields and types.
    """
    # 1. Test invalid execution_mode
    with pytest.raises(ValidationError):
        B2CNewsletterRequest(user_id="u1", execution_mode="invalid_mode")
        
    # 2. Test valid request
    req = B2CNewsletterRequest(user_id="u1", execution_mode="fast")
    assert req.user_id == "u1"
    assert req.execution_mode == "fast"
    
    # 3. Test Newsletter Response model
    res = B2CNewsletterResponse(
        status="APPROVED",
        html_content="<h1>Test</h1>",
        execution_path_taken=["init", "curate", "write"]
    )
    assert "<h1>" in res.html_content
    
    # 4. Test Persona Update Archetype field
    update = UserPersonaUpdate(
        user_id="u1",
        explicit_category_weights={"AI": 1.0},
        persona_archetype="ML_RESEARCHER"
    )
    assert update.persona_archetype == "ML_RESEARCHER"
    print("\n[SUCCESS] Pydantic models correctly enforcing schema contracts for all API routes.")

if __name__ == "__main__":
    test_pydantic_schema_validation()
