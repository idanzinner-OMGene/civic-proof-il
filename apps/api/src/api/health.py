"""Liveness and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from fastapi.concurrency import run_in_threadpool

from .clients import (
    minio_client,
    neo4j_client,
    opensearch_client,
    postgres,
)

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe — returns OK as long as the process is up."""

    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, object]:
    """Readiness probe — confirms all downstream dependencies are reachable."""

    pg_ok = await run_in_threadpool(postgres.ping_postgres)
    neo_ok = await run_in_threadpool(neo4j_client.ping_neo4j)
    os_ok = await run_in_threadpool(opensearch_client.ping_opensearch)
    mn_ok = await run_in_threadpool(minio_client.ping_minio)

    components = {
        "postgres": bool(pg_ok),
        "neo4j": bool(neo_ok),
        "opensearch": bool(os_ok),
        "minio": bool(mn_ok),
    }
    all_ready = all(components.values())
    response.status_code = (
        status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return {
        "status": "ready" if all_ready else "not_ready",
        "components": components,
    }
