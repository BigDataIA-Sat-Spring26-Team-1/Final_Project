import re
import numpy as np
from urllib.parse import urlparse
from typing import List, Dict, Any
import asyncio

from litellm import aembedding
from sklearn.metrics.pairwise import cosine_similarity
from qdrant_client.models import PointStruct

from app.core.config import get_settings
from app.core.logging_conf import get_logger
from app.db.qdrant import get_qdrant_client

logger = get_logger("app.services.deduplication")
settings = get_settings()

class DeduplicationService:
    """Dual-layer deduplication engine that groups overlapping news stories.
    
    Uses URL matching for exact duplicates and OpenAI structural embeddings 
    for semantic overlap mapping. Also pushes points to Qdrant.
    """
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Removes tracking and non-essential routing segments from URLs."""
        if not url: 
            return ""
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            path = parsed.path.rstrip('/')
            return f"{netloc}{path}"
        except Exception as e:
            logger.warning("URL normalization failed", url=url, error=str(e))
            return url

    @classmethod
    async def get_embeddings(cls, texts: List[str]) -> np.ndarray:
        """
        Fetches asynchronous vector embeddings using LiteLLM standard.
        Batches requests into chunks of 100 to prevent API timeouts.
        
        Args:
            texts: A list of clean summary/title text blobs.
        Returns:
            A NumPy array of multi-dimensional vector embeddings.
        """
        logger.info("Fetching OpenAI embeddings", model=settings.embedding_model, count=len(texts))
        
        embeddings = []
        chunk_size = 100
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i:i+chunk_size]
            response = await aembedding(
                model=settings.embedding_model, 
                input=chunk,
                api_key=settings.openai_api_key
            )
            for item in response['data']:
                embeddings.append(item['embedding'])
        return np.array(embeddings)

    @classmethod
    async def process_batch(cls, articles: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Runs the semantic clustering pipeline on a batch of unclustered articles.
        
        Args:
            articles: A list of raw article dictionaries fetched from the database.
            
        Returns:
            A list of clusters, where each cluster is a list of article dictionaries
            that share structural or semantic similarity.
            
        Process flow:
        1. Collapse structurally identical articles (exact URL match).
        2. Generate vector embeddings for the unique articles using OpenAI.
        3. Form clusters using a Cosine Similarity distance metric threshold.
        4. Ingest the newly calculated vectors into Qdrant for routing/search.
        """
        if not articles:
            return []

        logger.info("Starting deduplication batch", count=len(articles))

        # 1. URL Grouping (collapse exact duplicates)
        url_groups: Dict[str, List[Dict[str, Any]]] = {}
        for art in articles:
            norm_url = cls.normalize_url(art.get('url', ''))
            url_groups.setdefault(norm_url, []).append(art)
        
        url_uniques = []
        for cluster in url_groups.values():
            representative = cluster[0].copy()
            representative['_all_ids'] = [c['id'] for c in cluster]
            representative['_all_sources'] = list(set([c.get('source_name', 'Unknown') for c in cluster]))
            url_uniques.append(representative)

        logger.info("Structural deduplication complete", raw_total=len(articles), unique_url_count=len(url_uniques))

        if len(url_uniques) <= 1:
            return [[u] for u in url_uniques]

        # 2. Semantic Clustering
        clean_sentences = []
        for art in url_uniques:
            text = f"{art.get('title', '')} {art.get('summary', '')}".strip()
            # Basic clean without removing meaning
            clean_text = re.sub(r'[^\w\s]', '', text.lower())
            clean_sentences.append(clean_text)
            
        embeddings = await cls.get_embeddings(clean_sentences)
        sim_matrix = cosine_similarity(embeddings)
        
        clusters = []
        visited = set()
        
        for i in range(len(url_uniques)):
            if i in visited:
                continue
            
            similar_indices = np.where(sim_matrix[i] >= settings.deduplication_threshold)[0]
            
            current_cluster = []
            for idx in similar_indices:
                if idx not in visited:
                    # Keep the embedding with the article for Qdrant insertion later if needed
                    url_uniques[idx]['_embedding'] = embeddings[idx].tolist()
                    current_cluster.append(url_uniques[idx])
                    visited.add(idx)
            
            if current_cluster:
                clusters.append(current_cluster)

        logger.info("Semantic clustering formed", cluster_count=len(clusters))
        
        # 3. Optional: Insert clusters/representatives directly into Qdrant for routing
        # Background indexing logic
        try:
            client = get_qdrant_client()
            points = []
            for cluster in clusters:
                rep = cluster[0]
                points.append(PointStruct(
                    # Using the first article's ID as the vector ID. Convert to UUID if necessary.
                    id=str(rep['id']),
                    vector=rep['_embedding'],
                    payload={
                        "title": rep.get('title', ''),
                        "sources": rep.get('_all_sources', []),
                        "cluster_size": len(cluster)
                    }
                ))
            if points:
                client.upsert(collection_name="articles", points=points)
                logger.info("Ingested cluster representatives into Qdrant", points=len(points))
        except Exception as e:
            logger.error("Failed to index clusters in Qdrant", error=str(e))

        return clusters

    @classmethod
    def synthesize_story(cls, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Creates a single cohesive story object that represents a group of identically 
        themed articles.
        
        Args:
            cluster: A list of matched articles forming a singular news event.
            
        Returns:
            A consolidated object representing the cluster, complete with aggregated IDs,
            source overlap tags, and the primary content extracted from the representative.
        """
        representative = cluster[0]
        
        all_ids = []
        all_sources = set()
        for item in cluster:
            all_ids.extend(item.get('_all_ids', [item['id']]))
            all_sources.update(item.get('_all_sources', [item.get('source_name', 'Unknown')]))

        return {
            "primary_title": representative.get('title', ''),
            "primary_summary": representative.get('summary', ''),
            "cluster_size": len(all_ids),
            "trend_status": "TRENDING" if len(all_sources) > 1 else "NEW",
            "article_ids": all_ids,
            "sources": list(all_sources)
        }
