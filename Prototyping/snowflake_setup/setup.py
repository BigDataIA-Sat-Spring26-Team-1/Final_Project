import os
import sys
import snowflake.connector
from dotenv import load_dotenv

# Load environment variables from the root .env file
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
env_path = os.path.join(root_dir, '.env')

if not os.path.exists(env_path):
    print(f"Error: Could not find .env file at {env_path}")
    sys.exit(1)

load_dotenv(env_path)

def initialize_database():
    """
    Connects to Snowflake and runs the schema.sql to initialize our tables.
    """
    print("Connecting to Snowflake...")
    try:
        conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
            database=os.getenv('SNOWFLAKE_DATABASE'),
            schema=os.getenv('SNOWFLAKE_SCHEMA'),
            role=os.getenv('SNOWFLAKE_ROLE')
        )
        
        cursor = conn.cursor()
        print("Successfully connected. Reading schema file...")
        
        # Determine the path to the schema file
        schema_path = os.path.join(root_dir, 'backend', 'app', 'database', 'schema.sql')
        
        with open(schema_path, 'r') as file:
            sql_script = file.read()
            
        print("Executing schema setup queries...")
        
        # Split script appropriately and execute one by one
        # Snowflake Connector handles single commands sequentially much safer
        statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
        
        for statement in statements:
            if not statement or statement.startswith('--') and '\n' not in statement:
                continue
            
            print(f"Running: {statement[:60]}...")
            cursor.execute(statement)
            
        print("\nSUCCESS: All schemas and tables initialized in Snowflake!")
        
    except Exception as e:
        print(f"An error occurred during Snowflake execution: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    initialize_database()
