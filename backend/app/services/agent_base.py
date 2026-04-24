import time
from functools import wraps
from typing import TypedDict, List, Dict, Any, Callable
from langgraph.graph import StateGraph
from app.core.logging_conf import get_logger
from app.core.metrics import LANGGRAPH_NODE_LATENCY
from app.services.llm_base import BaseLLMService

logger = get_logger("app.services.agent_base")

def track_node_latency(node_func: Callable) -> Callable:

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
    user_id: str
    execution_mode: str
    user_persona: Dict[str, Any]
    
    search_query: str
    retrieved_articles: List[Dict[str, Any]]
    
    messages: List[Dict[str, str]]
    next_step: str
    
    generated_content: str 
    status: str
    metadata: Dict[str, Any]

class BaseAgentService:
    
    @staticmethod
    async def call_llm(
        messages: List[Dict[str, str]],
        response_model: Any = None,
        temperature: float | None = None,
    ) -> Any:

        if response_model:
            kwargs = {"response_model": response_model, "messages": messages}
            if temperature is not None:
                kwargs["temperature"] = temperature
            return await BaseLLMService.get_structured_completion(**kwargs)
        kwargs = {"messages": messages}
        if temperature is not None:
            kwargs["temperature"] = temperature
        return await BaseLLMService.get_text_completion(**kwargs)

def create_base_graph() -> StateGraph:
    
    return StateGraph(AgentState)


def track_node_latency(node_func: Callable):
    @wraps(node_func)
    async def wrapper(state: AgentState, *args, **kwargs):
        start = time.perf_counter()
        result = await node_func(state, *args, **kwargs)
        duration = time.perf_counter() - start

        # Record to Prometheus
        LANGGRAPH_NODE_LATENCY.labels(node_name=node_func.__name__).observe(duration)
        return result
    return wrapper