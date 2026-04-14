from typing import Dict, Any
from langgraph.graph import END
from app.services.agent_base import create_base_graph, AgentState, BaseAgentService
from app.core.logging_conf import get_logger

from app.db.snowflake import get_db_connection
from app.services.search import SearchService
from app.repository.persona import PersonaRepository

logger = get_logger("app.services.b2c_agent")

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

async def curate_content(state: AgentState) -> Dict[str, Any]:
    """
    Step 2: Hit the built-in SearchService to get articles matching the user's tags.
    """
    user_id = state.get("user_id")
    logger.info("Curating content for newsletter", user_id=user_id)
    
    # get_db_connection is a generator (yields), so we handle it manually here
    db_gen = get_db_connection()
    db = next(db_gen)
    
    try:
        recommendations = await SearchService.get_personalized_recommendations(user_id, limit=3, db=db)
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

def get_b2c_newsletter_graph():
    """
    Builds the static LangGraph for B2C Newsletters.
    # TODO: Abhinav - Modify the connections or add nodes (e.g., 'editor', 'fact-check') as required.
    """
    workflow = create_base_graph()
    
    # 1. Define Nodes
    workflow.add_node("init", initialize_state)
    workflow.add_node("curate", curate_content)
    workflow.add_node("write", generate_newsletter)
    
    # 2. Define Edges
    workflow.set_entry_point("init")
    workflow.add_edge("init", "curate")
    workflow.add_edge("curate", "write")
    workflow.add_edge("write", END)
    
    return workflow.compile()
