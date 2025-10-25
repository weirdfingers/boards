from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import strawberry
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from ...database.connection import get_async_session
from ...dbmodels import BoardMembers, Boards, Generations, Users
from ...generators.registry import registry as generator_registry
from ...jobs import repository as jobs_repo
from ...logging import get_logger
from ...workers.actors import process_generation
from ..access_control import can_access_board, get_auth_context_from_info

if TYPE_CHECKING:
    from ..mutations.root import CreateGenerationInput
    from ..types.board import Board
    from ..types.generation import ArtifactType, Generation, GenerationStatus
    from ..types.user import User

logger = get_logger(__name__)


# Query resolvers
async def resolve_generation_by_id(info: strawberry.Info, id: UUID) -> Generation | None:
    """
    Resolve a generation by its ID.

    Checks authorization: user must have access to the generation's board.
    """
    auth_context = await get_auth_context_from_info(info)
    if auth_context is None:
        return None

    async with get_async_session() as session:
        # Query generation
        stmt = select(Generations).where(Generations.id == id)
        result = await session.execute(stmt)
        gen = result.scalar_one_or_none()

        if not gen:
            logger.info("Generation not found", generation_id=str(id))
            return None

        # Check board access
        board_stmt = (
            select(Boards)
            .where(Boards.id == gen.board_id)
            .options(selectinload(Boards.board_members))
        )
        board_result = await session.execute(board_stmt)
        board = board_result.scalar_one_or_none()

        if not board or not can_access_board(board, auth_context):
            logger.info(
                "Access denied to generation",
                generation_id=str(id),
                board_id=str(gen.board_id),
                user_id=(
                    str(auth_context.user_id) if auth_context and auth_context.user_id else None
                ),
            )
            return None

        # Convert to GraphQL type
        from ..types.generation import ArtifactType, GenerationStatus
        from ..types.generation import Generation as GenerationType

        return GenerationType(
            id=gen.id,
            tenant_id=gen.tenant_id,
            board_id=gen.board_id,
            user_id=gen.user_id,
            generator_name=gen.generator_name,
            artifact_type=ArtifactType(gen.artifact_type),
            storage_url=gen.storage_url,
            thumbnail_url=gen.thumbnail_url,
            additional_files=gen.additional_files or [],
            input_params=gen.input_params or {},
            output_metadata=gen.output_metadata or {},
            parent_generation_id=gen.parent_generation_id,
            input_generation_ids=gen.input_generation_ids or [],
            external_job_id=gen.external_job_id,
            status=GenerationStatus(gen.status),
            progress=float(gen.progress or 0.0),
            error_message=gen.error_message,
            started_at=gen.started_at,
            completed_at=gen.completed_at,
            created_at=gen.created_at,
            updated_at=gen.updated_at,
        )


