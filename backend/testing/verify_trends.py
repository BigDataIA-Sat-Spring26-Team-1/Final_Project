import snowflake.connector
from app.core.config import get_settings

def main():
    settings = get_settings()
    conn = snowflake.connector.connect(
        user=settings.snowflake_user,
        password=settings.snowflake_password,
        account=settings.snowflake_account,
        warehouse=settings.snowflake_warehouse,
        database=settings.snowflake_database,
        schema=settings.snowflake_schema,
        role=settings.snowflake_role
    )
    cur = conn.cursor()
    
    cur.execute("""
        SELECT trend_status, COUNT(*) as cnt, 
               ROUND(AVG(final_trend_score), 1) as avg_score
        FROM article_clusters 
        WHERE trend_status IS NOT NULL
        GROUP BY trend_status 
        ORDER BY avg_score DESC
    """)
    print("TREND STATUS REPORT")
    print("=" * 45)
    for row in cur.fetchall():
        print(f"  {row[0]:20s} | Count: {row[1]:4d} | Avg Score: {row[2]}")
    
    print()
    cur.execute("""
        SELECT primary_title, trend_status, final_trend_score, cluster_size
        FROM article_clusters 
        WHERE trend_status IS NOT NULL
        ORDER BY final_trend_score DESC 
        LIMIT 10
    """)
    print("TOP 10 STORIES")
    print("=" * 70)
    for i, row in enumerate(cur.fetchall()):
        print(f"  {i+1:2d}. [{row[1]}] Score: {row[2]}, Sources: {row[3]}")
        print(f"      {row[0][:75]}")
    
    conn.close()

if __name__ == "__main__":
    main()
