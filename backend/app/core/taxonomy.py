from typing import Dict

# Taxonomy mapping Axiomatic Keywords to Multi-Label Weights
AXIOMATIC_TAXONOMY: Dict[str, Dict[str, float]] = {
    "llm": {"llms": 0.9, "general_ai": 0.6},
    "openai": {"llms": 1.0, "general_ai": 0.5},
    "claude": {"llms": 1.0, "general_ai": 0.4},
    "anthropic": {"llms": 1.0, "general_ai": 0.4},
    "gpt-4": {"llms": 1.0},
    "llama": {"llms": 1.0},
    "gemini": {"llms": 1.0},
    "mistral": {"llms": 1.0},
    "genai": {"llms": 0.5, "general_ai": 0.9},
    "sora": {"llms": 0.6, "computer_vision": 0.9},
    
    "vulnerability": {"security": 1.0},
    "exploit": {"security": 1.0},
    "breach": {"security": 1.0},
    "cybersecurity": {"security": 1.0},
    "malware": {"security": 1.0},
    
    "hardware": {"hardware": 1.0},
    "nvidia": {"hardware": 1.0, "llms": 0.2},
    "h100": {"hardware": 1.0},
    "gpu": {"hardware": 1.0},
    "tsmc": {"hardware": 1.0},
    "intel": {"hardware": 1.0},
    "amd": {"hardware": 1.0},
    
    "founding": {"startups": 1.0},
    "valuation": {"startups": 1.0},
    "series a": {"startups": 1.0},
    "series b": {"startups": 1.0},
    "startup": {"startups": 1.0},
    "venture capital": {"startups": 1.0},
    "acquisition": {"startups": 1.0},
    
    "github": {"software_engineering": 0.9},
    "open source": {"software_engineering": 0.8},
    "api": {"software_engineering": 0.8},
    "framework": {"software_engineering": 0.7},
    "react": {"software_engineering": 1.0},
    "rust": {"software_engineering": 1.0},
    "python": {"software_engineering": 0.9},
    
    "policy": {"ai_policy": 0.9},
    "regulation": {"ai_policy": 0.9},
    "senate": {"ai_policy": 0.8},
    "eu ai act": {"ai_policy": 1.0},
    
    "agent": {"ai_agents": 1.0},
    "autonomous": {"ai_agents": 0.6, "robotics": 0.4},
    
    "database": {"data_engineering": 1.0},
    "pipeline": {"data_engineering": 0.8},
    "snowflake": {"data_engineering": 1.0},
    "big data": {"data_engineering": 0.9}
}

def get_axiomatic_weights(text: str) -> Dict[str, float]:
    """
    Scans text for axiomatic keywords and returns aggregated weights.
    """
    clean_text = text.lower()
    final_weights = {}
    
    for kw, weights in AXIOMATIC_TAXONOMY.items():
        if kw in clean_text:
            for cat, val in weights.items():
                # We take the max if multiple keywords hit the same category
                final_weights[cat] = max(final_weights.get(cat, 0.0), val)
                
    return final_weights
