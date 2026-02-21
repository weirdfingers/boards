"""
Tag GraphQL resolvers
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from uuid import UUID

import strawberry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...auth.context import AuthContext
from ...database.connection import get_async_session
from ...dbmodels import Boards, Generations, GenerationTags, Tags
from ...logging import get_logger
from ..access_control import can_access_board, get_auth_context_from_info

if TYPE_CHECKING:
    from ..mutations.root import CreateTagInput, UpdateTagInput
    from ..types.tag import Tag

logger = get_logger(__name__)


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    # Convert to lowercase
    slug = text.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)
    # Remove any characters that aren't alphanumeric or hyphens
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r"-+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    return slug


# Query resolvers
async def resolve_tags(
    info: strawberry.Info,
    limit: int = 100,
    offset: int = 0,
) -> list[Tag]:
    """
    Resolve all tags for the current tenant.

    Requires authentication.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        logger.info("Unauthenticated access to tags")
        return []

    async with get_async_session() as session:
        stmt = (
            select(Tags)
            .where(Tags.tenant_id == auth_context.tenant_id)
            .order_by(Tags.name)
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(stmt)
        tags = result.scalars().all()

        from ..types.tag import tag_from_db_model

        return [tag_from_db_model(tag) for tag in tags]


async def resolve_tag_by_id(info: strawberry.Info, id: UUID) -> Tag | None:
    """
    Resolve a tag by its ID.

    Requires authentication and tag must belong to user's tenant.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        return None

    async with get_async_session() as session:
        stmt = select(Tags).where(
            Tags.id == id,
            Tags.tenant_id == auth_context.tenant_id,
        )

        result = await session.execute(stmt)
        tag = result.scalar_one_or_none()

        if not tag:
            return None

        from ..types.tag import tag_from_db_model

        return tag_from_db_model(tag)


async def resolve_tag_by_slug(info: strawberry.Info, slug: str) -> Tag | None:
    """
    Resolve a tag by its slug.

    Requires authentication and tag must belong to user's tenant.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        return None

    async with get_async_session() as session:
        stmt = select(Tags).where(
            Tags.slug == slug,
            Tags.tenant_id == auth_context.tenant_id,
        )

        result = await session.execute(stmt)
        tag = result.scalar_one_or_none()

        if not tag:
            return None

        from ..types.tag import tag_from_db_model

        return tag_from_db_model(tag)


async def resolve_generation_tags(generation_id: UUID, info: strawberry.Info) -> list[Tag]:
    """
    Resolve tags for a generation.

    This is a field resolver for Generation.tags.
    Authorization is handled by the parent generation resolver.
    """
    async with get_async_session() as session:
        stmt = (
            select(Tags)
            .join(GenerationTags, GenerationTags.tag_id == Tags.id)
            .where(GenerationTags.generation_id == generation_id)
            .order_by(Tags.name)
        )

        result = await session.execute(stmt)
        tags = result.scalars().all()

        from ..types.tag import tag_from_db_model

        return [tag_from_db_model(tag) for tag in tags]


# Mutation resolvers
async def create_tag(info: strawberry.Info, input: CreateTagInput) -> Tag:
    """
    Create a new tag.

    Requires authentication. Tag is created in the user's tenant.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        raise RuntimeError("Authentication required to create a tag")

    async with get_async_session() as session:
        # Generate slug from name if not provided
        slug = input.slug if input.slug else slugify(input.name)

        if not slug:
            raise RuntimeError("Tag name must contain at least one alphanumeric character")

        # Check for duplicate slug in tenant
        existing_stmt = select(Tags).where(
            Tags.tenant_id == auth_context.tenant_id,
            Tags.slug == slug,
        )
        existing_result = await session.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            raise RuntimeError(f"Tag with slug '{slug}' already exists")

        # Create the tag
        new_tag = Tags()
        new_tag.tenant_id = auth_context.tenant_id
        new_tag.name = input.name
        new_tag.slug = slug
        new_tag.description = input.description
        new_tag.metadata_ = input.metadata or {}

        session.add(new_tag)
        await session.commit()
        await session.refresh(new_tag)

        logger.info(
            "Tag created",
            tag_id=str(new_tag.id),
            tenant_id=str(auth_context.tenant_id),
            name=new_tag.name,
            slug=new_tag.slug,
        )

        from ..types.tag import tag_from_db_model

        return tag_from_db_model(new_tag)


async def update_tag(info: strawberry.Info, input: UpdateTagInput) -> Tag:
    """
    Update an existing tag.

    Requires authentication. Tag must belong to user's tenant.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        raise RuntimeError("Authentication required to update a tag")

    async with get_async_session() as session:
        # Get the tag
        stmt = select(Tags).where(
            Tags.id == input.id,
            Tags.tenant_id == auth_context.tenant_id,
        )
        result = await session.execute(stmt)
        tag = result.scalar_one_or_none()

        if not tag:
            raise RuntimeError("Tag not found")

        # Update fields if provided
        if input.name is not None:
            tag.name = input.name
            # Update slug if name changed and slug not explicitly provided
            if input.slug is None:
                new_slug = slugify(input.name)
                if not new_slug:
                    raise RuntimeError("Tag name must contain at least one alphanumeric character")
                # Check for duplicate slug
                existing_stmt = select(Tags).where(
                    Tags.tenant_id == auth_context.tenant_id,
                    Tags.slug == new_slug,
                    Tags.id != input.id,
                )
                existing_result = await session.execute(existing_stmt)
                if existing_result.scalar_one_or_none():
                    raise RuntimeError(f"Tag with slug '{new_slug}' already exists")
                tag.slug = new_slug

        if input.slug is not None:
            # Check for duplicate slug
            existing_stmt = select(Tags).where(
                Tags.tenant_id == auth_context.tenant_id,
                Tags.slug == input.slug,
                Tags.id != input.id,
            )
            existing_result = await session.execute(existing_stmt)
            if existing_result.scalar_one_or_none():
                raise RuntimeError(f"Tag with slug '{input.slug}' already exists")
            tag.slug = input.slug

        if input.description is not None:
            tag.description = input.description

        if input.metadata is not None:
            tag.metadata_ = input.metadata

        await session.commit()
        await session.refresh(tag)

        logger.info(
            "Tag updated",
            tag_id=str(tag.id),
            tenant_id=str(auth_context.tenant_id),
        )

        from ..types.tag import tag_from_db_model

        return tag_from_db_model(tag)


async def delete_tag(info: strawberry.Info, id: UUID) -> bool:
    """
    Delete a tag.

    Requires authentication. Tag must belong to user's tenant.
    This will also remove all generation-tag associations.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        raise RuntimeError("Authentication required to delete a tag")

    async with get_async_session() as session:
        # Get the tag
        stmt = select(Tags).where(
            Tags.id == id,
            Tags.tenant_id == auth_context.tenant_id,
        )
        result = await session.execute(stmt)
        tag = result.scalar_one_or_none()

        if not tag:
            raise RuntimeError("Tag not found")

        # Delete the tag (cascade will handle generation_tags)
        await session.delete(tag)
        await session.commit()

        logger.info(
            "Tag deleted",
            tag_id=str(id),
            tenant_id=str(auth_context.tenant_id),
        )

        return True


async def _verify_generation_edit_access(
    session: AsyncSession,
    generation_id: UUID,
    auth_context: AuthContext,
) -> None:
    """Verify the user has edit access to a generation's board.

    Checks that the generation exists, belongs to the user's tenant,
    and the user is the board owner or an editor/admin member.
    """
    gen_stmt = select(Generations).where(
        Generations.id == generation_id,
        Generations.tenant_id == auth_context.tenant_id,
    )
    gen_result = await session.execute(gen_stmt)
    generation = gen_result.scalar_one_or_none()

    if not generation:
        raise RuntimeError("Generation not found")

    board_stmt = (
        select(Boards)
        .where(Boards.id == generation.board_id)
        .options(selectinload(Boards.board_members))
    )
    board_result = await session.execute(board_stmt)
    board = board_result.scalar_one_or_none()

    if not board or not can_access_board(board, auth_context):
        raise RuntimeError("Access denied to generation")

    is_owner = board.owner_id == auth_context.user_id
    is_editor = any(
        member.user_id == auth_context.user_id and member.role in {"editor", "admin"}
        for member in board.board_members
    )

    if not is_owner and not is_editor:
        raise RuntimeError(
            "Permission denied: only board owner or editor can modify generation tags"
        )


async def add_tag_to_generation(
    info: strawberry.Info,
    generation_id: UUID,
    tag_id: UUID,
) -> Tag:
    """
    Add a tag to a generation.

    Requires authentication and access to the generation's board.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        raise RuntimeError("Authentication required to add a tag to a generation")

    async with get_async_session() as session:
        await _verify_generation_edit_access(session, generation_id, auth_context)

        # Get the tag and verify it belongs to the same tenant
        tag_stmt = select(Tags).where(
            Tags.id == tag_id,
            Tags.tenant_id == auth_context.tenant_id,
        )
        tag_result = await session.execute(tag_stmt)
        tag = tag_result.scalar_one_or_none()

        if not tag:
            raise RuntimeError("Tag not found")

        # Check if association already exists
        existing_stmt = select(GenerationTags).where(
            GenerationTags.generation_id == generation_id,
            GenerationTags.tag_id == tag_id,
        )
        existing_result = await session.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            # Already tagged, just return the tag
            from ..types.tag import tag_from_db_model

            return tag_from_db_model(tag)

        # Create the association
        gen_tag = GenerationTags()
        gen_tag.generation_id = generation_id
        gen_tag.tag_id = tag_id

        session.add(gen_tag)
        await session.commit()

        # Refresh tag after commit to avoid expired state issues
        await session.refresh(tag)

        logger.info(
            "Tag added to generation",
            generation_id=str(generation_id),
            tag_id=str(tag_id),
            tag_name=tag.name,
        )

        from ..types.tag import tag_from_db_model

        return tag_from_db_model(tag)


async def remove_tag_from_generation(
    info: strawberry.Info,
    generation_id: UUID,
    tag_id: UUID,
) -> bool:
    """
    Remove a tag from a generation.

    Requires authentication and edit access to the generation's board.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        raise RuntimeError("Authentication required to remove a tag from a generation")

    async with get_async_session() as session:
        await _verify_generation_edit_access(session, generation_id, auth_context)

        # Find and delete the association
        assoc_stmt = select(GenerationTags).where(
            GenerationTags.generation_id == generation_id,
            GenerationTags.tag_id == tag_id,
        )
        assoc_result = await session.execute(assoc_stmt)
        assoc = assoc_result.scalar_one_or_none()

        if not assoc:
            raise RuntimeError("Tag is not associated with this generation")

        await session.delete(assoc)
        await session.commit()

        logger.info(
            "Tag removed from generation",
            generation_id=str(generation_id),
            tag_id=str(tag_id),
        )

        return True
