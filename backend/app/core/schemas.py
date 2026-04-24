from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None

class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserPersonaBase(BaseModel):
    linkedin_url: Optional[str] = None
    job_title: Optional[str] = None
    seniority: Optional[str] = None
    bio_summary: Optional[str] = None
    explicit_category_weights: Dict[str, float] = Field(default_factory=dict)
    behavioral_category_weights: Dict[str, float] = Field(default_factory=dict)

class UserPersonaResponse(UserPersonaBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

class ArticleClusterBase(BaseModel):
    primary_title: str
    primary_summary: Optional[str] = None
    synthesized_content: Optional[str] = None
    category_weights: Dict[str, float] = Field(default_factory=dict)
    trend_status: Optional[str] = None
    cluster_size: int = 1
    social_popularity_score: float = 0.0
    final_trend_score: float = 0.0

class ArticleClusterResponse(ArticleClusterBase):
    id: str
    created_at: datetime

class ArticleRawBase(BaseModel):
    source_name: str
    source_type: Optional[str] = None
    title: str
    url: str
    summary: Optional[str] = None
    content_raw: Optional[Dict[str, Any]] = None
    extracted_full_text: Optional[str] = None
    source_tags: Optional[List[str]] = None
    published_at: Optional[datetime] = None

class ArticleRawResponse(ArticleRawBase):
    id: str
    cluster_id: Optional[str] = None
    fetched_at: datetime

class DailySelectionResponse(BaseModel):
    id: str
    user_id: str
    cluster_id: str
    selection_type: str
    match_score: float
    selected_date: datetime
    created_at: datetime

class NewsletterBase(BaseModel):
    draft_metadata: Optional[Dict[str, Any]] = None
    draft_content: Optional[str] = None
    final_content: Optional[str] = None
    status: str = 'DRAFT'
    feedback_signal: Optional[str] = None

class NewsletterResponse(NewsletterBase):
    id: str
    user_id: str
    edition_date: datetime
    created_at: datetime
    updated_at: datetime

class CategoryWeights(BaseModel):
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

class CompanyContentAffinity(BaseModel):

    llms: float = Field(ge=0.0, le=1.0)
    ai_agents: float = Field(ge=0.0, le=1.0)
    computer_vision: float = Field(ge=0.0, le=1.0)
    security: float = Field(ge=0.0, le=1.0)
    hardware: float = Field(ge=0.0, le=1.0)
    software_engineering: float = Field(ge=0.0, le=1.0)
    ai_policy: float = Field(ge=0.0, le=1.0)
    general_ai: float = Field(ge=0.0, le=1.0)
    data_engineering: float = Field(ge=0.0, le=1.0)
    startups: float = Field(ge=0.0, le=1.0)

class PersonaExtractionResult(BaseModel):
    name: str = Field(description="Full name of the user.")
    job_title: str = Field(description="Current or most recent job title.")
    seniority: str = Field(description="Estimated seniority level: entry, mid, senior, lead, executive.")
    primary_interests: List[str] = Field(description="List of primary professional interests or specializations.")
    technical_skills: List[str] = Field(description="List of hard technical skills extracted from the document.")
    bio_summary: str = Field(description="A 2-sentence professional bio summary.")
    persona_archetype: str = Field(description="One of: ML_RESEARCHER, AI_SYSTEMS_ENGINEER, DATA_STRATEGIST, PRODUCT_LEAD_AI, POLICY_ETHICS_GURU, GENERAL_TECH_ENVELOPE")
    category_weights: CategoryWeights
    source_type: str = Field(description="Inferred classification (e.g. LinkedIn PDF, Resume)")
    extraction_latency_seconds: float = Field(default=0.0)

class SinglePersonaExtractionResponse(BaseModel):
    filename: str
    is_success: bool
    data: Optional[PersonaExtractionResult] = None
    error: Optional[str] = None

class BatchPersonaResponse(BaseModel):
    user_id: str
    results: List[SinglePersonaExtractionResponse]
    overall_latency_seconds: float

class UserPersonaUpdate(BaseModel):
    user_id: str
    linkedin_url: Optional[str] = None
    job_title: Optional[str] = None
    seniority: Optional[str] = None
    persona_archetype: Optional[str] = None
    bio_summary: Optional[str] = None
    explicit_category_weights: Dict[str, float]

class RawArticleMetadata(BaseModel):
    source_name: str
    source_url: str
    title: str
    url: str
    summary: Optional[str] = None
    published_at: str
    author: Optional[str] = "Unknown"
    tags: List[str] = []

class IngestionBatchResponse(BaseModel):
    status: str
    total_found: int
    saved_count: int = 0
    start_time: str
    end_time: str
    processing_time_seconds: float

class DAGTriggerResponse(BaseModel):

    status: str = Field(description="ACCEPTED once the scheduler has the run.")
    message: str
    dag_id: str
    dag_run_id: str
    state: Optional[str] = Field(default=None, description="queued / running / success / failed.")

class B2BReportRequest(BaseModel):
    user_id: str = Field(..., description="Corporate client identifier.")

class B2BReportResponse(BaseModel):
    user_id: str
    report: str
    status: str
    already_generated: bool = Field(default=False, description="True when a brief already existed for today and was returned unchanged.")
    generated_at: Optional[str] = Field(default=None, description="ISO timestamp of the persisted brief, when known.")
    brief_date: Optional[str] = Field(default=None, description="The business day the brief addresses (YYYY-MM-DD).")
    structured_brief: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured SEO brief payload (see StrategicBrief model).",
    )
    urgency_tier: Optional[str] = None

