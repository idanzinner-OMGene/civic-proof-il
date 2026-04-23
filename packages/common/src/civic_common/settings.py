"""Shared application settings loaded from environment variables.

Every service (apps/api, apps/worker, apps/migrator, packages/clients, …)
imports ``Settings`` / ``get_settings`` from here so the env-var contract
(see ``.env.example``) has a single source of truth.

Runtime env vars are the only input: we intentionally pass ``env_file=None``
because inside Docker Compose the vars are injected by the orchestrator and
inside CI they come from the process environment. Loading a stray ``.env``
would mask real mis-configurations.
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
    """Return a process-cached Settings instance.

    Call ``get_settings.cache_clear()`` between tests that mutate env vars.
    """

    return Settings()
