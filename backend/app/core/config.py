import os
from functools import lru_cache
from typing import Annotated, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_REPO_ROOT_ENV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
)

class Settings(BaseSettings):

    app_name: str = "Curate AI"
    app_version: str = "1.0.0"
    app_env: str = "dev"
    secret_key: str
    port: int = 8080
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_database: str
    snowflake_schema: str
    snowflake_warehouse: str
    snowflake_role: str
    openai_api_key: str
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    default_llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    vector_dimension_size: int = 1536
    deduplication_threshold: float = 0.75
    trend_breaking_threshold: int = 3
    trend_trending_threshold: int = 2
    trend_viral_social_benchmark: int = 500
    trend_community_pick_social_benchmark: int = 150
    trend_cluster_min_size: int = 3

    airflow_host: str = ""
    airflow_username: str = "admin"
    airflow_password: str = "admin"
    airflow_request_timeout_seconds: float = 10.0

    # Gmail SMTP — replaces MailerSend. Uses STARTTLS on 587 with an App
    # Password generated for a Google account (personal @gmail.com or
    # Workspace @yourdomain.com). No recipient allow-list, ~500 sends/day
    # for consumer Gmail and 2000/day for Workspace.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "CurateAI Newsletter"
    smtp_test_recipient: str = ""

    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT_ENV,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"uat", "prod"}

@lru_cache()
def get_settings() -> Settings:
    return Settings()