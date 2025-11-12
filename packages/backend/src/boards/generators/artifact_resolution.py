"""
Utilities for resolving generation IDs to artifact objects.

This module provides utilities for converting generation ID strings (UUIDs)
into typed artifact objects (ImageArtifact, AudioArtifact, etc.) with proper
validation of ownership and completion status.

The main approach is to automatically detect artifact fields via type introspection
and resolve them BEFORE Pydantic validation.
"""

from typing import Any, TypeVar, get_args, get_origin
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..dbmodels import Generations
from ..jobs import repository as jobs_repo
from ..logging import get_logger
from .artifacts import AudioArtifact, ImageArtifact, TextArtifact, VideoArtifact

logger = get_logger(__name__)

# Type variable for artifact types
TArtifact = TypeVar("TArtifact", ImageArtifact, VideoArtifact, AudioArtifact, TextArtifact)

# Set of all artifact types for quick checking
ARTIFACT_TYPES = {ImageArtifact, VideoArtifact, AudioArtifact, TextArtifact}


def _extract_artifact_type(annotation: Any) -> type[TArtifact] | None:
    """Extract artifact type from a field annotation.

    Handles both single artifacts (ImageArtifact) and lists (list[ImageArtifact]).

    Args:
        annotation: The type annotation from a Pydantic field

    Returns:
        The artifact class if this is an artifact field, None otherwise

    Examples:
        _extract_artifact_type(ImageArtifact) -> ImageArtifact
        _extract_artifact_type(list[ImageArtifact]) -> ImageArtifact
        _extract_artifact_type(str) -> None
    """
    # Direct artifact type (e.g., ImageArtifact)
    if annotation in ARTIFACT_TYPES:
        return annotation  # type: ignore[return-value]

    # List of artifacts (e.g., list[ImageArtifact])
    origin = get_origin(annotation)
    if origin is list:
        args = get_args(annotation)
        if args and args[0] in ARTIFACT_TYPES:
            return args[0]  # type: ignore[return-value]

    return None


def extract_artifact_fields(schema: type[BaseModel]) -> dict[str, tuple[type[TArtifact], bool]]:
    """Automatically extract artifact fields from a Pydantic schema.

    Inspects the schema's field annotations and returns a mapping of field names
    to their artifact types and whether they expect a list.

    Args:
        schema: Pydantic model class to inspect

    Returns:
        Dictionary mapping field names to (artifact_type, is_list) tuples

    Example:
        class MyInput(BaseModel):
            prompt: str
            image_source: ImageArtifact
            video_sources: list[VideoArtifact]

        extract_artifact_fields(MyInput)
        # Returns: {"image_source": (ImageArtifact, False), "video_sources": (VideoArtifact, True)}
    """
    artifact_fields: dict[str, tuple[type[TArtifact], bool]] = {}

    for field_name, field_info in schema.model_fields.items():
        artifact_type = _extract_artifact_type(field_info.annotation)
        if artifact_type is not None:
            # Check if the field is a list type
            origin = get_origin(field_info.annotation)
            is_list = origin is list
            artifact_fields[field_name] = (artifact_type, is_list)

    return artifact_fields


def _get_artifact_type_name[T: (ImageArtifact, VideoArtifact, AudioArtifact, TextArtifact)](
    artifact_class: type[T],
) -> str:
    """Get the database artifact_type string for an artifact class."""
    type_map = {
        ImageArtifact: "image",
        VideoArtifact: "video",
        AudioArtifact: "audio",
        TextArtifact: "text",
    }
    artifact_type = type_map.get(artifact_class)
    if artifact_type is None:
        raise ValueError(f"Unsupported artifact class: {artifact_class}")
    return artifact_type


