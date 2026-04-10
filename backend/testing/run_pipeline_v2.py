import httpx
import asyncio

BASE_URL = "http://127.0.0.1:8015/api/v1"

async def run_full_pipeline():
    print("STARTING CURATE-AI END-TO-END PIPELINE V2")
    async with httpx.AsyncClient(timeout=300.0) as client:
        
        # 1. Deduplication (Semantic Clustering)
        print("\n[STEP 1]: Clustering articles...")
        try:
            resp = await client.post(f"{BASE_URL}/deduplication/process")
            print(f"  Status: {resp.status_code}")
            print(f"  Response: {resp.json()}")
        except Exception as e:
            print(f"  Dedupe error: {e}")
            
        # 2. Trend Ranking
        print("\n[STEP 2]: Ranking daily clusters...")
        try:
            resp = await client.post(f"{BASE_URL}/trend/rank")
            print(f"  Status: {resp.status_code}")
            print(f"  Response: {resp.json()}")
        except Exception as e:
            print(f"  Trend error: {e}")

    print("\n" + "="*50)
    print("PIPELINE RUN COMPLETE")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(run_full_pipeline())
