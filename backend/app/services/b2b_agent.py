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


async def extract_intelligence(state: AgentState) -> Dict[str, Any]:
   
    user_id = state.get("user_id")
    logger.info("Extracting B2B intelligence", user_id=user_id)

    db_gen = get_db_connection()
    db = next(db_gen)

    try:
        # B2B fetches more articles for cross-cluster business intelligence
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
        # Signal 1 — Relevance: cosine similarity is already 0–1, scale to 0–40
        relevance = article.get("score", 0.0) * 40.0

        # Signal 2 — Velocity: cluster_size of 5+ sources = full 30 pts
        velocity = min(article.get("cluster_size", 1) / 5.0, 1.0) * 30.0

        # Signal 3 — Competition Gap: cluster_size of 10+ = no gap (0 pts);
        # single-source story = maximum gap (30 pts)
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

        scored.append({**article, "opportunity_score": total_score, "urgency_tier": urgency})

    # Rank by opportunity score descending
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


async def generate_report(state: AgentState) -> Dict[str, Any]:
    
    articles = state.get("retrieved_articles", [])
    if not articles:
        return {
            "generated_content": (
                "# Enterprise Intelligence Report\n\n"
                "No relevant intelligence signals found for this profile."
            ),
            "status": "EMPTY_RESULT",
        }

    intel_lines = []
    for a in articles:
        tier = a.get("urgency_tier", "MONITOR")
        score = a.get("opportunity_score", 0)
        sources_count = a.get("cluster_size", 1)
        intel_lines.append(
            f"- [{tier}] **{a['title']}** | Score: {score} | Coverage: {sources_count} source(s)"
        )

    intel_summary = "\n".join(intel_lines)

    prompt = f"""You are the CurateAI B2B Intelligence Analyst.
Generate a concise executive research briefing in Markdown for a corporate client based on the following scored intelligence signals:

{intel_summary}

Structure the report exactly as follows:

# Executive Intelligence Briefing

## Key Opportunity Signals
Summarize the top HIDDEN GEM and ACT NOW topics with strategic context. If none exist, note that all signals are at MONITOR level.

## Market Trends Overview
Identify cross-topic patterns and emerging themes from the full signal set.

## Recommended Actions
List 3–5 concrete, prioritized next steps the client should take based on the intelligence above.

Keep the tone data-driven, concise, and professional. Do not invent facts not present in the signal data."""

    logger.info(
        "Generating B2B report via LLM",
        user_id=state.get("user_id"),
        article_count=len(articles),
    )
    response = await BaseAgentService.call_llm(messages=[{"role": "user", "content": prompt}])

    return {"generated_content": response, "status": "SUCCESS"}


def get_b2b_report_graph():
    """
    Builds the static LangGraph for B2B Intelligence Reports.
    """
    workflow = create_base_graph()

    # 1. Define Nodes
    workflow.add_node("init", initialize_state)
    workflow.add_node("intel_extract", extract_intelligence)
    workflow.add_node("report_gen", generate_report)

    # 2. Define Edges
    workflow.set_entry_point("init")
    workflow.add_edge("init", "intel_extract")
    workflow.add_edge("intel_extract", "report_gen")
    workflow.add_edge("report_gen", END)

    return workflow.compile()