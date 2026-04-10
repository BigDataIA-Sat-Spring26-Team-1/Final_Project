import os
import time
from typing import List, Dict

import pdfplumber
from pypdf import PdfReader
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

# Initialize configured environment context
load_dotenv()
client = OpenAI()

class CategoryWeights(BaseModel):
    """Explicitly mapped category weights since OpenAI strict-mode forbids open Dict mapping."""
    llms: float = Field(description="Weight for LLMs (0.0 to 1.0)")
    ai_agents: float = Field(description="Weight for AI Agents (0.0 to 1.0)")
    computer_vision: float = Field(description="Weight for Computer Vision (0.0 to 1.0)")
    security: float = Field(description="Weight for Security (0.0 to 1.0)")
    hardware: float = Field(description="Weight for Hardware (0.0 to 1.0)")
    software_engineering: float = Field(description="Weight for Software Engineering (0.0 to 1.0)")
    ai_policy: float = Field(description="Weight for AI Policy (0.0 to 1.0)")
    general_ai: float = Field(description="Weight for General AI (0.0 to 1.0)")
    data_engineering: float = Field(description="Weight for Data Engineering (0.0 to 1.0)")
    startups: float = Field(description="Weight for Startups (0.0 to 1.0)")

class UserInterestProfile(BaseModel):
    """Structured representation of a user's professional background and interests."""
    name: str = Field(description="Full name of the user.")
    job_title: str = Field(description="Current or most recent job title.")
    seniority: str = Field(description="Estimated seniority level: entry, mid, senior, lead, executive.")
    primary_interests: List[str] = Field(description="List of primary professional interests or specializations.")
    technical_skills: List[str] = Field(description="List of hard technical skills extracted from the document.")
    bio_summary: str = Field(description="A 2-sentence professional bio summary suitable for semantic search and vector encoding.")
    category_weights: CategoryWeights

class DocumentExtractor:
    """Handles text extraction from PDF documents using benchmarking strategies."""
    
    @staticmethod
    def extract_with_pdfplumber(file_path: str) -> tuple[str, float]:
        start = time.time()
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as e:
            print(f"    [!] pdfplumber extraction failed: {e}")
        return text.strip(), time.time() - start

    @staticmethod
    def extract_with_pypdf(file_path: str) -> tuple[str, float]:
        start = time.time()
        text = ""
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            print(f"    [!] pypdf extraction failed: {e}")
        return text.strip(), time.time() - start

class PersonaAnalyzer:
    """Analyzes structured profile generation using LLM semantic parsing."""
    
    TAXONOMY = [
        "LLMs", "AI Agents", "Computer Vision", "Security", "Hardware",
        "Software Engineering", "AI Policy", "General AI", "Data Engineering", "Startups"
    ]
    
    @staticmethod
    def detect_document_type(text: str) -> str:
        """Heuristically determines the original format of the parsed text."""
        linkedin_markers = ["linkedin.com/", "Experience", "Top Skills", "About", "Education"]
        score = sum(1 for m in linkedin_markers if m.lower() in text.lower())
        return "LinkedIn PDF" if score >= 3 else "Resume"

    @classmethod
    def generate_profile(cls, text: str, source_type: str) -> UserInterestProfile:
        """Sends extracted text to OpenAI utilizing strictly-typed Pydantic model guarantees."""
        prompt = f"""
        Analyze the following {source_type} and extract a structured professional profile.
        
        TAXONOMY REQUIRED (assign a relevance weight from 0.0 to 1.0 for each category):
        {', '.join(cls.TAXONOMY)}
        
        DOCUMENT TEXT:
        {text[:10000]}
        """
        
        # Native OpenAI structured output parser (guarantees our Pydantic model)
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert technical intelligence extractor analyzing resumes and profiles."},
                {"role": "user", "content": prompt}
            ],
            response_format=UserInterestProfile
        )
        
        return response.choices[0].message.parsed

def extract_and_analyze(file_path: str, label: str):
    """Orchestrates the extraction, benchmarking, and analysis pipeline for a specified document."""
    print(f"\n--- Processing {label} ---")
    if not os.path.exists(file_path):
        print(f"  [!] File not found at {file_path}. Skipping.")
        return
        
    print(f"  Step 1: Benchmarking text extraction engines...")
    txt_plumb, lat_plumb = DocumentExtractor.extract_with_pdfplumber(file_path)
    txt_pypdf, lat_pypdf = DocumentExtractor.extract_with_pypdf(file_path)

    print(f"    -> pdfplumber : {lat_plumb:.3f}s | {len(txt_plumb)} chars")
    print(f"    -> pypdf      : {lat_pypdf:.3f}s | {len(txt_pypdf)} chars")

    # Select the engine that extracted the highest volume of valid characters
    best_text = txt_pypdf if len(txt_pypdf) >= len(txt_plumb) else txt_plumb
    if not best_text:
        print("  [!] Failed to extract any text from the document.")
        return
        
    doc_type = PersonaAnalyzer.detect_document_type(best_text)
    print(f"  Step 2: Detected document composition as '{doc_type}'")

    print(f"  Step 3: Orchestrating profile extraction via LLM parser...")
    
    start_llm = time.time()
    profile = PersonaAnalyzer.generate_profile(best_text, doc_type)
    print(f"    -> OpenAI structured parsing completed in {time.time() - start_llm:.2f}s")
    
    return profile

def main():
    # Targets the exact user-specified Test_Docs_Data location containing the resumes
    docs_dir = "../../Temp/Test_Docs_Data"
    
    files = {
        "LinkedIn": os.path.join(docs_dir, "LinkedIn_Profile.pdf"),
        "Resume": os.path.join(docs_dir, "Resume.pdf")
    }

    results = {}
    
    for label, path in files.items():
        profile = extract_and_analyze(path, label)
        if profile:
            results[label] = profile

    print("\n" + "=" * 80)
    print("COLD START EXTRACTION SUMMARY RESULTS")
    print("=" * 80)
    
    for label, res in results.items():
        # Convert explicit model dump back to dict equivalent for dynamic sorting
        weights = res.category_weights.model_dump()
        top_cat = max(weights, key=weights.get)
        top_val = weights[top_cat]
        
        print(f"  [{label} Profile]:     {res.name} | {res.job_title}")
        print(f"  -> Top Domain Affiliation:   {top_cat} ({top_val})")
        print(f"  -> Derived Skills:           {', '.join(res.technical_skills[:8])}")
        print(f"  -> Vectorized Bio Summary:   {res.bio_summary}")
        print("-" * 80)

if __name__ == "__main__":
    main()