async def resolve_recent_generations(
    info: strawberry.Info,
    board_id: UUID | None,
    status: GenerationStatus | None,
    artifact_type: ArtifactType | None,
    limit: int,
    offset: int,
) -> list[Generation]:
    """
    Resolve recent generations with filtering.

    If board_id is None, returns generations from all boards the user has access to.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        logger.info("Unauthenticated access to recent_generations")
        return []

    async with get_async_session() as session:
        # Build base query
        generations_query = select(Generations)

        # Apply filters
        if board_id is not None:
            # Check access to specific board
            board_stmt = (
                select(Boards)
                .where(Boards.id == board_id)
                .options(selectinload(Boards.board_members))
            )
            board_result = await session.execute(board_stmt)
            board = board_result.scalar_one_or_none()

            if not board or not can_access_board(board, auth_context):
                logger.info(
                    "Access denied to board for recent generations",
                    board_id=str(board_id),
                    user_id=str(auth_context.user_id),
                )
                return []

            generations_query = generations_query.where(Generations.board_id == board_id)
        else:
            # Get all boards user has access to
            member_board_ids = select(BoardMembers.board_id).where(
                BoardMembers.user_id == auth_context.user_id
            )
            accessible_boards_condition = or_(
                Boards.owner_id == auth_context.user_id,
                Boards.id.in_(member_board_ids),
                Boards.is_public,
            )
            accessible_boards_stmt = select(Boards.id).where(accessible_boards_condition)
            accessible_boards_result = await session.execute(accessible_boards_stmt)
            accessible_board_ids = [row[0] for row in accessible_boards_result.all()]

            if not accessible_board_ids:
                return []

            generations_query = generations_query.where(
                Generations.board_id.in_(accessible_board_ids)
            )

        # Apply status filter
        if status is not None:
            generations_query = generations_query.where(Generations.status == status.value)

        # Apply artifact_type filter
        if artifact_type is not None:
            generations_query = generations_query.where(
                Generations.artifact_type == artifact_type.value
            )

        # Order by created_at DESC and apply pagination
        generations_query = (
            generations_query.order_by(Generations.created_at.desc()).limit(limit).offset(offset)
        )

        result = await session.execute(generations_query)
        generations = result.scalars().all()

        # Convert to GraphQL types
        from ..types.generation import ArtifactType as ArtifactTypeEnum
        from ..types.generation import Generation as GenerationType
        from ..types.generation import GenerationStatus as GenerationStatusEnum

        return [
            GenerationType(
                id=gen.id,
                tenant_id=gen.tenant_id,
                board_id=gen.board_id,
                user_id=gen.user_id,
                generator_name=gen.generator_name,
                artifact_type=ArtifactTypeEnum(gen.artifact_type),
                storage_url=gen.storage_url,
                thumbnail_url=gen.thumbnail_url,
                additional_files=gen.additional_files or [],
                input_params=gen.input_params or {},
                output_metadata=gen.output_metadata or {},
                parent_generation_id=gen.parent_generation_id,
                input_generation_ids=gen.input_generation_ids or [],
                external_job_id=gen.external_job_id,
                status=GenerationStatusEnum(gen.status),
                progress=float(gen.progress or 0.0),
                error_message=gen.error_message,
                started_at=gen.started_at,
                completed_at=gen.completed_at,
                created_at=gen.created_at,
                updated_at=gen.updated_at,
            )
            for gen in generations
        ]


# Field resolvers
async def resolve_generation_board(generation: Generation, info: strawberry.Info) -> Board:
    """Resolve the board this generation belongs to."""
    auth_context = await get_auth_context_from_info(info)

    async with get_async_session() as session:
        stmt = (
            select(Boards)
            .where(Boards.id == generation.board_id)
            .options(
                selectinload(Boards.owner),
                selectinload(Boards.board_members).selectinload(BoardMembers.user),
            )
        )
        result = await session.execute(stmt)
        board = result.scalar_one_or_none()

        if not board:
            raise RuntimeError("Generation board not found")

        if not can_access_board(board, auth_context):
            raise RuntimeError("Access denied to generation board")

        from ..types.board import Board as BoardType

        return BoardType(
            id=board.id,
            tenant_id=board.tenant_id,
            owner_id=board.owner_id,
            title=board.title,
            description=board.description,
            is_public=board.is_public,
            settings=board.settings or {},
            metadata=board.metadata_ or {},
            created_at=board.created_at,
            updated_at=board.updated_at,
        )


async def resolve_generation_user(generation: Generation, info: strawberry.Info) -> User:
    """Resolve the user who created this generation."""
    async with get_async_session() as session:
        stmt = select(Users).where(Users.id == generation.user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise RuntimeError("Generation user not found")

        from ..types.user import User as UserType

        return UserType(
            id=user.id,
            tenant_id=user.tenant_id,
            auth_provider=user.auth_provider,
            auth_subject=user.auth_subject,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


async def resolve_generation_parent(
    generation: Generation, info: strawberry.Info
) -> Generation | None:
    """Resolve the parent generation if any."""
    if not generation.parent_generation_id:
        return None

    auth_context = await get_auth_context_from_info(info)

    async with get_async_session() as session:
        # Query parent generation
        stmt = select(Generations).where(Generations.id == generation.parent_generation_id)
        result = await session.execute(stmt)
        parent = result.scalar_one_or_none()

        if not parent:
            logger.warning(
                "Parent generation not found",
                parent_id=str(generation.parent_generation_id),
            )
            return None

        # Check access to parent's board
        board_stmt = (
            select(Boards)
            .where(Boards.id == parent.board_id)
            .options(selectinload(Boards.board_members))
        )
        board_result = await session.execute(board_stmt)
        board = board_result.scalar_one_or_none()

        if not board or not can_access_board(board, auth_context):
            logger.info(
                "Access denied to parent generation",
                parent_id=str(generation.parent_generation_id),
            )
            return None

        # Convert to GraphQL type
        from ..types.generation import ArtifactType, GenerationStatus
        from ..types.generation import Generation as GenerationType

        return GenerationType(
            id=parent.id,
            tenant_id=parent.tenant_id,
            board_id=parent.board_id,
            user_id=parent.user_id,
            generator_name=parent.generator_name,
            artifact_type=ArtifactType(parent.artifact_type),
            storage_url=parent.storage_url,
            thumbnail_url=parent.thumbnail_url,
            additional_files=parent.additional_files or [],
            input_params=parent.input_params or {},
            output_metadata=parent.output_metadata or {},
            parent_generation_id=parent.parent_generation_id,
            input_generation_ids=parent.input_generation_ids or [],
            external_job_id=parent.external_job_id,
            status=GenerationStatus(parent.status),
            progress=float(parent.progress or 0.0),
            error_message=parent.error_message,
            started_at=parent.started_at,
            completed_at=parent.completed_at,
            created_at=parent.created_at,
            updated_at=parent.updated_at,
        )


async def resolve_generation_inputs(
    generation: Generation, info: strawberry.Info
) -> list[Generation]:  # noqa: E501
    """Resolve input generations used for this generation."""
    if not generation.input_generation_ids:
        return []

    auth_context = await get_auth_context_from_info(info)

    async with get_async_session() as session:
        # Query input generations
        stmt = select(Generations).where(Generations.id.in_(generation.input_generation_ids))
        result = await session.execute(stmt)
        inputs = result.scalars().all()

        # Filter by board access
        accessible_inputs = []
        for input_gen in inputs:
            board_stmt = (
                select(Boards)
                .where(Boards.id == input_gen.board_id)
                .options(selectinload(Boards.board_members))
            )
            board_result = await session.execute(board_stmt)
            board = board_result.scalar_one_or_none()

            if board and can_access_board(board, auth_context):
                accessible_inputs.append(input_gen)

        # Convert to GraphQL types
        from ..types.generation import ArtifactType, GenerationStatus
        from ..types.generation import Generation as GenerationType

        return [
            GenerationType(
                id=gen.id,
                tenant_id=gen.tenant_id,
                board_id=gen.board_id,
                user_id=gen.user_id,
                generator_name=gen.generator_name,
                artifact_type=ArtifactType(gen.artifact_type),
                storage_url=gen.storage_url,
                thumbnail_url=gen.thumbnail_url,
                additional_files=gen.additional_files or [],
                input_params=gen.input_params or {},
                output_metadata=gen.output_metadata or {},
                parent_generation_id=gen.parent_generation_id,
                input_generation_ids=gen.input_generation_ids or [],
                external_job_id=gen.external_job_id,
                status=GenerationStatus(gen.status),
                progress=float(gen.progress or 0.0),
                error_message=gen.error_message,
                started_at=gen.started_at,
                completed_at=gen.completed_at,
                created_at=gen.created_at,
                updated_at=gen.updated_at,
            )
            for gen in accessible_inputs
        ]


async def resolve_generation_children(
    generation: Generation, info: strawberry.Info
) -> list[Generation]:  # noqa: E501
    """Resolve child generations derived from this one."""
    auth_context = await get_auth_context_from_info(info)

    async with get_async_session() as session:
        # Query child generations
        stmt = select(Generations).where(Generations.parent_generation_id == generation.id)
        result = await session.execute(stmt)
        children = result.scalars().all()

        # Filter by board access
        accessible_children = []
        for child_gen in children:
            board_stmt = (
                select(Boards)
                .where(Boards.id == child_gen.board_id)
                .options(selectinload(Boards.board_members))
            )
            board_result = await session.execute(board_stmt)
            board = board_result.scalar_one_or_none()

            if board and can_access_board(board, auth_context):
                accessible_children.append(child_gen)

        # Convert to GraphQL types
        from ..types.generation import ArtifactType, GenerationStatus
        from ..types.generation import Generation as GenerationType

        return [
            GenerationType(
                id=gen.id,
                tenant_id=gen.tenant_id,
                board_id=gen.board_id,
                user_id=gen.user_id,
                generator_name=gen.generator_name,
                artifact_type=ArtifactType(gen.artifact_type),
                storage_url=gen.storage_url,
                thumbnail_url=gen.thumbnail_url,
                additional_files=gen.additional_files or [],
                input_params=gen.input_params or {},
                output_metadata=gen.output_metadata or {},
                parent_generation_id=gen.parent_generation_id,
                input_generation_ids=gen.input_generation_ids or [],
                external_job_id=gen.external_job_id,
                status=GenerationStatus(gen.status),
                progress=float(gen.progress or 0.0),
                error_message=gen.error_message,
                started_at=gen.started_at,
                completed_at=gen.completed_at,
                created_at=gen.created_at,
                updated_at=gen.updated_at,
            )
            for gen in accessible_children
        ]


# Mutation resolvers
async def create_generation(info: strawberry.Info, input: CreateGenerationInput) -> Generation:
    """
    Create a new generation and enqueue it for processing.

    Requires editor or owner role on the target board.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated or not auth_context.user_id:
        raise RuntimeError("Authentication required to create a generation")

    async with get_async_session() as session:
        # Check board access - require editor or owner role
        board_stmt = (
            select(Boards)
            .where(Boards.id == input.board_id)
            .options(selectinload(Boards.board_members))
        )
        board_result = await session.execute(board_stmt)
        board = board_result.scalar_one_or_none()

        if not board:
            raise RuntimeError("Board not found")

        # Check if user is owner or editor
        is_owner = board.owner_id == auth_context.user_id
        is_editor = any(
            member.user_id == auth_context.user_id and member.role in {"editor", "admin"}
            for member in board.board_members
        )

        if not is_owner and not is_editor:
            raise RuntimeError(
                "Permission denied: only board owner or editor can create generations"
            )

        # Validate generator exists
        generator = generator_registry.get(input.generator_name)
        if generator is None:
            raise RuntimeError(f"Unknown generator: {input.generator_name}")

        # Verify access to parent generation if provided
        if input.parent_generation_id:
            parent_stmt = select(Generations).where(Generations.id == input.parent_generation_id)
            parent_result = await session.execute(parent_stmt)
            parent_gen = parent_result.scalar_one_or_none()

            if not parent_gen:
                raise RuntimeError("Parent generation not found")

            # Check access to parent's board
            parent_board_stmt = (
                select(Boards)
                .where(Boards.id == parent_gen.board_id)
                .options(selectinload(Boards.board_members))
            )
            parent_board_result = await session.execute(parent_board_stmt)
            parent_board = parent_board_result.scalar_one_or_none()

            if not parent_board or not can_access_board(parent_board, auth_context):
                raise RuntimeError("Access denied to parent generation")

        # Verify access to input generations if provided
        if input.input_generation_ids:
            for input_gen_id in input.input_generation_ids:
                input_stmt = select(Generations).where(Generations.id == input_gen_id)
                input_result = await session.execute(input_stmt)
                input_gen = input_result.scalar_one_or_none()

                if not input_gen:
                    raise RuntimeError(f"Input generation {input_gen_id} not found")

                # Check access to input's board
                input_board_stmt = (
                    select(Boards)
                    .where(Boards.id == input_gen.board_id)
                    .options(selectinload(Boards.board_members))
                )
                input_board_result = await session.execute(input_board_stmt)
                input_board = input_board_result.scalar_one_or_none()

                if not input_board or not can_access_board(input_board, auth_context):
                    raise RuntimeError(f"Access denied to input generation {input_gen_id}")

        # Create generation record
        gen = await jobs_repo.create_generation(
            session,
            tenant_id=auth_context.tenant_id,
            board_id=input.board_id,
            user_id=auth_context.user_id,
            generator_name=input.generator_name,
            artifact_type=input.artifact_type.value,
            input_params=input.input_params,
        )

        # Update parent and input relationships if provided
        if input.parent_generation_id:
            gen.parent_generation_id = input.parent_generation_id
        if input.input_generation_ids:
            gen.input_generation_ids = input.input_generation_ids

        await session.commit()
        await session.refresh(gen)

        logger.info(
            "Generation created",
            generation_id=str(gen.id),
            board_id=str(input.board_id),
            user_id=str(auth_context.user_id),
            generator_name=input.generator_name,
        )

        # Enqueue job for processing
        message = process_generation.send(str(gen.id))
        logger.info(
            "Generation job enqueued",
            generation_id=str(gen.id),
            message_id=message.message_id,
            queue_name=message.queue_name,
        )

        # Convert to GraphQL type
        from ..types.generation import ArtifactType, GenerationStatus
        from ..types.generation import Generation as GenerationType

        return GenerationType(
            id=gen.id,
            tenant_id=gen.tenant_id,
            board_id=gen.board_id,
            user_id=gen.user_id,
            generator_name=gen.generator_name,
            artifact_type=ArtifactType(gen.artifact_type),
            storage_url=gen.storage_url,
            thumbnail_url=gen.thumbnail_url,
            additional_files=gen.additional_files or [],
            input_params=gen.input_params or {},
            output_metadata=gen.output_metadata or {},
            parent_generation_id=gen.parent_generation_id,
            input_generation_ids=gen.input_generation_ids or [],
            external_job_id=gen.external_job_id,
            status=GenerationStatus(gen.status),
            progress=float(gen.progress or 0.0),
            error_message=gen.error_message,
            started_at=gen.started_at,
            completed_at=gen.completed_at,
            created_at=gen.created_at,
            updated_at=gen.updated_at,
        )


