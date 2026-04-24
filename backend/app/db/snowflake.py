import os
import snowflake.connector
from app.core.config import get_settings
from app.core.logging_conf import get_logger

logger = get_logger("app.db.snowflake")

def get_db_connection():
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

    settings = get_settings()
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql")
    
    if not os.path.exists(schema_path):
        logger.warning("Master schema.sql not found. Skipping auto-sync.", path=schema_path)
        return

    try:
        with open(schema_path, "r") as f:
            sql_content = f.read()
            
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
                
        conn.close()
        logger.info("Database schema synchronization successfully verified.")
        
    except Exception as e:
        logger.error("Critical failure during database auto-sync", error=str(e))