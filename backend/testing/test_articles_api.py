import uuid
import asyncio
from app.db.snowflake import get_db_connection
from app.services.article_service import ArticleOrchestratorService

async def test_p2():
    print("P2: Article Classification Integration Test")
    
    try:
        db_gen = get_db_connection()
        conn = next(db_gen)
        cur = conn.cursor()
        
        # 1. Ensure we have at least one test article
        cur.execute("SELECT id FROM articles_raw LIMIT 1")
        if not cur.fetchone():
            print("Inserting dummy article for P2 test...")
            dummy_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO articles_raw (id, source_name, title, summary, url, extracted_full_text)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                dummy_id,
                "The Verge",
                "DeepMind announces a new AI agent called AlphaStar",
                "AlphaStar is a new AI agent that can play StarCraft II at a grandmaster level.",
                "https://theverge.com/ai/alphastar",
                "AlphaStar uses a multi-agent reinforcement learning algorithm... It trained for 200 years of real-time play... It beat TLO and MaNa."
            ))
        
        # 2. Trigger Batch Classification
        print("Running Article Orchestrator...")
        stats = await ArticleOrchestratorService.classify_pending_articles(conn, batch_size=5)
        print(f"Processed {stats.get('success', 0)}/{stats.get('total', 0)} articles.")
        
        # 3. Verify
        cur.execute("SELECT title, internal_category_weights FROM articles_raw WHERE internal_category_weights IS NOT NULL LIMIT 1")
        row = cur.fetchone()
        if row:
            print(f"Classification Verified for Article: {row[0]}")
            print(f"Weights: {row[1]}")
        else:
            print("No classified articles found in DB.")
            
    except Exception as e:
        print(f"P2 Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_p2())