async def cancel_generation(info: strawberry.Info, id: UUID) -> Generation:
    """
    Cancel a pending or processing generation.

    Requires ownership or editor role on the board.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        raise RuntimeError("Authentication required to cancel a generation")

    async with get_async_session() as session:
        # Query generation
        stmt = select(Generations).where(Generations.id == id)
        result = await session.execute(stmt)
        gen = result.scalar_one_or_none()

        if not gen:
            raise RuntimeError("Generation not found")

        # Check board access and permissions
        board_stmt = (
            select(Boards)
            .where(Boards.id == gen.board_id)
            .options(selectinload(Boards.board_members))
        )
        board_result = await session.execute(board_stmt)
        board = board_result.scalar_one_or_none()

        if not board:
            raise RuntimeError("Board not found")

        # Check authorization
        is_owner = board.owner_id == auth_context.user_id
        is_editor = any(
            member.user_id == auth_context.user_id and member.role in {"editor", "admin"}
            for member in board.board_members
        )
        is_creator = gen.user_id == auth_context.user_id

        # Owner can cancel any generation, editor can only cancel their own
        if not is_owner and not (is_editor and is_creator):
            raise RuntimeError(
                "Permission denied: only board owner or generation creator can cancel"
            )

        # Validate status
        if gen.status not in {"pending", "processing"}:
            raise RuntimeError(
                f"Cannot cancel generation with status '{gen.status}'. "
                "Only pending or processing generations can be cancelled."
            )

        # Update status to cancelled
        await jobs_repo.update_progress(
            session,
            id,
            status="cancelled",
            progress=float(gen.progress or 0.0),
            error_message="Cancelled by user",
        )
        await session.commit()

        # Refresh to get updated data
        await session.refresh(gen)

        logger.info(
            "Generation cancelled",
            generation_id=str(id),
            user_id=str(auth_context.user_id),
        )

        # Convert to GraphQL type
        from ..types.generation import ArtifactType, GenerationStatus
        from ..types.generation import Generation as GenerationType

        return GenerationType(
            id=gen.id,
            tenant_id=gen.tenant_id,
            board_id=gen.board_id,
            user_id=gen.user_id,
            generator_name=gen.generator_name,
            artifact_type=ArtifactType(gen.artifact_type),
            storage_url=gen.storage_url,
            thumbnail_url=gen.thumbnail_url,
            additional_files=gen.additional_files or [],
            input_params=gen.input_params or {},
            output_metadata=gen.output_metadata or {},
            parent_generation_id=gen.parent_generation_id,
            input_generation_ids=gen.input_generation_ids or [],
            external_job_id=gen.external_job_id,
            status=GenerationStatus(gen.status),
            progress=float(gen.progress or 0.0),
            error_message=gen.error_message,
            started_at=gen.started_at,
            completed_at=gen.completed_at,
            created_at=gen.created_at,
            updated_at=gen.updated_at,
        )


async def delete_generation(info: strawberry.Info, id: UUID) -> bool:
    """
    Delete a generation and its associated storage artifacts.

    Requires ownership or editor role on the board.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        raise RuntimeError("Authentication required to delete a generation")

    async with get_async_session() as session:
        # Query generation
        stmt = select(Generations).where(Generations.id == id)
        result = await session.execute(stmt)
        gen = result.scalar_one_or_none()

        if not gen:
            raise RuntimeError("Generation not found")

        # Check board access and permissions
        board_stmt = (
            select(Boards)
            .where(Boards.id == gen.board_id)
            .options(selectinload(Boards.board_members))
        )
        board_result = await session.execute(board_stmt)
        board = board_result.scalar_one_or_none()

        if not board:
            raise RuntimeError("Board not found")

        # Check authorization
        is_owner = board.owner_id == auth_context.user_id
        is_editor = any(
            member.user_id == auth_context.user_id and member.role in {"editor", "admin"}
            for member in board.board_members
        )
        is_creator = gen.user_id == auth_context.user_id

        # Owner can delete any generation, editor can only delete their own
        if not is_owner and not (is_editor and is_creator):
            raise RuntimeError(
                "Permission denied: only board owner or generation creator can delete"
            )

        # Delete storage artifacts
        # TODO: Full storage deletion requires storage_key and storage_provider fields
        # to be added to the Generations table. For now, we log the deletion intent.
        # Once those fields are added, use: await storage_manager.delete_artifact(key, provider)

        if gen.storage_url or gen.thumbnail_url or gen.additional_files:
            logger.info(
                "Storage artifact deletion",
                generation_id=str(id),
                has_storage_url=bool(gen.storage_url),
                has_thumbnail=bool(gen.thumbnail_url),
                additional_files_count=(len(gen.additional_files) if gen.additional_files else 0),
            )
            logger.warning(
                "Storage artifact deletion not yet implemented - requires storage_key and "
                "storage_provider fields in Generations table",
                generation_id=str(id),
            )

        # Delete generation from database
        await session.delete(gen)
        await session.commit()

        logger.info(
            "Generation deleted",
            generation_id=str(id),
            user_id=str(auth_context.user_id),
        )

        return True


