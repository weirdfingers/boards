"""
Generator resolvers for GraphQL API
"""

import strawberry

from ...generators.registry import registry
from ..types.generation import ArtifactType
from ..types.generator import GeneratorInfo


async def resolve_generators(
    info: strawberry.Info,
    artifact_type: str | None = None,
) -> list[GeneratorInfo]:
    """Get all available generators, optionally filtered by artifact type.

    Args:
        info: GraphQL info context
        artifact_type: Optional filter by artifact type (image, video, audio, text)

    Returns:
        List of generator information
    """
    _ = info  # Unused but required by GraphQL interface

    # Get generators from registry
    if artifact_type:
        generators = registry.list_by_artifact_type(artifact_type)
    else:
        generators = registry.list_all()

    # Convert to GraphQL types
    result = []
    for gen in generators:
        input_schema_class = gen.get_input_schema()

        # Convert string artifact_type to enum
        artifact_type_enum = ArtifactType(gen.artifact_type)

        result.append(
            GeneratorInfo(
                name=gen.name,
                description=gen.description,
                artifact_type=artifact_type_enum,
                input_schema=input_schema_class.model_json_schema(),
            )
        )

    return result
