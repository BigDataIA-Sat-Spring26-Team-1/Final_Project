from typing import Dict, Any
from langgraph.graph import END
from app.services.agent_base import create_base_graph, AgentState, BaseAgentService
from app.core.logging_conf import get_logger
from app.db.snowflake import get_db_connection
from app.services.search import SearchService

logger = get_logger("app.services.b2b_agent")


async def initialize_state(state: AgentState) -> Dict[str, Any]:
    
    logger.info("Initializing B2B Agent State", user_id=state.get("user_id"))
    return {"status": "INITIALIZED"}


def get_b2b_report_graph():
    workflow = create_base_graph()
    workflow.add_node("init", initialize_state)
    workflow.add_node("intel_extract", extract_intelligence)
    workflow.set_entry_point("init")
    workflow.add_edge("init", "intel_extract")
    workflow.add_edge("intel_extract", END)
    return workflow.compile()

async def extract_intelligence(state: AgentState) -> Dict[str, Any]:
    
    user_id = state.get("user_id")
    logger.info("Extracting B2B intelligence", user_id=user_id)

    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        recommendations = await SearchService.get_personalized_recommendations(
            user_id, limit=10, db=db
        )
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    if not recommendations:
        return {"status": "NO_ARTICLES_FOUND", "retrieved_articles": []}

    articles = recommendations.get("results", [])
    scored = []
    for article in articles:
        relevance = article.get("score", 0.0) * 40.0
        velocity = min(article.get("cluster_size", 1) / 5.0, 1.0) * 30.0
        competition_gap = (1.0 - min(article.get("cluster_size", 1) / 10.0, 1.0)) * 30.0
        total_score = round(relevance + velocity + competition_gap, 2)

        if total_score >= 85:
            urgency = "HIDDEN GEM"
        elif total_score >= 70:
            urgency = "ACT NOW"
        elif total_score >= 50:
            urgency = "MONITOR"
        else:
            urgency = "SKIP"

        scored.append({
            **article,
            "opportunity_score": total_score,
            "urgency_tier": urgency,
        })

    scored.sort(key=lambda x: x["opportunity_score"], reverse=True)

    logger.info(
        "Opportunity scoring complete",
        user_id=user_id,
        article_count=len(scored),
        top_tier=scored[0]["urgency_tier"] if scored else "N/A",
    )

    return {
        "retrieved_articles": scored,
        "search_query": recommendations.get("semantic_basis", ""),
        "status": "RESEARCH_COMPLETE",
    }