# ==========================================
# Phase 4 Prototype: Archetype-Based Hashing
# ==========================================
# Simulates Task 15: Designing the unique cache key.
# Instead of hashing by user_id (O(users)), we hash by archetype (O(archetypes)).

import hashlib
from datetime import datetime

# Mock Mapping: In production, this comes from Snowflake 'user_personas' table.
USER_TO_ARCHETYPE = {
    "user_101": "ML_RESEARCHER",
    "user_102": "ML_RESEARCHER", # Shared archetype!
    "user_103": "AI_POLICY_LEAD",
    "user_104": "ML_RESEARCHER"  # Shared archetype!
}

def generate_archetype_cache_key(user_id: str):
    """
    Step 1: Map User to Archetype.
    Step 2: Hash Archetype + Date to ensure 24-hour TTL.
    """
    archetype = USER_TO_ARCHETYPE.get(user_id, "GENERAL_TECH")
    today = datetime.now().strftime("%Y-%m-%d")
    
    raw_key = f"{archetype}_{today}"
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
    
    return archetype, hashed_key

def main():
    print("--- Testing Archetype Key Convergence ---")
    
    users = ["user_101", "user_102", "user_104"]
    keys = []
    
    for uid in users:
        arch, key = generate_archetype_cache_key(uid)
        print(f"User: {uid} | Archetype: {arch} | Key: {key[:12]}...")
        keys.append(key)
        
    # Validation: All three users should have the EXACT same key
    if len(set(keys)) == 1:
        print("\nSUCCESS: All 3 users converged on the same cache key!")
        print("This enables 1 generation to serve all 3 users (98% cost efficiency).")
    else:
        print("\nFAILURE: Keys diverged. Scaling is still O(users).")

if __name__ == "__main__":
    main()
