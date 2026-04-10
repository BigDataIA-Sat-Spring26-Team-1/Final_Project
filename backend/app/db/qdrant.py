import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

def get_qdrant_client() -> QdrantClient:
    """
    Returns a connected and authenticated QdrantClient instance.
    
    Dynamically switches between unauthenticated local connections (for Docker Dev)
    and authenticated REST API connections (for Cloud environments) based on 
    whether an API key is specified in the environment variables.
    """
    if settings.qdrant_api_key:
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
    else:
        # Local unauthenticated
        return QdrantClient(url=settings.qdrant_url)

def sync_vector_collections():
    """
    Ensures that the necessary Qdrant collections exist upon backend initialization.
    
    This function acts as a health check and auto-provisioning step. If the Qdrant 
    container is fresh or data was wiped, it recreates the 'articles' collection using
    the exact Cosine Distance specifications and vector dimension mapped to the active 
    OpenAI embedding model (from config.py).
    
    Fails safely with a logged error if the connection times out.
    """
    logger.info("Syncing Qdrant vector collections...")
    client = get_qdrant_client()
    collection_name = "articles"
    
    try:
        if not client.collection_exists(collection_name):
            logger.info("Creating missing Qdrant collection", collection=collection_name)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.vector_dimension_size, 
                    distance=Distance.COSINE
                )
            )
            logger.info("Successfully created Qdrant collection", collection=collection_name)
        else:
            logger.info("Qdrant collection exists - health check passed", collection=collection_name)
    except Exception as e:
        logger.error("Failed to sync Qdrant collections", error=str(e))
        # We don't strictly crash the app if Qdrant isn't immediately available at startup,
        # but we log it aggressively