async def regenerate(info: strawberry.Info, id: UUID) -> Generation:
    """
    Regenerate from an existing generation.

    Creates a new generation with the same inputs and sets the original as parent.
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated or not auth_context.user_id:
        raise RuntimeError("Authentication required to regenerate")

    async with get_async_session() as session:
        # Query original generation
        stmt = select(Generations).where(Generations.id == id)
        result = await session.execute(stmt)
        original = result.scalar_one_or_none()

        if not original:
            raise RuntimeError("Original generation not found")

        # Check board access - require editor or owner role
        board_stmt = (
            select(Boards)
            .where(Boards.id == original.board_id)
            .options(selectinload(Boards.board_members))
        )
        board_result = await session.execute(board_stmt)
        board = board_result.scalar_one_or_none()

        if not board:
            raise RuntimeError("Board not found")

        # Check if user is owner or editor
        is_owner = board.owner_id == auth_context.user_id
        is_editor = any(
            member.user_id == auth_context.user_id and member.role in {"editor", "admin"}
            for member in board.board_members
        )

        if not is_owner and not is_editor:
            raise RuntimeError("Permission denied: only board owner or editor can regenerate")

        # Validate generator still exists
        generator = generator_registry.get(original.generator_name)
        if generator is None:
            raise RuntimeError(f"Generator '{original.generator_name}' is no longer available")

        # Create new generation with copied inputs
        new_gen = await jobs_repo.create_generation(
            session,
            tenant_id=original.tenant_id,
            board_id=original.board_id,
            user_id=auth_context.user_id,
            generator_name=original.generator_name,
            artifact_type=original.artifact_type,
            input_params=original.input_params or {},
        )

        # Set parent and copy input relationships
        new_gen.parent_generation_id = original.id
        new_gen.input_generation_ids = original.input_generation_ids or []

        await session.commit()
        await session.refresh(new_gen)

        logger.info(
            "Generation regenerated",
            new_generation_id=str(new_gen.id),
            original_generation_id=str(id),
            user_id=str(auth_context.user_id),
        )

        # Enqueue job for processing
        process_generation.send(str(new_gen.id))
        logger.info("Regeneration job enqueued", generation_id=str(new_gen.id))

        # Convert to GraphQL type
        from ..types.generation import ArtifactType, GenerationStatus
        from ..types.generation import Generation as GenerationType

        return GenerationType(
            id=new_gen.id,
            tenant_id=new_gen.tenant_id,
            board_id=new_gen.board_id,
            user_id=new_gen.user_id,
            generator_name=new_gen.generator_name,
            artifact_type=ArtifactType(new_gen.artifact_type),
            storage_url=new_gen.storage_url,
            thumbnail_url=new_gen.thumbnail_url,
            additional_files=new_gen.additional_files or [],
            input_params=new_gen.input_params or {},
            output_metadata=new_gen.output_metadata or {},
            parent_generation_id=new_gen.parent_generation_id,
            input_generation_ids=new_gen.input_generation_ids or [],
            external_job_id=new_gen.external_job_id,
            status=GenerationStatus(new_gen.status),
            progress=float(new_gen.progress or 0.0),
            error_message=new_gen.error_message,
            started_at=new_gen.started_at,
            completed_at=new_gen.completed_at,
            created_at=new_gen.created_at,
            updated_at=new_gen.updated_at,
        )
