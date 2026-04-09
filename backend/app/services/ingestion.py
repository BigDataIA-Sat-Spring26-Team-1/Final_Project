import httpx
import asyncio
import feedparser
import xml.etree.ElementTree as ET
from dateutil import parser as date_parser
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from app.core.sources import RSS_FEEDS
from app.core.logging_conf import get_logger

logger = get_logger("app.services.ingestion")

class IngestionService:
    """
    Unified ingestion engine that aggregates content from RSS, ArXiv API, and HackerNews API.
    Designed to scale to 3,000+ articles per daily run.
    """
    
    # ArXiv categories for high-volume technical discovery
    ARXIV_CATEGORIES = [
        "cs.AI", "cs.LG", "cs.CV", "cs.CL", "cs.NE", "cs.RO", "cs.DS", 
        "cs.SE", "cs.DB", "cs.IR", "cs.DC"
    ]
    
    @staticmethod
    def _get_yesterday_range() -> tuple[datetime, datetime]:
        """Calculates the 26-hour ingestion window to prevent coverage gaps.

        Returns:
            tuple[datetime, datetime]: (start_time, end_time) as UTC aware objects.
        """
        now = datetime.now(timezone.utc)
        # 26h window provides 2 hours of overlap with previous runs
        start = now - timedelta(hours=26)
        return start, now

    @classmethod
    async def fetch_all_sources(cls) -> List[Dict[str, Any]]:
        """Orchestrates all crawlers in parallel to maximize throughput.

        Returns:
            List[Dict]: Consolidated firehose of articles from all sources.
        """
        logger.info("Starting multi-source ingestion firehose")
        
        # Parallel execution of three different ingestion streams
        results = await asyncio.gather(
            cls.fetch_all_rss(),
            cls.fetch_arxiv_api(),
            cls.fetch_hn_api(),
            return_exceptions=True
        )
        
        # Unpack while filtering out potential task exceptions
        rss_articles = results[0] if not isinstance(results[0], Exception) else []
        arxiv_articles = results[1] if not isinstance(results[1], Exception) else []
        hn_articles = results[2] if not isinstance(results[2], Exception) else []
        
        consolidated = rss_articles + arxiv_articles + hn_articles
        
        logger.info("Ingestion firehose complete", 
                    total_count=len(consolidated), 
                    rss_count=len(rss_articles), 
                    arxiv_count=len(arxiv_articles), 
                    hn_count=len(hn_articles))
        return consolidated

    @classmethod
    async def fetch_all_rss(cls) -> List[Dict[str, Any]]:
        """Scrapes editorial RSS feeds defined in core/sources.py.

        Returns:
            List[Dict]: Filtered list of articles from editorial sources.
        """
        start_time, end_time = cls._get_yesterday_range()
        semaphore = asyncio.Semaphore(5)
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            tasks = [cls._fetch_single_rss(client, url, semaphore, start_time, end_time) for url in RSS_FEEDS]
            results = await asyncio.gather(*tasks)
            
        return [item for sublist in results for item in sublist if sublist]

    @classmethod
    async def _fetch_single_rss(cls, client: httpx.AsyncClient, url: str, 
                                semaphore: asyncio.Semaphore, 
                                start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Worker to fetch and parse a single RSS feed."""
        async with semaphore:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                feed = await asyncio.to_thread(feedparser.parse, resp.text)
                source_name = feed.feed.get("title", url.split("/")[2])
                articles = []
                
                for entry in feed.entries:
                    raw_date = entry.get("published", entry.get("updated", entry.get("pubDate")))
                    if not raw_date:
                        continue
                        
                    try:
                        dt = date_parser.parse(raw_date)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                            
                        if start_time <= dt <= end_time:
                            articles.append({
                                "source_name": source_name,
                                "source_url": url,
                                "title": entry.get("title", "Untitled").strip(),
                                "url": entry.get("link", "").strip(),
                                "summary": entry.get("summary", entry.get("description", "")).strip()[:1000],
                                "published_at": dt.isoformat(),
                                "author": entry.get("author", "Unknown"),
                                "tags": [t.get("term", "") for t in entry.get("tags", [])]
                            })
                    except Exception:
                        continue
                return articles
            except Exception as e:
                logger.warning("RSS fetch failed", url=url, error=str(e))
                return []

    @classmethod
    async def fetch_arxiv_api(cls) -> List[Dict[str, Any]]:
        """Queries the ArXiv API for the latest research papers across technical categories.

        Returns:
            List[Dict]: Filtered list of new ArXiv submissions.
        """
        start_time, end_time = cls._get_yesterday_range()
        articles = []
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            for cat in cls.ARXIV_CATEGORIES:
                url = f"https://export.arxiv.org/api/query?search_query=cat:{cat}&start=0&max_results=500&sortBy=submittedDate&sortOrder=descending"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        root = ET.fromstring(resp.text)
                        ns = {'atom': 'http://www.w3.org/2005/Atom'}
                        
                        feed_entries = root.findall('atom:entry', ns)
                        cat_count = 0
                        for entry in feed_entries:
                            published_tag = entry.find('atom:published', ns)
                            if published_tag is None:
                                continue
                            
                            dt = date_parser.parse(published_tag.text)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            
                            if start_time <= dt <= end_time:
                                title_tag = entry.find('atom:title', ns)
                                id_tag = entry.find('atom:id', ns)
                                summary_tag = entry.find('atom:summary', ns)
                                author_name_tag = entry.find('atom:author/atom:name', ns)
                                
                                articles.append({
                                    "source_name": f"ArXiv ({cat})",
                                    "source_url": url,
                                    "title": title_tag.text.strip() if title_tag is not None else "Untitled",
                                    "url": id_tag.text.strip() if id_tag is not None else "",
                                    "summary": summary_tag.text.strip()[:1000] if summary_tag is not None else "",
                                    "published_at": dt.isoformat(),
                                    "author": author_name_tag.text if author_name_tag is not None else "Unknown",
                                    "tags": [cat]
                                })
                                cat_count += 1
                        logger.info("ArXiv category crawl complete", cat=cat, matched=cat_count)
                    
                    await asyncio.sleep(1) # Respect ArXiv rate limits
                except Exception as e:
                    logger.error("ArXiv API failed", cat=cat, error=str(e))
                    
        return articles

    @classmethod
    async def fetch_hn_api(cls, limit: int = 500) -> List[Dict[str, Any]]:
        """Aggregates top stories from Hacker News.

        Returns:
            List[Dict]: Filtered list of HN stories within the timeframe.
        """
        start_time, end_time = cls._get_yesterday_range()
        articles = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
                resp.raise_for_status()
                ids = resp.json()[:limit]
                
                semaphore = asyncio.Semaphore(10)
                tasks = [cls._fetch_hn_item(client, sid, semaphore, start_time, end_time) for sid in ids]
                results = await asyncio.gather(*tasks)
                articles = [item for item in results if item is not None]
                
            except Exception as e:
                logger.error("HackerNews API failed", error=str(e))
                
        return articles

    @classmethod
    async def _fetch_hn_item(cls, client: httpx.AsyncClient, sid: int, 
                             semaphore: asyncio.Semaphore, 
                             start_time: datetime, end_time: datetime) -> Optional[Dict[str, Any]]:
        """Worker to fetch metadata for a single HN story."""
        async with semaphore:
            try:
                url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    if data and data.get("type") == "story":
                        dt = datetime.fromtimestamp(data.get("time", 0), tz=timezone.utc)
                        if start_time <= dt <= end_time:
                            return {
                                "source_name": "Hacker News",
                                "source_url": "https://news.ycombinator.com",
                                "title": data.get("title", "Untitled"),
                                "url": data.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                                "summary": data.get("text", "")[:1000],
                                "published_at": dt.isoformat(),
                                "author": data.get("by", "Unknown"),
                                "tags": ["hn", "tech-community"]
                            }
                return None
            except Exception:
                return None
