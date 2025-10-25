"""
Generation GraphQL type definitions
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

import strawberry

if TYPE_CHECKING:
    from .board import Board
    from .user import User


@strawberry.enum
class ArtifactType(Enum):
    """Artifact type enumeration."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    LORA = "lora"
    MODEL = "model"


@strawberry.enum
class GenerationStatus(Enum):
    """Generation status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@strawberry.type
class AdditionalFile:
    """Additional file associated with a generation."""

    url: str
    type: str
    metadata: strawberry.scalars.JSON  # type: ignore[reportInvalidTypeForm]


@strawberry.type
class Generation:
    """Generation type for GraphQL API."""

    id: UUID
    tenant_id: UUID
    board_id: UUID
    user_id: UUID

    # Generation details
    generator_name: str
    artifact_type: ArtifactType

    # Storage
    storage_url: str | None
    thumbnail_url: str | None
    additional_files: list[AdditionalFile]

    # Parameters and metadata
    input_params: strawberry.scalars.JSON  # type: ignore[reportInvalidTypeForm]
    output_metadata: strawberry.scalars.JSON  # type: ignore[reportInvalidTypeForm]

    # Lineage
    parent_generation_id: UUID | None
    input_generation_ids: list[UUID]

    # Job tracking
    external_job_id: str | None
    status: GenerationStatus
    progress: float
    error_message: str | None

    # Timestamps
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def board(self, info: strawberry.Info) -> Annotated["Board", strawberry.lazy(".board")]:
        """Get the board this generation belongs to."""
        from ..resolvers.generation import resolve_generation_board

        return await resolve_generation_board(self, info)

    @strawberry.field
    async def user(self, info: strawberry.Info) -> Annotated["User", strawberry.lazy(".user")]:
        """Get the user who created this generation."""
        from ..resolvers.generation import resolve_generation_user

        return await resolve_generation_user(self, info)

    @strawberry.field
    async def parent(
        self, info: strawberry.Info
    ) -> Annotated["Generation", strawberry.lazy(".generation")] | None:  # noqa: E501
        """Get the parent generation if any."""
        if not self.parent_generation_id:
            return None
        from ..resolvers.generation import resolve_generation_parent

        return await resolve_generation_parent(self, info)

    @strawberry.field
    async def inputs(
        self, info: strawberry.Info
    ) -> list[Annotated["Generation", strawberry.lazy(".generation")]]:  # noqa: E501
        """Get input generations used for this generation."""
        if not self.input_generation_ids:
            return []
        from ..resolvers.generation import resolve_generation_inputs

        return await resolve_generation_inputs(self, info)

    @strawberry.field
    async def children(
        self, info: strawberry.Info
    ) -> list[Annotated["Generation", strawberry.lazy(".generation")]]:  # noqa: E501
        """Get child generations derived from this one."""
        from ..resolvers.generation import resolve_generation_children

        return await resolve_generation_children(self, info)
