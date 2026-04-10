import json
from app.db.snowflake import get_db_connection

def verify():
    print("Fetching Classified Article Snapshot from Snowflake...")
    try:
        db_gen = get_db_connection()
        conn = next(db_gen)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT title, internal_category_weights 
            FROM articles_raw 
            WHERE internal_category_weights IS NOT NULL 
            ORDER BY fetched_at DESC 
            LIMIT 5
        """)
        
        rows = cur.fetchall()
        if not rows:
            print("No classified articles found in DB.")
            return

        for title, weights_json in rows:
            print(f"\n[ARTICLE]: {title}")
            # Weights might be already a dict or a JSON string depending on connector settings
            weights = json.loads(weights_json) if isinstance(weights_json, str) else weights_json
            
            # Filter for non-zero weights only to see the 'Highlights'
            highlights = {k: v for k, v in weights.items() if v > 0}
            print(f"Intelligence Highlights: {highlights}")
            
    except Exception as e:
        print(f"Verification Failed: {e}")
    finally:
        # Note: In a real app we'd close the generator properly
        pass

if __name__ == "__main__":
    verify()
