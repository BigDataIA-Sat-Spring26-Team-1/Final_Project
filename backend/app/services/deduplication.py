import re
import numpy as np
from urllib.parse import urlparse
from typing import List, Dict, Any

from app.core.logging_conf import get_logger
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = get_logger("app.services.deduplication")

class DeduplicationService:
    """Dual-layer deduplication engine that groups overlapping news stories.
    
    Uses URL matching for exact duplicates and SentenceTransformers 
    for semantic overlap mapping.
    """
    
    _model = None
    SIMILARITY_THRESHOLD = 0.70

    @classmethod
    def get_model(cls):
        if cls._model is None:
            logger.info("Loading semantic embedding model (all-MiniLM-L6-v2)")
            cls._model = SentenceTransformer('all-MiniLM-L6-v2')
        return cls._model

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
    def process_batch(cls, articles: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Runs the clustering pipeline on a batch of unclustered articles."""
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
            representative['_all_sources'] = list(set([c['source_name'] for c in cluster]))
            url_uniques.append(representative)

        logger.info("Structural deduplication complete", raw_total=len(articles), unique_url_count=len(url_uniques))

        if len(url_uniques) <= 1:
            return [[u] for u in url_uniques]

        # 2. Semantic Clustering
        model = cls.get_model()
        
        clean_sentences = []
        for art in url_uniques:
            text = f"{art.get('title', '')} {art.get('summary', '')}".strip()
            clean_text = re.sub(r'[^\w\s]', '', text.lower())
            clean_sentences.append(clean_text)
        
        logger.info("Generating embeddings for semantic grouping", count=len(clean_sentences))
        embeddings = model.encode(clean_sentences, convert_to_numpy=True)
        sim_matrix = cosine_similarity(embeddings)
        
        clusters = []
        visited = set()
        
        for i in range(len(url_uniques)):
            if i in visited:
                continue
            
            similar_indices = np.where(sim_matrix[i] >= cls.SIMILARITY_THRESHOLD)[0]
            
            current_cluster = []
            for idx in similar_indices:
                if idx not in visited:
                    current_cluster.append(url_uniques[idx])
                    visited.add(idx)
            
            if current_cluster:
                clusters.append(current_cluster)

        logger.info("Semantic clustering formed", cluster_count=len(clusters))
        return clusters

    @classmethod
    def synthesize_story(cls, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Creates a single cohesive story object that represents a group of articles."""
        representative = cluster[0]
        
        all_ids = []
        all_sources = set()
        for item in cluster:
            all_ids.extend(item.get('_all_ids', [item['id']]))
            all_sources.update(item.get('_all_sources', [item['source_name']]))

        return {
            "primary_title": representative['title'],
            "primary_summary": representative.get('summary', ''),
            "cluster_size": len(all_ids),
            "trend_status": "TRENDING" if len(all_sources) > 1 else "NEW",
            "article_ids": all_ids,
            "sources": list(all_sources)
        }
