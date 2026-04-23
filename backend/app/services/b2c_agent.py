from typing import Dict, Any

from langgraph.graph import END

from app.core.logging_conf import get_logger
from app.core.metrics import NEWSLETTER_REJECTIONS_TOTAL
from app.db.snowflake import get_db_connection
from app.repository.persona import PersonaRepository
from app.services.agent_base import (
    AgentState,
    BaseAgentService,
    create_base_graph,
    track_node_latency,
)
from app.services.search import SearchService

logger = get_logger("app.services.b2c_agent")

@track_node_latency
async def initialize_state(state: AgentState) -> Dict[str, Any]:
    """
    Step 1: Set up the initial context.
    Fetches the explicit and behavioral persona details from the DB.
    """
    user_id = state.get("user_id")
    logger.info("Initializing B2C Agent State", user_id=user_id)
    
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        persona_data = PersonaRepository.get_persona(db, user_id)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
            
    return {
        "status": "INITIALIZED", 
        "messages": [],
        "user_persona": persona_data if persona_data else {}
    }

@track_node_latency
async def curate_content(state: AgentState) -> Dict[str, Any]:
    """
    Step 2: Hit the built-in SearchService to get articles matching the user's tags.
    """
    user_id = state.get("user_id")
    edition_date = state.get("edition_date")
    logger.info("Curating content for newsletter", user_id=user_id, edition_date=edition_date)

    # get_db_connection is a generator (yields), so we handle it manually here
    db_gen = get_db_connection()
    db = next(db_gen)

    try:
        recommendations = await SearchService.get_personalized_recommendations(
            user_id, limit=3, db=db, edition_date=edition_date
        )
    finally:
        # Close the connection by finishing the generator
        try:
            next(db_gen)
        except StopIteration:
            pass
    
    if not recommendations:
        return {"status": "NO_ARTICLES_FOUND", "retrieved_articles": []}
        
    # Format the payload returned from the Snowflake/Qdrant SearchService
    return {
        "retrieved_articles": recommendations.get("results", []), 
        "search_query": recommendations.get("semantic_basis", ""),
        "status": "RESEARCH_COMPLETE"
    }

@track_node_latency
async def generate_newsletter(state: AgentState) -> Dict[str, Any]:
    """
    Step 3: Take the retrieved articles and use the LLM to write a coherent briefing.
    Dynamically adheres to the user persona fetched in Step 1.
    """
    articles = state.get("retrieved_articles", [])
    if not articles:
        return {"generated_content": "No relevant news found today.", "status": "EMPTY_RESULT"}

    # Dynamically extract persona parameters context
    user_persona = state.get("user_persona", {})
    job_title = user_persona.get("job_title", "General Technology Enthusiast")
    seniority = user_persona.get("seniority", "Mid-level")
    bio_summary = user_persona.get("bio_summary", "A reader interested in tech.")

    article_summaries = "\n".join([f"- {a['title']} (Score: {a['score']}, Depth: {a.get('cluster_size', 1)} sources)" for a in articles])
    
    prompt = f"""
    You are the CurateAI Newsletter Editor.
    
    Target Audience Profile:
    - Job Role: {job_title} ({seniority})
    - Background: {bio_summary}
    
    Create a highly personalized, engaging daily newsletter specifically tailored for the audience above, based on these top articles:
    {article_summaries}
    
    Formatting Requirements:
    - Return clean, semantic HTML format (no markdown formatting blocks).
    - Include a catchy <h1> headline.
    - Write a brief introductory paragraph connecting the news to their role.
    - Present the core news as scannable bullet points mapping back to the sources.
    """
    
    logger.info("Generating newsletter via LLM with User Persona", job_title=job_title)
    response = await BaseAgentService.call_llm(messages=[{"role": "user", "content": prompt}])
    
    return {"generated_content": response, "status": "SUCCESS"}

