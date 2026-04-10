import asyncio
import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.b2c_agent import get_b2c_newsletter_graph
from app.services.b2b_agent import get_b2b_report_graph

async def verify_graphs():
    print("Starting scaffold verification...")
    
    try:
        print("Checking B2C Newsletter Graph...")
        b2c_graph = get_b2c_newsletter_graph()
        print("B2C Graph Compiled Successfully")
        
        # Test dry run
        print("Executing B2C Dry Run...")
        result = await b2c_graph.ainvoke({"user_id": "test_user_123", "messages": []})
        print(f"B2C Execution Successful. Status: {result.get('status')}")
        
    except Exception as e:
        print(f"B2C Graph Failed: {str(e)}")
        return False

    try:
        print("\nChecking B2B Intelligence Graph...")
        b2b_graph = get_b2b_report_graph()
        print("B2B Graph Compiled Successfully")
        
        # Test dry run
        print("Executing B2B Dry Run...")
        result = await b2b_graph.ainvoke({"user_id": "test_b2b_456", "messages": []})
        print(f"B2B Execution Successful. Status: {result.get('status')}")
        
    except Exception as e:
        print(f"B2B Graph Failed: {str(e)}")
        return False

    print("\n All scaffolds are verified and ready for the team!")
    return True

if __name__ == "__main__":
    asyncio.run(verify_graphs())
