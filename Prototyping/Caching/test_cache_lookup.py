# ==========================================
# Phase 4 Prototype: Cache Lookup Logic
# ==========================================
# Simulates Task 17: Blocking dual-invocations.
# Simulates Task 16: Decorator logic flow.

import time

# Simulation of In-Memory Cache (Global scope)
INTERNAL_CACHE = {}

def mock_langgraph_execution(archetype: str):
    """Simulates an expensive 10-second LangGraph/LLM call."""
    print(f"   [LLM ENGINE] Generating unique newsletter for {archetype}...")
    time.sleep(2) # Simulated delay
    return f"<html><body>Content for {archetype}</body></html>"

def get_newsletter_with_cache(user_id: str, archetype: str):
    """
    Simulates the logic inside the @cached_newsletter decorator.
    """
    date_key = "2026-04-16"
    cache_key = f"{archetype}_{date_key}"
    
    print(f"Request from {user_id} ({archetype})")
    
    # Task 17: Lookup Logic
    if cache_key in INTERNAL_CACHE:
        print(f"   [CACHE HIT] Returning stored content for {cache_key} (0ms latency)")
        return INTERNAL_CACHE[cache_key], "CACHE"
    
    # Cold start
    print(f"   [CACHE MISS] No entry for {cache_key}. Triggering LangGraph...")
    content = mock_langgraph_execution(archetype)
    INTERNAL_CACHE[cache_key] = content
    return content, "LLM"

def main():
    print("--- Simulating Multi-User Traffic (Archetype: DATA_ENGINEER) ---")
    
    # Scenario: 3 users of the same archetype visit the app
    traffic = [
        ("user_A", "DATA_ENGINEER"),
        ("user_B", "DATA_ENGINEER"),
        ("user_C", "DATA_ENGINEER")
    ]
    
    for uid, arch in traffic:
        _, source = get_newsletter_with_cache(uid, arch)
        print(f"Result Source: {source}\n")

if __name__ == "__main__":
    main()