@track_node_latency
async def editor_review(state: AgentState) -> Dict[str, Any]:
    """
    Step 4: Review the draft against the retrieved articles for hallucinations.
    """
    draft = state.get("generated_content", "")
    articles = state.get("retrieved_articles", [])
    
    prompt = f"""
    You are the CurateAI Senior Editor. Your job is strict fact-checking.
    Verify this draft does NOT invent any facts, numbers, or claims that are not present in these sources.
    
    Sources: {articles}
    
    Draft: {draft}
    
    Respond strictly with "APPROVED" if the draft is clean and factually accurate.
    If it hallucinates or invents information, respond with "REJECT:" followed by the specific reason.
    """
    
    logger.info("Editor reviewing draft for hallucinations")
    response = await BaseAgentService.call_llm(messages=[{"role": "user", "content": prompt}])
    
    if "REJECT" in response.upper():
        logger.warning("Draft rejected by editor", reason=response)
        return {
            "status": "REVISION_NEEDED", 
            "messages": [{"role": "system", "content": f"Editor Feedback: {response}"}]
        }
        
    return {"status": "APPROVED"}

@track_node_latency
async def editor_revise(state: AgentState) -> Dict[str, Any]:
    """
    Step 5: Rewrite the draft based on Editor's rejection notes.
    """
    draft = state.get("generated_content", "")
    
    # Grab the last message (which automatically contains the Editor's feedback)
    messages = state.get("messages", [])
    rejection_notes = messages[-1]["content"] if messages else "Review notes missing."
    
    prompt = f"""
    You are the CurateAI Senior Copy Editor.

    The following newsletter draft was flagged for hallucinations/errors.
    Here is the specific feedback you must address:
    {rejection_notes}
    
    Original Draft: 
    {draft}
    
    Rewrite this draft entirely to fix the noted issues. Output only the final updated HTML, with no conversational filler.
    """
    
    logger.info("Revising draft based on editor feedback")
    response = await BaseAgentService.call_llm(messages=[{"role": "user", "content": prompt}])
    
    return {"generated_content": response, "status": "REVISED"}

def route_execution_mode(state: AgentState) -> str:
    """
    Tasks 12 & 13: Splits graph execution.
    Fast mode bypasses the editor straight to END.
    Polished mode goes to editor_review.
    """
    if state.get("execution_mode") == "fast":
        return "fast"
    return "polished"

def review_condition(state: AgentState) -> str:
    """
    Determines if the graph should end or go to the revision node.
    """
    if state.get("status") == "REVISION_NEEDED":
        # Task 21: Record Rejection
        user_id = state.get("user_id", "anonymous")
        NEWSLETTER_REJECTIONS_TOTAL.labels(user_id=user_id).inc()
        return "revise"
    return "end"

def get_b2c_newsletter_graph():
    """
    Builds the static LangGraph for B2C Newsletters.
    Complete with fact-checking and revision loops.
    """
    workflow = create_base_graph()
    
    # 1. Define Nodes
    workflow.add_node("init", initialize_state)
    workflow.add_node("curate", curate_content)
    workflow.add_node("write", generate_newsletter)
    workflow.add_node("editor_review", editor_review)
    workflow.add_node("editor_revise", editor_revise)
    
    # 2. Define Edges
    workflow.set_entry_point("init")
    workflow.add_edge("init", "curate")
    workflow.add_edge("curate", "write")
    
    # Tasks 12 & 13: Dynamically route execution based on speed
    workflow.add_conditional_edges(
        "write",
        route_execution_mode,
        {
            "fast": END,                 # The Fast Mode Exit Bypass
            "polished": "editor_review"  # The Polished Mode Safe Loop
        }
    )
    
    # Task 6: Add Conditional Branching
    workflow.add_conditional_edges(
        "editor_review",
        review_condition,
        {
            "revise": "editor_revise",
            "end": END
        }
    )
    
    # After revision, go back for another review (Self-healing loop)
    workflow.add_edge("editor_revise", "editor_review")
    
    return workflow.compile()
