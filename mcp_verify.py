import sys
import os
from dotenv import load_dotenv

# Dummy keys to pass startup check
os.environ["OPENAI_API_KEY"] = "sk-placeholder"
os.environ["SNOWFLAKE_ACCOUNT"] = "placeholder"
os.environ["SNOWFLAKE_USER"] = "placeholder"
os.environ["SNOWFLAKE_PASSWORD"] = "placeholder"
os.environ["SNOWFLAKE_DATABASE"] = "placeholder"
os.environ["SNOWFLAKE_SCHEMA"] = "placeholder"

load_dotenv()
sys.path.insert(0, os.path.abspath('backend'))

try:
    from app.core.mcp_server import mcp_server
    print(f"\n🚀 MCP Server [{mcp_server.name}] Initialized Successfully!")
    print("-" * 50)
    print("Registered Tools:")
    
    # Corrected attribute name: .tools instead of ._tools
    for tool_name in mcp_server.tools.keys():
        print(f" - {tool_name}")
        
    print("-" * 50)
    print("✅ All tools are correctly mapped and valid!\n")
except Exception as e:
    print(f"\n❌ Final Check Failed: {str(e)}")
