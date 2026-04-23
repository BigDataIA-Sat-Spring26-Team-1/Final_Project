import hashlib
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional
from app.core.logging_conf import get_logger
from app.repository.persona import PersonaRepository
from app.db.snowflake import get_db_connection

logger = get_logger("app.core.cache")

INTERNAL_CACHE: Dict[str, Any] = {}

def generate_archetype_cache_key(archetype: str) -> str:

    today = datetime.now().strftime("%Y-%m-%d")
    raw_string = f"{archetype}_{today}"
    return hashlib.sha256(raw_string.encode()).hexdigest()

def cached_newsletter(func):

    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request") or args[0]
        user_id = request.user_id
        
        logger.info("Cache check initiated", user_id=user_id)
        db_gen = get_db_connection()
        db = next(db_gen)
        
        try:
            persona = PersonaRepository.get_persona(db, user_id)
            if not persona:
                logger.warning("No persona found, bypassing cache", user_id=user_id)
                return await func(*args, **kwargs)
            
            archetype = persona.get("persona_archetype", "GENERAL_TECH_ENVELOPE")
            cache_key = generate_archetype_cache_key(archetype)
            
            if cache_key in INTERNAL_CACHE:
                logger.info("CACHE HIT: Shared archetype content found", archetype=archetype, user_id=user_id)
                return INTERNAL_CACHE[cache_key]
            
            logger.info("CACHE MISS: Generating fresh content for archetype", archetype=archetype)
            result = await func(*args, **kwargs)
            
            INTERNAL_CACHE[cache_key] = result
            return result
            
        finally:
            try:
                next(db_gen) 
            except StopIteration:
                pass
                
    return wrapper

def invalidate_archetype_cache(archetype: str):

    cache_key = generate_archetype_cache_key(archetype)
    if cache_key in INTERNAL_CACHE:
        del INTERNAL_CACHE[cache_key]
        logger.info("Cache invalidated for archetype", archetype=archetype)