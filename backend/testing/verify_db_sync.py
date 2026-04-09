from app.db.snowflake import get_db_connection
import json

def verify():
    print("Verifying Snowflake Data Persistence...")
    try:
        # Get the connection from the generator
        db_gen = get_db_connection()
        conn = next(db_gen)
        
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, job_title, seniority, explicit_category_weights, bio_summary 
            FROM user_personas 
            WHERE user_id = 'test-user-123'
        """)
        row = cur.fetchone()
        
        if row:
            print(f" Data Found for User: {row[0]}")
            print(f"   Job Title: {row[1]}")
            print(f"   Seniority: {row[2]}")
            print(f"   Bio Length: {len(row[4]) if row[4] else 0} chars")
            
            # Category weights is a VARIANT (JSON)
            weights = json.loads(row[3]) if isinstance(row[3], str) else row[3]
            print(f"   Weights: {json.dumps(weights, indent=2)}")
        else:
            print("No matching persona found in Snowflake. Persistence failed.")
            
    except StopIteration:
        print("Could not obtain Snowflake connection.")
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    verify()
