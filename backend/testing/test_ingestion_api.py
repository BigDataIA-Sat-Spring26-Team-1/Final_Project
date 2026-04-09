import httpx
import asyncio

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8011" # Assuming the persistent terminal on 8011 is still running or we restart it
INGEST_URL = f"{BASE_URL}/api/v1/ingestion/fetch-rss"

async def test_rss_ingestion():
    print("Testing RSS Ingestion Hub (Endpoint 1)...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            print("Triggering ingestion for yesterday's content...")
            resp = await client.post(INGEST_URL)
            
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                result = resp.json()
                print("Ingestion Successful")
                print(f"   Status: {result['status']}")
                print(f"   Window: {result['start_time']} to {result['end_time']}")
                print(f"   Discovered: {result['total_found']} articles")
                print(f"   Saved to Snowflake: {result['saved_count']} new articles")
                print(f"   Latency: {result['processing_time_seconds']}s")
            else:
                print(f"Ingestion Failed: {resp.text}")
                
        except Exception as e:
            print(f"Request Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_rss_ingestion())
