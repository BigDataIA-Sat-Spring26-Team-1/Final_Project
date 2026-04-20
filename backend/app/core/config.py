"""Application configuration.

Settings are loaded via ``pydantic-settings`` in this order of precedence:
    1. Process environment variables  (what Cloud Run / Docker inject)
    2. A ``.env`` file at the repo root  (developer convenience for local runs)
    3. Hard-coded defaults declared below

Secrets (Snowflake, OpenAI, etc.) must never be committed — they come from
env vars in every deployed environment. The ``.env`` lookup is best-effort:
if the file is missing (as on Cloud Run) pydantic-settings silently skips it.
"""
import os
from functools import lru_cache
from typing import Annotated, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


# Walk up from this file to the repo root so .env resolves correctly whether
# you launch from /backend, the repo root, or inside a container where the
# file simply isn't there.
_REPO_ROOT_ENV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
)


class Settings(BaseSettings):
    """Runtime configuration for the CurateAI backend."""

    # ---- Application identity --------------------------------------------------
    app_name: str = "Curate AI"
    app_version: str = "1.0.0"
    # dev / uat / prod — switches logging renderer and log verbosity.
    app_env: str = "dev"
    # Used for session/signing; in prod this must come from Secret Manager.
    secret_key: str

    # ---- HTTP server -----------------------------------------------------------
    # Cloud Run injects PORT; locally this acts as a sensible default.
    port: int = 8080
    # CSV of allowed CORS origins. `NoDecode` keeps pydantic-settings from
    # trying to JSON-parse the raw env var — the validator below turns
    # "https://a.com,https://b.com" into a list, which is what CORS wants.
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # ---- Snowflake -------------------------------------------------------------
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_database: str
    snowflake_schema: str
    snowflake_warehouse: str
    snowflake_role: str

    # ---- External APIs ---------------------------------------------------------
    openai_api_key: str

    # ---- Qdrant Vector DB ------------------------------------------------------
    qdrant_url: str = "http://localhost:6333"
    # Empty in local dev; required when Qdrant Cloud enforces auth.
    qdrant_api_key: str = ""

    # ---- Intelligence engine ---------------------------------------------------
    default_llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    vector_dimension_size: int = 1536
    deduplication_threshold: float = 0.75

    # ---- Trend analysis --------------------------------------------------------
    trend_breaking_threshold: int = 3
    trend_trending_threshold: int = 2
    trend_viral_social_benchmark: int = 500
    trend_community_pick_social_benchmark: int = 150
    trend_cluster_min_size: int = 3

    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT_ENV,
        env_file_encoding="utf-8",
        # Unknown env vars (AIRFLOW_*, GCP_*, etc.) shouldn't crash startup.
        extra="ignore",
        # CORS_ORIGINS="a,b,c" should behave the same as a YAML/JSON list.
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv_origins(cls, v):
        """Allow CORS_ORIGINS="https://a.com,https://b.com" from env vars."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """True once APP_ENV is explicitly set to uat or prod."""
        return self.app_env.lower() in {"uat", "prod"}


@lru_cache()
def get_settings() -> Settings:
    """Return a process-wide singleton of ``Settings``.

    Cached so every ``Depends(get_settings)`` FastAPI call reuses the same
    instance — avoids re-parsing .env and re-validating fields on every request.
    """
    return Settings()
