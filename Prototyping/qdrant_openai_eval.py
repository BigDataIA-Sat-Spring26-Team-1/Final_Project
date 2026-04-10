import os
import sys
import time
import asyncio
import numpy as np
from typing import List, Dict, Any
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# Setup python path to import from backend/app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.core.config import get_settings
from app.db.snowflake import get_db_connection
from app.repository.article import ArticleRepository
from litellm import aembedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

settings = get_settings()

def get_articles(limit=500):
    print(f"Fetching {limit} distinct recent articles from Snowflake...")
    articles = []
    # get_db_connection() is a generator used as a context manager
    generator = get_db_connection()
    conn = next(generator)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT id, title, summary, source_name FROM articles_raw ORDER BY fetched_at DESC LIMIT {limit}")
        cols = [c[0].lower() for c in cur.description]
        articles = [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        try:
            next(generator)
        except StopIteration:
            pass
    return articles

def clean_text(art):
    return f"{art.get('title', '')} {art.get('summary', '')}".strip()

async def get_openai_embeddings(texts: List[str]) -> np.ndarray:
    print(f"Calling OpenAI text-embedding-3-small for {len(texts)} texts...")
    
    # Batch requests to OpenAI (LiteLLM handles it but we batch just in case)
    embeddings = []
    chunk_size = 100
    for i in range(0, len(texts), chunk_size):
        chunk = texts[i:i+chunk_size]
        response = await aembedding(
            model="text-embedding-3-small", 
            input=chunk,
            api_key=settings.openai_api_key
        )
        for item in response['data']:
            embeddings.append(item['embedding'])
    return np.array(embeddings)

def cluster_vectors(embeddings, similarity_threshold):
    print(f"Clustering with threshold {similarity_threshold}...")
    sim_matrix = cosine_similarity(embeddings)
    clusters = []
    visited = set()
    
    for i in range(len(embeddings)):
        if i in visited:
            continue
        similar_indices = np.where(sim_matrix[i] >= similarity_threshold)[0]
        current_cluster = []
        for idx in similar_indices:
            if idx not in visited:
                current_cluster.append(idx)
                visited.add(idx)
        if current_cluster:
            clusters.append(current_cluster)
            
    return clusters

def run_qdrant_test(articles, vectors):
    print("\n--- Testing Qdrant Local Integration ---")
    client = QdrantClient(host="localhost", port=6333)
    collection_name = "curateai_articles_prototype"
    
    # Ensure collection exists
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)
        
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vectors.shape[1], distance=Distance.COSINE),
    )
    
    # Build points
    points = [
        PointStruct(
            id=i,
            vector=vectors[i].tolist(),
            payload={"title": articles[i]["title"], "source": articles[i]["source_name"]}
        ) for i in range(len(articles))
    ]
    
    t0 = time.time()
    client.upsert(
        collection_name=collection_name,
        points=points
    )
    t1 = time.time()
    print(f"Successfully upserted {len(points)} vectors into Qdrant in {t1-t0:.2f} seconds.")
    
    # Execute a search test
    print("Testing Vector Search via Qdrant on Article index 0...")
    hits = client.query_points(
        collection_name=collection_name,
        query=vectors[0].tolist(),
        limit=3
    ).points
    for hit in hits:
        print(f"  -> Score: {hit.score:.4f} | Title: {hit.payload['title'][:60]}")

async def main():
    print("====================================")
    print("DEDUPLICATION & QDRANT EVAL PROTOTYPE")
    print("====================================\n")
    
    articles = get_articles(500)
    texts = [clean_text(a) for a in articles]
    
    # 1. Baseline: Sentence Transformers
    print("\n--- Baseline: all-MiniLM-L6-v2 ---")
    st_t0 = time.time()
    model = SentenceTransformer('all-MiniLM-L6-v2')
    st_vectors = model.encode(texts, convert_to_numpy=True)
    st_t1 = time.time()
    st_clusters = cluster_vectors(st_vectors, 0.70)
    print(f"ST Encode Time: {st_t1 - st_t0:.2f}s")
    print(f"ST Output: {len(st_clusters)} clusters formed from {len(articles)} articles.")
    
    # 2. Evaluation: OpenAI text-embedding-3-small
    print("\n--- Evaluation: OpenAI text-embedding-3-small ---")
    oa_t0 = time.time()
    oa_vectors = await get_openai_embeddings(texts)
    oa_t1 = time.time()
    # OpenAI vectors are deeper so threshold usually behaves differently (0.75-0.80 range)
    oa_clusters = cluster_vectors(oa_vectors, 0.75) 
    print(f"OpenAI Encode Time: {oa_t1 - oa_t0:.2f}s")
    print(f"OpenAI Output: {len(oa_clusters)} clusters formed from {len(articles)} articles.")
    
    # 3. Test the Qdrant connection using the new OpenAI vectors
    run_qdrant_test(articles, oa_vectors)
    
if __name__ == "__main__":
    asyncio.run(main())
