from typing import Dict, Any
from langgraph.graph import END
from app.services.agent_base import create_base_graph, AgentState, BaseAgentService
from app.core.logging_conf import get_logger
from app.db.snowflake import get_db_connection
from app.services.search import SearchService

logger = get_logger("app.services.b2b_agent")


async def initialize_state(state: AgentState) -> Dict[str, Any]:
    """
    Step 1: Set up the Enterprise context (Industry, Competitors).
    """
    logger.info("Initializing B2B Agent State", user_id=state.get("user_id"))
    return {"status": "INITIALIZED"}


def get_b2b_report_graph():
    """
    Builds the static LangGraph for B2B Intelligence Reports.
    """
    workflow = create_base_graph()
    workflow.add_node("init", initialize_state)
    workflow.set_entry_point("init")
    workflow.add_edge("init", END)
    return workflow.compile()