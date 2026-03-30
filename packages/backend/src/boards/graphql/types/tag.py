"""
Tag GraphQL type definitions
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import strawberry

if TYPE_CHECKING:
    from ...dbmodels import Tags as TagsDB


@strawberry.type
class Tag:
    """Tag type for GraphQL API."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    description: str | None
    metadata: strawberry.scalars.JSON  # type: ignore[reportInvalidTypeForm]
    created_at: datetime
    updated_at: datetime


def tag_from_db_model(db_tag: TagsDB) -> Tag:
    """Convert a database Tag model to GraphQL Tag type."""
    return Tag(
        id=db_tag.id,
        tenant_id=db_tag.tenant_id,
        name=db_tag.name,
        slug=db_tag.slug,
        description=db_tag.description,
        metadata=db_tag.metadata_ or {},
        created_at=db_tag.created_at,
        updated_at=db_tag.updated_at,
    )
