from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph
from app.services.llm_base import BaseLLMService
from app.core.logging_conf import get_logger

logger = get_logger("app.services.agent_base")

class AgentState(TypedDict):
    """
    Standard state container for all CurateAI Agents.
    Teammates: Use this as your base state. You can extend it if needed.
    """
    # Context
    user_id: str
    user_persona: Dict[str, Any]
    
    # Data pipeline
    search_query: str
    retrieved_articles: List[Dict[str, Any]]
    
    # Reasoning
    messages: List[Dict[str, str]]
    next_step: str
    
    # Final product
    generated_content: str  # Newsletter HTML or B2B Report Markdown
    status: str
    metadata: Dict[str, Any]

class BaseAgentService:
    """
    Base utility class for Agent logic.
    Provides standardized methods for node implementations.
    """
    
    @staticmethod
    async def call_llm(messages: List[Dict[str, str]], response_model: Any = None) -> Any:
        """Centralized LLM gateway for agents using our BaseLLMService."""
        if response_model:
            return await BaseLLMService.get_structured_completion(
                response_model=response_model,
                messages=messages
            )
        return await BaseLLMService.get_text_completion(messages=messages)

def create_base_graph() -> StateGraph:
    """
    Initializes a StateGraph with the standard AgentState.
    Teammates (Abhinav/Rahul): Use this to start your LangGraph builds.
    
    Example usage in your vertical:
    
    workflow = create_base_graph()
    workflow.add_node("research", my_research_node)
    workflow.add_node("write", my_writing_node)
    workflow.set_entry_point("research")
    workflow.add_edge("research", "write")
    ...
    """
    return StateGraph(AgentState)
