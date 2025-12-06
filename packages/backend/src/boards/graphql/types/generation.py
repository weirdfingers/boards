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


@strawberry.input
class UploadArtifactInput:
    """Input for uploading an artifact from URL."""

    board_id: UUID
    artifact_type: ArtifactType
    file_url: str | None = None
    original_filename: str | None = None
    user_description: str | None = None
    parent_generation_id: UUID | None = None


@strawberry.type
class ArtifactLineage:
    """Represents a single input artifact relationship with role metadata."""

    generation_id: UUID
    role: str
    artifact_type: ArtifactType

    @strawberry.field
    async def generation(
        self, info: strawberry.Info
    ) -> Annotated["Generation", strawberry.lazy(".generation")] | None:
        """Resolve the full generation object for this input."""
        from ..resolvers.lineage import resolve_generation_by_id

        return await resolve_generation_by_id(info, self.generation_id)


@strawberry.type
class AncestryNode:
    """Represents a node in the ancestry tree."""

    generation: Annotated["Generation", strawberry.lazy(".generation")]
    depth: int
    role: str | None
    parents: list["AncestryNode"]


@strawberry.type
class DescendantNode:
    """Represents a node in the descendants tree."""

    generation: Annotated["Generation", strawberry.lazy(".generation")]
    depth: int
    role: str | None
    children: list["DescendantNode"]


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
    async def input_artifacts(self, info: strawberry.Info) -> list[ArtifactLineage]:
        """Get input artifacts with role metadata."""
        from ..resolvers.lineage import resolve_input_artifacts

        return await resolve_input_artifacts(self, info)

    @strawberry.field
    async def ancestry(self, info: strawberry.Info, max_depth: int = 25) -> AncestryNode:
        """Get complete ancestry tree up to max_depth levels."""
        from ..resolvers.lineage import resolve_ancestry

        return await resolve_ancestry(self, info, max_depth)

    @strawberry.field
    async def descendants(self, info: strawberry.Info, max_depth: int = 25) -> DescendantNode:
        """Get complete descendants tree up to max_depth levels."""
        from ..resolvers.lineage import resolve_descendants

        return await resolve_descendants(self, info, max_depth)
