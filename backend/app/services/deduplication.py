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

        if not articles:
            return []

        logger.info("Starting deduplication batch", count=len(articles))

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

        clean_sentences = []
        for art in url_uniques:
            text = f"{art.get('title', '')} {art.get('summary', '')}".strip()
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
                    url_uniques[idx]['_embedding'] = embeddings[idx].tolist()
                    current_cluster.append(url_uniques[idx])
                    visited.add(idx)
            
            if current_cluster:
                clusters.append(current_cluster)

        logger.info("Semantic clustering formed", cluster_count=len(clusters))
        
        try:
            client = get_qdrant_client()
            points = [
                PointStruct(
                    id=str(cluster[0]['id']),
                    vector=cluster[0]['_embedding'],
                    payload={
                        "title": cluster[0].get('title', ''),
                        "url": cluster[0].get('url', ''),
                        "summary": cluster[0].get('summary', ''),
                        "sources": cluster[0].get('_all_sources', []),
                        "cluster_size": len(cluster),
                        # Forward the taxonomy weights so the frontend's
                        # like/dislike signal multiplies against real per-
                        # article weights instead of {}.
                        "category_weights": cluster[0].get('internal_category_weights')
                            or cluster[0].get('category_weights')
                            or {},
                    },
                )
                for cluster in clusters
            ]
            batch_size = 500
            for i in range(0, len(points), batch_size):
                client.upsert(
                    collection_name="articles",
                    points=points[i : i + batch_size],
                )
            if points:
                logger.info("Ingested cluster representatives into Qdrant", points=len(points))
        except Exception as e:
            logger.error("Failed to index clusters in Qdrant", error=str(e))

        return clusters

    @classmethod
    def synthesize_story(cls, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
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