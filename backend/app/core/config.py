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

    openai_api_key: str

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), '../../.env'),
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    """Cache settings to prevent repeated disk reads on each request."""
    return Settings()
