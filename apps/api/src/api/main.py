"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager, suppress

import psycopg
import structlog
from civic_clients import neo4j as neo4j_client
from civic_clients import opensearch as opensearch_client
from civic_clients import postgres as postgres_client
from civic_common.logging import configure_logging
from civic_retrieval import GraphRetriever, LexicalRetriever
from civic_review import PostgresReviewRepository
from fastapi import FastAPI

from .health import router as health_router
from .routers import claims_router, declarations_router, persons_router, review_router
from .routers.pipeline import LiveEntityResolver, VerifyPipeline, reset_pipeline, set_pipeline
from .routers.review import reset_review_repository, set_review_repository
from .settings import get_settings

log = structlog.get_logger()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """When all backing services respond to probes, wire live retrieval + review."""

    s = get_settings()
    if s.env in {"test", "ci"} and not _env_truthy("CIVIC_LIVE_WIRING", default=False):
        yield
        return
    if not (
        postgres_client.ping()
        and neo4j_client.ping()
        and opensearch_client.ping()
    ):
        log.warning("live pipeline wiring skipped: one or more backing stores unavailable")
        yield
        return
    conn: psycopg.Connection | None = None
    try:
        conn = postgres_client.make_connection()
        conn.autocommit = True
        set_review_repository(PostgresReviewRepository(conn))
        set_pipeline(
            VerifyPipeline(
                graph=GraphRetriever(neo4j_client.make_driver()),
                lexical=LexicalRetriever(opensearch_client.make_client()),
                resolver=LiveEntityResolver(
                    neo4j_driver=neo4j_client.make_driver(),
                    pg_conn=conn,
                ),
                review_connection=conn,
            )
        )
        app.state.pg_connection = conn
    except Exception:
        log.exception("failed to connect Postgres; review queue stays on empty repository")
        if conn is not None:
            with suppress(Exception):
                conn.close()
    try:
        yield
    finally:
        if conn is not None:
            with suppress(Exception):
                conn.close()
        reset_pipeline()
        reset_review_repository()


def _env_truthy(name: str, *, default: bool) -> bool:
    v = __import__("os").environ.get(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes"}


def create_app() -> FastAPI:
    configure_logging()
    get_settings()
    app = FastAPI(
        title="civic-proof-il API",
        version="0.0.0",
        lifespan=_lifespan,
    )
    app.include_router(health_router)
    app.include_router(claims_router)
    app.include_router(persons_router)
    app.include_router(review_router)
    app.include_router(declarations_router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "api.main:app",
        host=s.api_host,
        port=s.api_port,
        log_level=s.api_log_level,
    )


if __name__ == "__main__":
    run()
