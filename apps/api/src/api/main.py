"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from .health import router as health_router
from .settings import get_settings


def create_app() -> FastAPI:
    get_settings()
    app = FastAPI(title="civic-proof-il API", version="0.0.0")
    app.include_router(health_router)
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
