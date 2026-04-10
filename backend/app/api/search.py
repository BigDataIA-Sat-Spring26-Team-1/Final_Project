import json
from app.db.qdrant import get_qdrant_client
from app.core.logging_conf import get_logger
from app.db.snowflake import get_db_connection
from snowflake.connector import SnowflakeConnection
from app.services.deduplication import DeduplicationService
from fastapi import APIRouter, Depends, HTTPException, Query


logger = get_logger("app.api.search")
router = APIRouter()

@router.get("/recommendations")
async def get_user_recommendations(
    user_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: SnowflakeConnection = Depends(get_db_connection)
):
    """
    P3 Retrieval Router: Fetches top personalized articles for a specific user based on their
    behavioral and explicit category weights stored in Snowflake.
    """
    logger.info("Fetching personalized recommendations", user_id=user_id, limit=limit)
    
    # 1. Fetch User Weights from Snowflake
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT explicit_category_weights, behavioral_category_weights
            FROM user_personas
            WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User persona not found")
            
        explicit_weights = row[0]
        behavioral_weights = row[1]
        
        # Merge weights or fallback
        # In a real app we'd combine them precisely, here we just join the keys into a semantic string
        weights = {}
        if explicit_weights:
            try:
                weights.update(json.loads(explicit_weights))
            except:
                pass
        if behavioral_weights:
            try:
                weights.update(json.loads(behavioral_weights))
            except:
                pass
                
        if not weights:
            # Fallback string if they have no preferences
            search_query = "latest major technology industry news"
        else:
            # Sort categories by weight and pick top properties
            top_cats = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            search_query = " ".join([cat[0] for cat in top_cats])
            
        logger.info("Formulated semantic persona query", query=search_query)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch user persona", error=str(e))
        raise HTTPException(status_code=500, detail="Database error retrieving user")

    # 2. Vectorize the synthesized user preference query
    try:
        query_embeddings = await DeduplicationService.get_embeddings([search_query])
        query_vector = query_embeddings[0].tolist()
    except Exception as e:
        logger.error("Failed to embed user query", error=str(e))
        raise HTTPException(status_code=500, detail="LLM embedding error")

    # 3. Query Qdrant
    try:
        q_client = get_qdrant_client()
        response = q_client.query_points(
            collection_name="articles",
            query=query_vector,
            limit=limit,
        )
        
        results = []
        for hit in response.points:
            results.append({
                "cluster_id": str(hit.id),
                "score": round(hit.score, 4),
                "title": hit.payload.get("title", ""),
                "sources": hit.payload.get("sources", []),
                "cluster_size": hit.payload.get("cluster_size", 1)
            })
            
        return {
            "status": "SUCCESS",
            "user_id": user_id,
            "semantic_basis": search_query,
            "results": results
        }
    except Exception as e:
        logger.error("Qdrant retrieval error", error=str(e))
        raise HTTPException(status_code=500, detail="Vector search error")
