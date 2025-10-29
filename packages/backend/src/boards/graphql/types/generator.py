"""
Generator GraphQL type definitions
"""

import strawberry

from .generation import ArtifactType


@strawberry.type
class GeneratorInfo:
    """Information about an available generator."""

    name: str
    description: str
    artifact_type: ArtifactType
    input_schema: strawberry.scalars.JSON  # type: ignore[reportInvalidTypeForm]
