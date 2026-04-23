"""MembershipTerm — time-bounded membership of a Person in an org."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .common import OrgType


class MembershipTerm(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    membership_term_id: UUID
    person_id: UUID
    org_id: UUID
    org_type: OrgType
    valid_from: datetime
    valid_to: datetime | None = None
