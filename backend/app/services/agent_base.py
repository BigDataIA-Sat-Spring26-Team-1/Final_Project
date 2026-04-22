import time
from functools import wraps
from typing import TypedDict, List, Dict, Any, Callable

from langgraph.graph import StateGraph

from app.core.logging_conf import get_logger
from app.core.metrics import LANGGRAPH_NODE_LATENCY
from app.services.llm_base import BaseLLMService

logger = get_logger("app.services.agent_base")


def track_node_latency(node_func: Callable) -> Callable:
    """Record LangGraph node execution time as a Prometheus histogram.

    Lives here (not in b2c_agent) so both B2B and B2C graphs share the same
    decorator. The histogram is labeled with ``node_name`` which matches
    the wrapped function's ``__name__`` so dashboards group by node type.
    """
    @wraps(node_func)
    async def wrapper(state: "AgentState", *args, **kwargs):
        start = time.perf_counter()
        try:
            return await node_func(state, *args, **kwargs)
        finally:
            LANGGRAPH_NODE_LATENCY.labels(node_name=node_func.__name__).observe(
                time.perf_counter() - start
            )
    return wrapper

class AgentState(TypedDict):
    """
    Standard state container for all CurateAI Agents.
    """
    # Context
    user_id: str
    execution_mode: str
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
    # TODO: Abhinav/Rahul - Use this to start your LangGraph builds.
    
    Example usage in your vertical:
    
    workflow = create_base_graph()
    workflow.add_node("research", my_research_node)
    workflow.add_node("write", my_writing_node)
    workflow.set_entry_point("research")
    workflow.add_edge("research", "write")
    ...
    """
    return StateGraph(AgentState)


def track_node_latency(node_func: Callable):
    """Decorator to record LangGraph node execution time into Prometheus."""
    @wraps(node_func)
    async def wrapper(state: AgentState, *args, **kwargs):
        start = time.perf_counter()
        result = await node_func(state, *args, **kwargs)
        duration = time.perf_counter() - start

        # Record to Prometheus
        LANGGRAPH_NODE_LATENCY.labels(node_name=node_func.__name__).observe(duration)
        return result
    return wrapper
