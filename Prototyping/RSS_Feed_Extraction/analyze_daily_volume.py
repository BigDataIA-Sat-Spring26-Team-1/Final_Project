import asyncio
import httpx
import feedparser
from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser
from collections import Counter
from app.core.sources import RSS_FEEDS

async def analyze_daily_volume():
    print("📈 Analyzing Multi-Day Ingestion Volume (Last 7 Days)...")
    
    results = Counter()
    total_raw = 0
    now = datetime.now(timezone.utc)
    
    # We look back 7 days to see daily averages
    days = [(now - timedelta(days=i)).date() for i in range(8)]
    
    semaphore = asyncio.Semaphore(10)
    
    async def fetch(url):
        nonlocal total_raw
        async with semaphore:
            try:
                async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                    resp = await client.get(url, headers={"User-Agent": "CurateAI-Volume-Scanner/1.0"})
                    feed = feedparser.parse(resp.text)
                    
                    for entry in feed.entries:
                        total_raw += 1
                        raw_date = entry.get("published", entry.get("updated", entry.get("pubDate", entry.get("dc_date"))))
                        if raw_date:
                            try:
                                dt = date_parser.parse(raw_date)
                                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                                results[dt.date()] += 1
                            except: pass
            except: pass

    tasks = [fetch(url) for url in RSS_FEEDS]
    await asyncio.gather(*tasks)
    
    print("\n" + "="*40)
    print("DAILY VOLUME REPORT (Aggregated RSS)")
    print("="*40)
    for day in sorted(days, reverse=True):
        count = results.get(day, 0)
        print(f" {day.isoformat()} : {count} articles")
    
    print("="*40)
    print(f"Total entries processed: {total_raw}")
    avg = sum([results.get(d, 0) for d in days[1:6]]) / 5 # Average across full work days
    print(f"Average Weekly Workday Volume: {avg:.1f} articles/day")

if __name__ == "__main__":
    asyncio.run(analyze_daily_volume())
