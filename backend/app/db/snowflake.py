import snowflake.connector
from app.core.config import get_settings

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
