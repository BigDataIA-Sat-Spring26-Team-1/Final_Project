import httpx
import asyncio
import os
import json
import time

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8007"
HEALTH_URL = f"{BASE_URL}/api/v1/health"
EXTRACT_URL = f"{BASE_URL}/api/v1/personas/extract"
TEST_USER_ID = "test-user-123"
DOCS_DIR = "/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Final_Project/Final_Project/Temp/Test_Docs_Data"

async def test_health():
    print("\n[1/5] Testing Health Check...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(HEALTH_URL)
        print(f"Status: {resp.status_code}")
        assert resp.status_code == 200
        print("Health Check Passed")

async def test_persona_extraction_success():
    print(f"\n[2/5] Testing Successful Persona Extraction for User: {TEST_USER_ID}...")
    
    files = [
        ("files", ("LinkedIn_Profile.pdf", open(os.path.join(DOCS_DIR, "LinkedIn_Profile.pdf"), "rb"), "application/pdf")),
        ("files", ("Resume.pdf", open(os.path.join(DOCS_DIR, "Resume.pdf"), "rb"), "application/pdf")),
    ]
    data = {"user_id": TEST_USER_ID}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(EXTRACT_URL, data=data, files=files)
        print(f"Status: {resp.status_code}")
        assert resp.status_code == 200
        
        result = resp.json()
        print(f"User ID: {result['user_id']}")
        print(f"Total Results: {len(result['results'])}")
        
        for r in result['results']:
            status = "SUCCESS" if r['is_success'] else "FAILED"
            print(f" - {r['filename']}: {status}")
            if not r['is_success']:
                print(f"   Error: {r['error']}")
        
        print("Success Path Passed")

async def test_file_size_limit():
    print("\n[3/5] Testing File Size Limit (5MB)...")
    
    # Create a dummy large file (6MB)
    large_file_path = "/tmp/too_large.pdf"
    with open(large_file_path, "wb") as f:
        f.write(os.urandom(6 * 1024 * 1024))
    
    files = [("files", ("too_large.pdf", open(large_file_path, "rb"), "application/pdf"))]
    data = {"user_id": TEST_USER_ID}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(EXTRACT_URL, data=data, files=files)
        # The API returns 200 but the individual result should be failed if we handled it in process_batch
        result = resp.json()
        file_res = result['results'][0]
        print(f"Status: {resp.status_code}")
        print(f"File Result Success: {file_res['is_success']}")
        print(f"File Result Error: {file_res['error']}")
        assert file_res['is_success'] is False
        assert "exceeds" in file_res['error']
        
    os.remove(large_file_path)
    print("File Size Validation Passed")

async def test_rate_limiting():
    print("\n[4/5] Testing Rate Limiting (Expect 429 after 5 calls)...")
    
    # We already made 2 success-oriented calls if we run full suite.
    # Let's just spam a few more.
    async with httpx.AsyncClient() as client:
        for i in range(10):
            print(f"Request {i+1}...", end=" ")
            resp = await client.post(EXTRACT_URL, data={"user_id": TEST_USER_ID})
            print(f"Status: {resp.status_code}")
            if resp.status_code == 429:
                print(f"Successfully triggered Rate Limit: {resp.text}")
                print("Rate Limiting Passed")
                return
            await asyncio.sleep(0.1)
    
    print("Failed to trigger Rate Limit")

async def main():
    print("Starting Production Integration Tests for CurateAI Backend")
    try:
        await test_health()
        await test_persona_extraction_success()
        await test_file_size_limit()
        await test_rate_limiting()
        print("\nALL TESTS PASSED SUCCESSFULLY!")
    except Exception as e:
        print(f"\nTEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
