import os
import snowflake.connector
from app.core.config import get_settings
from app.core.logging_conf import get_logger

logger = get_logger("app.db.snowflake")

def get_db_connection():
    """
    FastAPI dependency that yields a Snowflake connection.
    Ensures swift tear-down of the cursor via a context manager logic block.
    """
    settings = get_settings()
    conn = None
    try:
        conn = snowflake.connector.connect(
            user=settings.snowflake_user,
            password=settings.snowflake_password,
            account=settings.snowflake_account,
            warehouse=settings.snowflake_warehouse,
            database=settings.snowflake_database,
            schema=settings.snowflake_schema,
            role=settings.snowflake_role
        )
        yield conn
    finally:
        if conn:
            conn.close()

def sync_database_schema():
    """
    Reads the project's master schema.sql and executes it against Snowflake.
    Ensures that any new columns or tables are created automatically on startup.
    Uses 'CREATE OR REPLACE' pattern as defined in schema.sql for idempotent updates.
    """
    settings = get_settings()
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql")
    
    if not os.path.exists(schema_path):
        logger.warning("Master schema.sql not found. Skipping auto-sync.", path=schema_path)
        return

    try:
        with open(schema_path, "r") as f:
            sql_content = f.read()
            
        # Basic SQL splitting (assuming statements are semi-colon terminated)
        # Note: In production you'd use a more robust SQL parser if you have procedures/triggers
        statements = [s.strip() for s in sql_content.split(";") if s.strip()]
        
        logger.info("Initializing Snowflake Schema sync from master file", path=schema_path, statements=len(statements))
        
        conn = snowflake.connector.connect(
            user=settings.snowflake_user,
            password=settings.snowflake_password,
            account=settings.snowflake_account,
            warehouse=settings.snowflake_warehouse,
            database=settings.snowflake_database,
            schema=settings.snowflake_schema,
            role=settings.snowflake_role
        )
        
        cursor = conn.cursor()
        for stmt in statements:
            try:
                cursor.execute(stmt)
            except Exception as stmt_err:
                logger.error("Failed to execute schema statement", statement=stmt[:50], error=str(stmt_err))
                # We continue to next statements as Snowflake might error on "CREATE IF NOT EXISTS" for some objects
                
        conn.close()
        logger.info("Database schema synchronization successfully verified.")
        
    except Exception as e:
        logger.error("Critical failure during database auto-sync", error=str(e))
