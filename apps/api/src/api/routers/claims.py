"""POST /claims/verify — decompose a statement and return a ranked
verdict bundle for each atomic claim it produces.

Request body:

```json
{"statement": "...", "language": "he"}
```

Response body:

```json
{"claims": [{"verdict": {...}, "top_evidence": [...], "uncertainty_note": null, "claim": {...}}]}
```
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .pipeline import VerifyPipeline, get_pipeline

router = APIRouter(prefix="/claims", tags=["claims"])


class ClaimsVerifyRequest(BaseModel):
    statement: str = Field(..., min_length=1)
    language: Literal["he", "en"] = "he"


class ClaimsVerifyResponse(BaseModel):
    claims: list[dict[str, Any]]


@router.post("/verify", response_model=ClaimsVerifyResponse)
def verify_claim(
    payload: ClaimsVerifyRequest,
    pipeline: Annotated[VerifyPipeline, Depends(get_pipeline)],
) -> ClaimsVerifyResponse:
    bundles = pipeline.verify(payload.statement, language=payload.language)
    return ClaimsVerifyResponse(claims=bundles)
