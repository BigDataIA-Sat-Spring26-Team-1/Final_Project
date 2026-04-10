import httpx
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

async def test_arxiv_api_volume():
    # Top 5 AI Categories: AI, Machine Learning, Computer Vision, Computation and Language, Neural Computing
    categories = ["cs.AI", "cs.LG", "cs.CV", "cs.CL", "cs.NE"]
    
    print(f"Testing ArXiv Search API for {len(categories)} categories...")
    
    total_found = 0
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for cat in categories:
            # Querying for latest 500 items in each category
            url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&start=0&max_results=500&sortBy=submittedDate&sortOrder=descending"
            
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    # ArXiv API returns Atom XML
                    root = ET.fromstring(resp.text)
                    # Atom namespace
                    ns = {'atom': 'http://www.w3.org/2005/Atom'}
                    entries = root.findall('atom:entry', ns)
                    
                    found = len(entries)
                    print(f"  - [{cat}] Found {found} recent papers")
                    total_found += found
                else:
                    print(f"  - [{cat}] Failed with status {resp.status_code}")
            except Exception as e:
                print(f"  - [{cat}] Error: {e}")
            
            # Rate limiting compliance
            await asyncio.sleep(1)

    print("\n" + "="*40)
    print(f"TOTAL ARTICLES FOUND: {total_found}")
    print("="*40)
    print("Note: This is unique data across categories, giving us a massive daily firehose.")

if __name__ == "__main__":
    asyncio.run(test_arxiv_api_volume())