def _generation_to_artifact[T: (ImageArtifact, VideoArtifact, AudioArtifact, TextArtifact)](
    generation: Generations, artifact_class: type[T]
) -> T:
    """Convert a Generations database record to an artifact object.

    Args:
        generation: Database generation record
        artifact_class: Target artifact class (ImageArtifact, VideoArtifact, etc.)

    Returns:
        Artifact object populated from the generation record

    Raises:
        ValueError: If generation is missing required fields or data
    """
    if not generation.storage_url:
        raise ValueError(
            f"Generation {generation.id} has no storage_url - generation may not be completed"
        )

    # Get output metadata
    metadata = generation.output_metadata or {}

    # Build artifact based on type
    if artifact_class == ImageArtifact:
        width = metadata.get("width")
        height = metadata.get("height")
        return ImageArtifact(
            generation_id=str(generation.id),
            storage_url=generation.storage_url,
            format=metadata.get("format", "png"),
            width=width,
            height=height,
        )  # type: ignore[return-value]

    elif artifact_class == VideoArtifact:
        width = metadata.get("width")
        height = metadata.get("height")
        return VideoArtifact(
            generation_id=str(generation.id),
            storage_url=generation.storage_url,
            format=metadata.get("format", "mp4"),
            width=width,
            height=height,
            duration=metadata.get("duration"),
            fps=metadata.get("fps"),
        )  # type: ignore[return-value]

    elif artifact_class == AudioArtifact:
        return AudioArtifact(
            generation_id=str(generation.id),
            storage_url=generation.storage_url,
            format=metadata.get("format", "mp3"),
            duration=metadata.get("duration"),
            sample_rate=metadata.get("sample_rate"),
            channels=metadata.get("channels"),
        )  # type: ignore[return-value]

    elif artifact_class == TextArtifact:
        content = metadata.get("content")
        if content is None:
            raise ValueError(f"Generation {generation.id} missing text content in output_metadata")
        return TextArtifact(
            generation_id=str(generation.id),
            storage_url=generation.storage_url,
            format=metadata.get("format", "plain"),
            content=content,
        )  # type: ignore[return-value]

    else:
        raise ValueError(f"Unsupported artifact class: {artifact_class}")


async def resolve_generation_ids_to_artifacts[
    T: (ImageArtifact, VideoArtifact, AudioArtifact, TextArtifact)
](
    generation_ids: list[str | UUID],
    artifact_class: type[T],
    session: AsyncSession,
    tenant_id: UUID,
) -> list[T]:
    """Convert a list of generation IDs to typed artifact objects.

    This function:
    1. Queries the database for each generation ID
    2. Validates the generation is completed
    3. Validates the artifact type matches
    4. Validates the user has access (tenant_id matches)
    5. Converts to the appropriate artifact object

    Args:
        generation_ids: List of generation IDs (as strings or UUIDs)
        artifact_class: Target artifact class (ImageArtifact, VideoArtifact, etc.)
        session: Database session for queries
        tenant_id: Tenant ID for access validation

    Returns:
        List of artifact objects

    Raises:
        ValueError: If any generation is not found, not completed, wrong type, or access denied
    """
    expected_artifact_type = _get_artifact_type_name(artifact_class)
    artifacts: list[T] = []

    for gen_id in generation_ids:
        # Query generation from database
        try:
            generation = await jobs_repo.get_generation(session, gen_id)
        except Exception as e:
            raise ValueError(f"Generation {gen_id} not found") from e

        # Validate tenant access
        if generation.tenant_id != tenant_id:
            raise ValueError(f"Access denied to generation {gen_id} - tenant mismatch")

        # Validate completion status
        if generation.status != "completed":
            raise ValueError(f"Generation {gen_id} is not completed (status: {generation.status})")

        # Validate artifact type
        if generation.artifact_type != expected_artifact_type:
            raise ValueError(
                f"Generation {gen_id} has wrong artifact type: "
                f"expected {expected_artifact_type}, got {generation.artifact_type}"
            )

        # Convert to artifact object
        try:
            artifact = _generation_to_artifact(generation, artifact_class)
            artifacts.append(artifact)
        except ValueError as e:
            raise ValueError(f"Failed to convert generation {gen_id} to artifact: {e}") from e

    return artifacts


