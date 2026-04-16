from fastapi import APIRouter, HTTPException
from app.core.schemas import B2CNewsletterRequest, B2CNewsletterResponse
from app.services.b2c_agent import get_b2c_newsletter_graph
from app.core.logging_conf import get_logger

logger = get_logger("newsletter_api")
router = APIRouter()

@router.post("/b2c", response_model=B2CNewsletterResponse)
async def generate_b2c_newsletter(request: B2CNewsletterRequest):
    """
    Executes the B2C Newsletter LangGraph workflow for a specific user.
    """
    logger.info("Received B2C newsletter request", user_id=request.user_id, mode=request.execution_mode)
    
    try:
        # Pre-compile or grab the static LangGraph
        graph = get_b2c_newsletter_graph()
        
        # Initialize the baseline agent state container
        initial_state = {
            "user_id": request.user_id,
            "execution_mode": request.execution_mode,
            "status": "PENDING",
            "messages": []
        }
        
        # Await the execution of the full LangGraph!
        # We use ainvoke to ensure the FastAPI event loop isn't blocked by LLM calls
        final_state = await graph.ainvoke(initial_state)
        
        return B2CNewsletterResponse(
            status=final_state.get("status", "UNKNOWN"),
            html_content=final_state.get("generated_content", "Error generating draft."),
            execution_path_taken=["init", "curate", "write", "editor_review"] # Dynamic paths handled in future task
        )
        
    except Exception as e:
        logger.error("Failed to generate B2C newsletter", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")
