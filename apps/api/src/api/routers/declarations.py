"""POST /declarations/ingest, POST /declarations/{id}/verify, GET /declarations/{id}

Decompose a political utterance into a Declaration + atomic claims, then
optionally run the full verification pipeline and emit attribution edges.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from civic_claim_decomp.declaration_decomposer import (
    DeclarationDecomposer,
    DeclarationDecompositionResult,
)
from civic_verification import DeclarationVerifier

from .pipeline import VerifyPipeline, get_pipeline

router = APIRouter(prefix="/declarations", tags=["declarations"])

_declaration_cache: dict[str, DeclarationDecompositionResult] = {}


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class DeclarationIngestRequest(BaseModel):
    utterance_text: str = Field(..., min_length=1)
    language: Literal["he", "en"] = "he"
    source_document_id: UUID
    source_kind: str = "other"
    speaker_hint: str | None = None


class DeclarationIngestResponse(BaseModel):
    declaration: dict[str, Any]
    claims_count: int
    family: str
    checkability: str


class DeclarationVerifyRequest(BaseModel):
    language: Literal["he", "en"] = "he"


class DeclarationVerifyResponse(BaseModel):
    declaration: dict[str, Any]
    claims: list[dict[str, Any]]
    claim_verdicts: list[dict[str, Any]]
    attribution_edges: list[dict[str, Any]]
    overall_relation: str


class DeclarationDetailResponse(BaseModel):
    declaration: dict[str, Any]
    claims_count: int
    family: str
    checkability: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/ingest", response_model=DeclarationIngestResponse)
def ingest_declaration(
    payload: DeclarationIngestRequest,
) -> DeclarationIngestResponse:
    decomposer = DeclarationDecomposer()
    result = decomposer.decompose(
        utterance_text=payload.utterance_text,
        language=payload.language,
        source_document_id=payload.source_document_id,
        source_kind=payload.source_kind,
    )
    key = str(result.declaration.declaration_id)
    _declaration_cache[key] = result
    return DeclarationIngestResponse(
        declaration=result.declaration.model_dump(mode="json"),
        claims_count=len(result.claims),
        family=result.family,
        checkability=result.checkability,
    )


@router.post("/{declaration_id}/verify", response_model=DeclarationVerifyResponse)
def verify_declaration(
    declaration_id: str,
    body: DeclarationVerifyRequest,
    request: Request,
    pipeline: Annotated[VerifyPipeline, Depends(get_pipeline)],
) -> DeclarationVerifyResponse:
    decomp_result = _declaration_cache.get(declaration_id)
    if decomp_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Declaration {declaration_id} not found in cache",
        )
    review_connection = getattr(request.app.state, "pg_connection", None)
    verifier = DeclarationVerifier(pipeline, review_connection=review_connection)
    verification = verifier.verify(decomp_result, language=body.language)
    payload = verification.as_dict()
    return DeclarationVerifyResponse(**payload)


@router.get("/{declaration_id}", response_model=DeclarationDetailResponse)
def get_declaration(declaration_id: str) -> DeclarationDetailResponse:
    decomp_result = _declaration_cache.get(declaration_id)
    if decomp_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Declaration {declaration_id} not found in cache",
        )
    return DeclarationDetailResponse(
        declaration=decomp_result.declaration.model_dump(mode="json"),
        claims_count=len(decomp_result.claims),
        family=decomp_result.family,
        checkability=decomp_result.checkability,
    )