async def resolve_input_artifacts(
    input_params: dict[str, Any],
    schema: type[BaseModel],
    session: AsyncSession,
    tenant_id: UUID,
) -> dict[str, Any]:
    """Resolve generation IDs to artifact objects in input parameters.

    This function automatically detects artifact fields from the Pydantic schema
    via type introspection, then resolves generation ID strings to typed artifact
    objects before Pydantic validation.

    The function respects the field's type annotation:
    - If field is `ImageArtifact`, input can be a single ID string → returns single artifact
    - If field is `list[ImageArtifact]`, input can be a list of IDs → returns list of artifacts
      (always a list, even if only one ID is provided)

    Usage in generator input schema (no special declarations needed!):
        class MyGeneratorInput(BaseModel):
            prompt: str = Field(...)
            image_source: ImageArtifact = Field(...)  # Automatically detected
            video_sources: list[VideoArtifact] = Field(...)  # Also detected

    Usage in actors.py:
        # Artifacts are automatically detected and resolved
        resolved_params = await resolve_input_artifacts(
            input_params,
            MyGeneratorInput,  # Just pass the schema class
            session,
            tenant_id,
        )
        # Now validate with resolved artifacts
        typed_inputs = MyGeneratorInput.model_validate(resolved_params)

    Args:
        input_params: Raw input parameters dictionary (may contain generation IDs)
        schema: Pydantic model class to inspect for artifact fields
        session: Database session for queries
        tenant_id: Tenant ID for access validation

    Returns:
        Updated input_params dictionary with generation IDs resolved to artifacts

    Raises:
        ValueError: If any generation ID cannot be resolved or validated
    """
    # Automatically extract artifact fields from schema
    artifact_field_map = extract_artifact_fields(schema)

    # If no artifact fields, just return original params
    if not artifact_field_map:
        return input_params

    # Create a new dict with resolved artifacts
    # Use dict constructor to avoid shallow copy issues
    resolved_params = dict(input_params)

    for field_name, (artifact_class, expects_list) in artifact_field_map.items():
        field_value = resolved_params.get(field_name)

        # Skip if field is not present
        if field_value is None:
            continue

        # Skip if already artifacts (already resolved)
        if isinstance(field_value, list) and all(
            isinstance(item, artifact_class) for item in field_value
        ):
            continue

        # Also check for single artifact (only if field expects a single artifact)
        if not expects_list and isinstance(field_value, artifact_class):
            continue

        # Convert field value to list of UUIDs
        generation_ids: list[str | UUID]
        if isinstance(field_value, str):
            # Single generation ID - convert to list for processing
            generation_ids = [field_value]
        elif isinstance(field_value, list):
            # List of generation IDs - ensure all are strings
            # Convert each item to str to ensure type consistency
            generation_ids = [str(item) for item in field_value]
        else:
            raise ValueError(
                f"Field '{field_name}' must be a generation ID (UUID string) "
                f"or list of generation IDs, got: {type(field_value)}"
            )

        # Resolve to artifacts
        try:
            artifacts = await resolve_generation_ids_to_artifacts(
                generation_ids, artifact_class, session, tenant_id
            )
        except ValueError as e:
            raise ValueError(f"Failed to resolve field '{field_name}': {e}") from e

        # Update params with resolved artifacts
        # If field expects a single artifact (not a list), unwrap the first artifact
        # Otherwise, keep as a list (even if there's only one artifact)
        if expects_list:
            resolved_value = artifacts
        else:
            # Field expects a single artifact, so unwrap
            if len(artifacts) != 1:
                raise ValueError(
                    f"Field '{field_name}' expects a single artifact, "
                    f"but got {len(artifacts)} generation IDs"
                )
            resolved_value = artifacts[0]

        # Debug logging
        logger.debug(
            "Resolved artifact field",
            field_name=field_name,
            expects_list=expects_list,
            artifacts_type=type(artifacts),
            artifacts_len=len(artifacts),
            resolved_value_type=type(resolved_value),
        )

        resolved_params[field_name] = resolved_value

    return resolved_params
