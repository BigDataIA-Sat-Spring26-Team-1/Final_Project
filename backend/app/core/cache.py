import hashlib
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional
from app.core.logging_conf import get_logger
from app.repository.persona import PersonaRepository
from app.db.snowflake import get_db_connection

logger = get_logger("app.core.cache")

# --- In-Memory Cache Store ---
# In a production environment, this would be Redis or Snowflake.
# For the prototype, we use a shared module-level dictionary to avoid 
# adding extra infrastructure while proving the cost-scaling logic.
INTERNAL_CACHE: Dict[str, Any] = {}

def generate_archetype_cache_key(archetype: str) -> str:
    """
    Task 15: Generates a unique SHA-256 key based on Archetype + Current Date.
    This ensures all users with the same archetype share the same cached content.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    raw_string = f"{archetype}_{today}"
    return hashlib.sha256(raw_string.encode()).hexdigest()

def cached_newsletter(func):
    """
    Task 16: Asynchronous decorator for caching newsletter generation.
    Orchestrates the lookup from Persona Archetype to Cache Key.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # We assume the first argument to the controller is the 'request' object (B2CNewsletterRequest)
        request = kwargs.get("request") or args[0]
        user_id = request.user_id
        
        logger.info("Cache check initiated", user_id=user_id)
        
        # 1. Resolve User Archetype (Task 17 Logic)
        # We need a DB connection to check the user's persona definition in Snowflake
        db_gen = get_db_connection()
        db = next(db_gen)
        
        try:
            persona = PersonaRepository.get_persona(db, user_id)
            if not persona:
                logger.warning("No persona found, bypassing cache", user_id=user_id)
                return await func(*args, **kwargs)
            
            archetype = persona.get("persona_archetype", "GENERAL_TECH_ENVELOPE")
            cache_key = generate_archetype_cache_key(archetype)
            
            # 2. Key Check
            if cache_key in INTERNAL_CACHE:
                logger.info("CACHE HIT: Shared archetype content found", archetype=archetype, user_id=user_id)
                return INTERNAL_CACHE[cache_key]
            
            # 3. Cache Miss - Execute the expensive LangGraph/LLM flow
            logger.info("CACHE MISS: Generating fresh content for archetype", archetype=archetype)
            result = await func(*args, **kwargs)
            
            # 4. Store for subsequent users of the same archetype
            INTERNAL_CACHE[cache_key] = result
            return result
            
        finally:
            try:
                next(db_gen) # Close DB connection
            except StopIteration:
                pass
                
    return wrapper

def invalidate_archetype_cache(archetype: str):
    """
    Task 18: Manually clear the cache for a specific archetype.
    Used when the content ingestion pipe detects significant new trends.
    """
    cache_key = generate_archetype_cache_key(archetype)
    if cache_key in INTERNAL_CACHE:
        del INTERNAL_CACHE[cache_key]
        logger.info("Cache invalidated for archetype", archetype=archetype)
