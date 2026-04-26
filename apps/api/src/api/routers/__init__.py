"""FastAPI routers for the /claims/verify Phase-3+4 slice."""

from __future__ import annotations

from .claims import router as claims_router
from .persons import router as persons_router
from .review import router as review_router

__all__ = ["claims_router", "persons_router", "review_router"]