class BriefKeyword(BaseModel):
    keyword: str = Field(..., description="Short keyword or phrase.")
    monthly_volume: Optional[int] = Field(
        default=None,
        description="Approx. monthly search volume. LLM-estimated when unknown.",
    )
    velocity_pct: Optional[float] = Field(
        default=None,
        description="Velocity % pulled from the SpaCy NER pipeline when available.",
    )
    status: Optional[str] = Field(
        default=None,
        description="SURGING / STABLE / DECLINING — only set when velocity is present.",
    )

class BriefContentSection(BaseModel):
    step: int = Field(..., description="1-indexed ordering of the section.")
    title: str
    description: str

class BriefReference(BaseModel):
    title: str
    url: str
    source_name: Optional[str] = None

class StrategicBrief(BaseModel):

    opportunity_score: float = Field(..., description="0-100 opportunity score.")
    urgency_tier: str = Field(
        ...,
        description="HIDDEN_GEM | ACT_NOW | MONITOR | SKIP",
    )
    headline: str = Field(..., description="One-line strategic framing of the opportunity.")
    blue_ocean_angle: str = Field(
        ...,
        description="2-3 sentence 'Blue Ocean' strategic angle unique to this company.",
    )
    editorial_titles: List[str] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="3-5 suggested article titles.",
    )
    primary_keywords: List[BriefKeyword] = Field(
        ...,
        description="4-6 keywords the article should rank for, with rough monthly volume.",
    )
    content_structure: List[BriefContentSection] = Field(
        ...,
        min_length=3,
        description="Ordered section breakdown for the long-form article.",
    )
    internal_linking_strategy: str = Field(
        ...,
        description="Plain-text paragraph suggesting cross-links and glossary concepts.",
    )


class StrategicBriefEnvelope(BaseModel):

    brief: StrategicBrief
    reference_sources: List[BriefReference] = Field(default_factory=list)
    company_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="Subset of the company profile captured at generation time.",
    )

class FeedbackType(str, Enum):
    like = "like"
    dislike = "dislike"
    skip = "skip"

class ArticleFeedbackRequest(BaseModel):
    user_id: str = Field(..., description="The user providing feedback.")
    article_categories: Dict[str, float] = Field(
        ...,
        description="Category weights for the article (e.g. {'llms': 0.8, 'security': 0.2})."
    )
    feedback: FeedbackType

class ArticleFeedbackResponse(BaseModel):
    user_id: str
    updated_categories: Dict[str, float]
    message: str

class B2CNewsletterRequest(BaseModel):
    user_id: str
    execution_mode: Literal["fast", "polished"] = Field(default="polished", description="Allows skipping the Fact-Checker loop for speed ('fast' vs 'polished')")

class B2CNewsletterResponse(BaseModel):
    status: str
    html_content: str
    execution_path_taken: List[str] = Field(default_factory=list, description="Array plotting the LangGraph nodes triggered natively for UI visibility")
    already_generated: bool = Field(default=False, description="True when today's newsletter was pulled from Snowflake rather than regenerated.")
    generated_at: Optional[str] = Field(default=None, description="ISO timestamp of the persisted draft, when known.")
    edition_date: Optional[str] = Field(default=None, description="Edition date (YYYY-MM-DD) the draft belongs to.")