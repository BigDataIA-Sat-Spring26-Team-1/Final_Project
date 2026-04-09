import re
import numpy as np
from urllib.parse import urlparse
from typing import List, Dict, Any
from app.core.logging_conf import get_logger
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = get_logger("app.services.deduplication")

class DeduplicationService:
    """
    Dual-layer deduplication engine:
    1. Exact URL normalization & matching
    2. Semantic title similarity clustering using Sentence Transformers
    """
    
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            logger.info("Loading SentenceTransformer model (all-MiniLM-L6-v2)")
            cls._model = SentenceTransformer('all-MiniLM-L6-v2')
        return cls._model

    @staticmethod
    def normalize_url(url: str) -> str:
        """Standardizes URLs to catch matches across versions (www, trailing slash, tracking params)."""
        if not url: return ""
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."): netloc = netloc[4:]
            path = parsed.path.rstrip('/')
            # We ignore query params for now as most news sites use them for tracking,
            # but keep an eye out for sites using query params for actual routing.
            return f"{netloc}{path}"
        except:
            return url

    SIMILARITY_THRESHOLD = 0.70

    @classmethod
    def process_batch(cls, articles: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Orchestrates the deduplication pipeline on a batch of raw articles.

        Performs dual-layer matching:
        1. Exact URL normalization and grouping.
        2. Semantic group clustering using Sentence Transformer embeddings.

        Args:
            articles: List of unclustered raw article dictionaries.

        Returns:
            List[List[Dict]]: A list of clusters, where each cluster is a list of articles.
        """
        if not articles:
            return []

        logger.info("Starting deduplication batch", count=len(articles))

        # Phase 1: URL-based Grouping
        url_groups: Dict[str, List[Dict[str, Any]]] = {}
        for art in articles:
            norm_url = cls.normalize_url(art.get('url', ''))
            url_groups.setdefault(norm_url, []).append(art)
        
        # Collapse URL groups into representative items for semantic phase
        url_uniques = []
        for cluster in url_groups.values():
            representative = cluster[0].copy()
            representative['_all_ids'] = [c['id'] for c in cluster]
            representative['_all_sources'] = list(set([c['source_name'] for c in cluster]))
            url_uniques.append(representative)

        logger.info("URL deduplication complete", raw_total=len(articles), unique_url_count=len(url_uniques))

        if len(url_uniques) <= 1:
            return [[u] for u in url_uniques]

        # Phase 2: Semantic Clustering on Titles + Summaries
        model = cls.get_model()
        
        # Prototype cleaning logic: lowercase + no punctuation for better matching
        clean_sentences = []
        for art in url_uniques:
            text = f"{art.get('title', '')} {art.get('summary', '')}".strip()
            clean_text = re.sub(r'[^\w\s]', '', text.lower())
            clean_sentences.append(clean_text)
        
        logger.info("Starting semantic clustering", vector_count=len(clean_sentences))
        embeddings = model.encode(clean_sentences, convert_to_numpy=True)
        sim_matrix = cosine_similarity(embeddings)
        
        clusters = []
        visited = set()
        
        for i in range(len(url_uniques)):
            if i in visited:
                continue
            
            # Find all indices with similarity > threshold
            similar_indices = np.where(sim_matrix[i] >= cls.SIMILARITY_THRESHOLD)[0]
            
            current_cluster = []
            for idx in similar_indices:
                if idx not in visited:
                    current_cluster.append(url_uniques[idx])
                    visited.add(idx)
            
            if current_cluster:
                clusters.append(current_cluster)

        logger.info("Synthesis complete: Clusters formed in memory", cluster_count=len(clusters))
        return clusters

    @classmethod
    def synthesize_story(cls, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesizes a representative Story object from a cluster of raw articles.

        Args:
            cluster: A list of semantically similar article dictionaries.

        Returns:
            Dict: A synthesized story dictionary ready for repository persistence.
        """
        # Pick representative (usually the first one from highest priority source)
        representative = cluster[0]
        
        # Aggregate all raw article IDs and sources represented by this cluster
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
