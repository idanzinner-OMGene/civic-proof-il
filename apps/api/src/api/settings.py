"""Application settings loaded from environment variables.

Uses pydantic-settings. We rely exclusively on real process env vars
(no .env file loading inside containers).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=False,
        env_prefix="",
        extra="ignore",
    )

    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(alias="POSTGRES_DB")

    neo4j_uri: str = Field(alias="NEO4J_URI")
    neo4j_user: str = Field(alias="NEO4J_USER")
    neo4j_password: str = Field(alias="NEO4J_PASSWORD")

    opensearch_url: str = Field(alias="OPENSEARCH_URL")
    opensearch_user: str | None = Field(default=None, alias="OPENSEARCH_USER")
    opensearch_password: str | None = Field(default=None, alias="OPENSEARCH_PASSWORD")

    minio_endpoint: str = Field(alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(alias="MINIO_SECRET_KEY")
    minio_bucket_archive: str = Field(default="civic-archive", alias="MINIO_BUCKET_ARCHIVE")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_log_level: str = Field(default="info", alias="API_LOG_LEVEL")
    env: str = Field(default="dev", alias="ENV")


@lru_cache
def get_settings() -> Settings:
    return Settings()
