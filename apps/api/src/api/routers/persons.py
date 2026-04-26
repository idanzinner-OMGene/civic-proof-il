"""GET /persons/{person_id} — return the canonical person card.

The card is read from Neo4j in production; tests inject a
``PersonRepository`` stub via dependency override.
"""

from __future__ import annotations

from typing import Annotated, Any, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/persons", tags=["persons"])


class PersonRepository(Protocol):
    def fetch(self, person_id: UUID) -> dict[str, Any] | None: ...


class _EmptyPersonRepository:
    def fetch(self, person_id: UUID) -> dict[str, Any] | None:  # noqa: D401, ARG002
        return None


_default_repository: PersonRepository = _EmptyPersonRepository()


def get_person_repository() -> PersonRepository:
    return _default_repository


def set_person_repository(repo: PersonRepository) -> None:
    global _default_repository
    _default_repository = repo


@router.get("/{person_id}")
def get_person(
    person_id: UUID,
    repo: Annotated[PersonRepository, Depends(get_person_repository)],
) -> dict[str, Any]:
    card = repo.fetch(person_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="person not found")
    return card
