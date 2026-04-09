from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

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
