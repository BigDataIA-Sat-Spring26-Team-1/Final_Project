import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings managed via Pydantic.
    Automatically maps variables from the root .env file.
    """
    app_name: str = "Curate AI"
    app_version: str = "1.0.0"
    app_env: str = "dev"  # dev | uat | prod
    secret_key: str

    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_database: str
    snowflake_schema: str
    snowflake_warehouse: str
    snowflake_role: str

    # External APIs
    openai_api_key: str

    # Qdrant Vector DB Settings
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = "" # Leave blank for local testing
    
    # Intelligence Engine Thresholds & Models
    default_llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    vector_dimension_size: int = 1536
    deduplication_threshold: float = 0.75
    
    # Trend Analysis Benchmarks
    trend_breaking_threshold: int = 3
    trend_trending_threshold: int = 2
    trend_viral_social_benchmark: int = 500
    trend_community_pick_social_benchmark: int = 150
    trend_cluster_min_size: int = 3

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), '../../.env'),
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    """Cache settings to prevent repeated disk reads on each request."""
    return Settings()
