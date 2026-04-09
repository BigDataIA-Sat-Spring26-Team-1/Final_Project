# Standard taxonomy for CurateAI Intelligence
TAXONOMY_CATEGORIES = [
    "LLMs", "AI Agents", "Computer Vision", "Security", "Hardware",
    "Software Engineering", "AI Policy", "General AI", "Data Engineering", "Startups"
]

def get_persona_extraction_prompt(source_type: str, text: str) -> str:
    """
    Constructs the prompt for extracting structured professional profiles.
    Separated from logic to allow for easier iteration on instruction sets.
    """
    return f"""
    Analyze the following {source_type} and extract a structured professional profile.
    
    TAXONOMY REQUIRED (assign a relevance weight from 0.0 to 1.0 for each category):
    {', '.join(TAXONOMY_CATEGORIES)}
    
    IMPORTANT: 
    1. Only assign weights (>0.1) to categories that are genuinely reflected in the experience.
    2. The bio_summary should be professional and concise (exactly 2 sentences).
    3. Technical skills must be extracted as they appear in the text (don't hallucinate skills).

    DOCUMENT TEXT:
    {text[:12000]}
    """
