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
    def _get_rolling_window():
        """Returns the start and end of the rolling 24-hour window in UTC."""
        now = datetime.now(timezone.utc)
        # Using a slightly larger window (26h) to ensure no overlap gaps during network jitter
        start = now - timedelta(hours=26)
        return start, now

    @classmethod
    async def fetch_all_sources(cls) -> List[Dict[str, Any]]:
        """
        Orchestrates all crawlers and returns a consolidated list of articles.
        """
        logger.info("Starting multi-source ingestion firehose")
        
        # Parallel execution of three different ingestion streams
        rss_task = cls.fetch_all_rss()
        arxiv_task = cls.fetch_arxiv_api()
        hn_task = cls.fetch_hn_api()
        
        results = await asyncio.gather(rss_task, arxiv_task, hn_task)
        
        rss_articles, arxiv_articles, hn_articles = results
        consolidated = rss_articles + arxiv_articles + hn_articles
        
        logger.info("Ingestion firehose complete", 
                    total=len(consolidated), 
                    rss=len(rss_articles), 
                    arxiv=len(arxiv_articles), 
                    hn=len(hn_articles))
        return consolidated

    @classmethod
    async def fetch_all_rss(cls) -> List[Dict[str, Any]]:
        """Fetches standard editorial RSS feeds."""
        start_time, end_time = cls._get_rolling_window()
        semaphore = asyncio.Semaphore(5)
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            tasks = [cls._fetch_single_rss(client, url, semaphore, start_time, end_time) for url in RSS_FEEDS]
            results = await asyncio.gather(*tasks)
            
        return [item for sublist in results for item in sublist]

    @classmethod
    async def _fetch_single_rss(cls, client, url, semaphore, start_time, end_time) -> List[Dict[str, Any]]:
        async with semaphore:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                feed = await asyncio.to_thread(feedparser.parse, resp.text)
                source_name = feed.feed.get("title", url.split("/")[2])
                articles = []
                
                for entry in feed.entries:
                    raw_date = entry.get("published", entry.get("updated", entry.get("pubDate")))
                    if not raw_date: continue
                    try:
                        dt = date_parser.parse(raw_date)
                        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
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
                    except: continue
                return articles
            except Exception as e:
                logger.warning("RSS fetch failed", url=url, error=str(e))
                return []

    @classmethod
    async def fetch_arxiv_api(cls) -> List[Dict[str, Any]]:
        """Hits the official ArXiv Search API for high-volume research."""
        start_time, end_time = cls._get_rolling_window()
        articles = []
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            for cat in cls.ARXIV_CATEGORIES:
                url = f"https://export.arxiv.org/api/query?search_query=cat:{cat}&start=0&max_results=500&sortBy=submittedDate&sortOrder=descending"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        root = ET.fromstring(resp.text)
                        # Atom namespace is the default for ArXiv API
                        ns = {'atom': 'http://www.w3.org/2005/Atom'}
                        
                        feed_entries = root.findall('atom:entry', ns)
                        logger.debug(f"ArXiv {cat} raw entries found", count=len(feed_entries))
                        
                        cat_count = 0
                        for entry in feed_entries:
                            published_tag = entry.find('atom:published', ns)
                            if published_tag is None: continue
                            
                            dt = date_parser.parse(published_tag.text)
                            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                            
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
                    
                    await asyncio.sleep(1) # ArXiv API rate limit courtesy
                except Exception as e:
                    logger.error("ArXiv API failed", cat=cat, error=str(e))
                    
        return articles

    @classmethod
    async def fetch_hn_api(cls, limit: int = 500) -> List[Dict[str, Any]]:
        """Fetches top stories via HackerNews Firebase API."""
        start_time, end_time = cls._get_rolling_window()
        articles = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # 1. Get top story IDs
                resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
                resp.raise_for_status()
                ids = resp.json()[:limit]
                
                # 2. Fetch details for each ID in parallel
                logger.debug("Fetching HN story details", count=len(ids))
                semaphore = asyncio.Semaphore(10)
                tasks = [cls._fetch_hn_item(client, sid, semaphore, start_time, end_time) for sid in ids]
                results = await asyncio.gather(*tasks)
                articles = [item for item in results if item is not None]
                
            except Exception as e:
                logger.error("HackerNews API failed", error=str(e))
                
        return articles

    @classmethod
    async def _fetch_hn_item(cls, client, sid, semaphore, start_time, end_time) -> Optional[Dict[str, Any]]:
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
            except:
                return None
