# ==========================================
# Prototyping Sandbox: Fast Mode Routing
# ==========================================
# This script simulates Phase 3 (Tasks 11-12) locally.
# It proves that when execution_mode="fast" is provided,
# the LangGraph bypasses the Editor/Fact-Checker entirely.
# No real OpenAI tokens are consumed.

from typing import TypedDict, List
from langgraph.graph import StateGraph, END
import time

# 1. Update LangGraph AgentState schema (Task 11 Prototype)
class BranchingAgentState(TypedDict):
    execution_mode: str
    generated_content: str
    execution_path_taken: List[str]

# 2. Define Mocked Nodes
def mock_writer_node(state: BranchingAgentState):
    print("Executing [Writer Module] -> Drafting content...")
    new_path = state.get("execution_path_taken", []) + ["writer"]
    return {"generated_content": "Drafted Newsletter Data", "execution_path_taken": new_path}

def mock_editor_node(state: BranchingAgentState):
    print("Executing [Editor Module] -> Fact checking... (YOU SHOULD NOT SEE THIS IN FAST MODE!)")
    new_path = state.get("execution_path_taken", []) + ["editor_review"]
    return {"execution_path_taken": new_path}

# 3. Build 'Fast' mode routing logic (Task 12 Prototype)
def route_execution_mode(state: BranchingAgentState) -> str:
    """The vital conditional brain that splits the graph based on user request."""
    print(f"Routing Condition Hit -> Mode requested: '{state['execution_mode']}'")
    if state["execution_mode"] == "fast":
        print(">> Bypassing Editor completely to save tokens/latency.")
        return "fast_lane"
    
    print(">> Pushing to strictly enforced Editor review loops.")
    return "polished_lane"

def main():
    print("--- Booting up Fast Mode Prototype ---")
    
    # 4. Compile the Graph Architecture
    workflow = StateGraph(BranchingAgentState)
    workflow.add_node("writer", mock_writer_node)
    workflow.add_node("editor_review", mock_editor_node)
    
    workflow.set_entry_point("writer")
    
    # Inject Conditional Edge!
    workflow.add_conditional_edges(
        "writer",
        route_execution_mode,
        {
            "fast_lane": END,
            "polished_lane": "editor_review"
        }
    )
    workflow.add_edge("editor_review", END)
    
    graph = workflow.compile()
    
    # 5. Invoke graph with FAST routing
    # No real API hits happen here.
    initial_state = {
        "execution_mode": "fast", 
        "execution_path_taken": []
    }
    
    final_state = graph.invoke(initial_state)
    
    print("\n--- Execution Complete ---")
    print(f"Actual Traversed Path: {final_state['execution_path_taken']}")
    
    # Assertion check logic proving it skipped the editor!
    assert "editor_review" not in final_state["execution_path_taken"], "ERROR: Editor was illegally run in Fast mode!"
    print("SUCCESS: Graph correctly ended immediately after writer in Fast mode!")

if __name__ == "__main__":
    main()
