"""
Lineage resolvers for ancestry and descendants tracking
"""

from uuid import UUID

import strawberry
from sqlalchemy import select, text

from ...database.connection import get_async_session
from ...dbmodels import Boards, Generations
from ...logging import get_logger
from ..access_control import can_access_board, get_auth_context_from_info
from ..types.generation import (
    AncestryNode,
    ArtifactLineage,
    ArtifactType,
    DescendantNode,
    Generation,
    GenerationStatus,
)

logger = get_logger(__name__)


def convert_db_to_graphql_generation(gen: Generations) -> Generation:
    """Convert a database Generation model to GraphQL Generation type."""
    return Generation(
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
        external_job_id=gen.external_job_id,
        status=GenerationStatus(gen.status),
        progress=float(gen.progress or 0.0),
        error_message=gen.error_message,
        started_at=gen.started_at,
        completed_at=gen.completed_at,
        created_at=gen.created_at,
        updated_at=gen.updated_at,
    )


async def resolve_input_artifacts(
    generation: Generation, info: strawberry.Info
) -> list[ArtifactLineage]:
    """Resolve input artifacts with role metadata."""
    async with get_async_session() as session:
        # Query the generation to get input_artifacts
        stmt = select(Generations).where(Generations.id == generation.id)
        result = await session.execute(stmt)
        gen = result.scalar_one_or_none()

        if not gen or not gen.input_artifacts:
            return []

        # Build ArtifactLineage objects
        lineages = []
        for artifact_data in gen.input_artifacts:
            lineages.append(
                ArtifactLineage(
                    generation_id=UUID(artifact_data["generation_id"]),
                    role=artifact_data["role"],
                    artifact_type=ArtifactType(artifact_data["artifact_type"]),
                )
            )

        return lineages


async def resolve_generation_by_id(info: strawberry.Info, generation_id: UUID) -> Generation | None:
    """Helper to resolve a generation by ID with access control."""
    auth_context = await get_auth_context_from_info(info)
    if auth_context is None:
        return None

    async with get_async_session() as session:
        # Query generation
        stmt = select(Generations).where(Generations.id == generation_id)
        result = await session.execute(stmt)
        gen = result.scalar_one_or_none()

        if not gen:
            return None

        # Check board access
        board_stmt = select(Boards).where(Boards.id == gen.board_id)
        board_result = await session.execute(board_stmt)
        board = board_result.scalar_one_or_none()

        if not board or not can_access_board(board, auth_context):
            return None

        return convert_db_to_graphql_generation(gen)


async def resolve_ancestry(
    generation: Generation, info: strawberry.Info, max_depth: int = 25
) -> AncestryNode:
    """Build recursive ancestry tree using recursive CTE."""
    auth_context = await get_auth_context_from_info(info)

    if not auth_context:
        # Return empty tree if not authenticated
        return AncestryNode(generation=generation, depth=0, role=None, parents=[])

    async with get_async_session() as session:
        # Use recursive CTE to fetch entire ancestry tree in one query
        cte_query = text("""
            WITH RECURSIVE ancestry_tree AS (
                -- Base case: starting generation
                SELECT
                    id,
                    tenant_id,
                    board_id,
                    user_id,
                    generator_name,
                    artifact_type,
                    storage_url,
                    thumbnail_url,
                    additional_files,
                    input_params,
                    output_metadata,
                    external_job_id,
                    status,
                    progress,
                    error_message,
                    started_at,
                    completed_at,
                    created_at,
                    updated_at,
                    input_artifacts,
                    0 as depth,
                    NULL::text as role,
                    ARRAY[id] as path  -- cycle detection
                FROM boards.generations
                WHERE id = :gen_id AND tenant_id = :tenant_id

                UNION ALL

                -- Recursive case: parent generations
                SELECT
                    g.id,
                    g.tenant_id,
                    g.board_id,
                    g.user_id,
                    g.generator_name,
                    g.artifact_type,
                    g.storage_url,
                    g.thumbnail_url,
                    g.additional_files,
                    g.input_params,
                    g.output_metadata,
                    g.external_job_id,
                    g.status,
                    g.progress,
                    g.error_message,
                    g.started_at,
                    g.completed_at,
                    g.created_at,
                    g.updated_at,
                    g.input_artifacts,
                    at.depth + 1,
                    artifact->>'role' as role,
                    at.path || g.id
                FROM ancestry_tree at
                CROSS JOIN LATERAL jsonb_array_elements(at.input_artifacts) AS artifact
                JOIN boards.generations g ON
                    g.id = (artifact->>'generation_id')::uuid
                    AND NOT (g.id = ANY(at.path))  -- prevent cycles
                    AND at.depth < :max_depth
                WHERE g.tenant_id = :tenant_id
            )
            SELECT * FROM ancestry_tree ORDER BY depth, id
        """)

        result = await session.execute(
            cte_query,
            {
                "gen_id": generation.id,
                "tenant_id": auth_context.tenant_id,
                "max_depth": max_depth,
            },
        )
        rows = result.fetchall()

        if not rows:
            # Return root node with no parents
            return AncestryNode(generation=generation, depth=0, role=None, parents=[])

        # Build tree from flat results
        nodes_by_id: dict[UUID, tuple[Generations, int, str | None]] = {}
        for row in rows:
            gen_obj = Generations()
            gen_obj.id = row.id
            gen_obj.tenant_id = row.tenant_id
            gen_obj.board_id = row.board_id
            gen_obj.user_id = row.user_id
            gen_obj.generator_name = row.generator_name
            gen_obj.artifact_type = row.artifact_type
            gen_obj.storage_url = row.storage_url
            gen_obj.thumbnail_url = row.thumbnail_url
            gen_obj.additional_files = row.additional_files
            gen_obj.input_params = row.input_params
            gen_obj.output_metadata = row.output_metadata
            gen_obj.external_job_id = row.external_job_id
            gen_obj.status = row.status
            gen_obj.progress = row.progress
            gen_obj.error_message = row.error_message
            gen_obj.started_at = row.started_at
            gen_obj.completed_at = row.completed_at
            gen_obj.created_at = row.created_at
            gen_obj.updated_at = row.updated_at
            gen_obj.input_artifacts = row.input_artifacts
            nodes_by_id[row.id] = (gen_obj, row.depth, row.role)

        # Build tree structure recursively
        def build_node(gen_id: UUID) -> AncestryNode:
            gen_obj, depth, role = nodes_by_id[gen_id]
            gen_graphql = convert_db_to_graphql_generation(gen_obj)

            # Find parent nodes
            parent_nodes = []
            if gen_obj.input_artifacts:
                for artifact_data in gen_obj.input_artifacts:
                    parent_id = UUID(artifact_data["generation_id"])
                    if parent_id in nodes_by_id:
                        parent_nodes.append(build_node(parent_id))

            return AncestryNode(
                generation=gen_graphql, depth=depth, role=role, parents=parent_nodes
            )

        return build_node(generation.id)


async def resolve_descendants(
    generation: Generation, info: strawberry.Info, max_depth: int = 25
) -> DescendantNode:
    """Build recursive descendants tree using recursive CTE."""
    auth_context = await get_auth_context_from_info(info)

    if not auth_context:
        # Return empty tree if not authenticated
        return DescendantNode(generation=generation, depth=0, role=None, children=[])

    async with get_async_session() as session:
        # Use recursive CTE to fetch entire descendants tree in one query
        cte_query = text("""
            WITH RECURSIVE descendants_tree AS (
                -- Base case: starting generation
                SELECT
                    id,
                    tenant_id,
                    board_id,
                    user_id,
                    generator_name,
                    artifact_type,
                    storage_url,
                    thumbnail_url,
                    additional_files,
                    input_params,
                    output_metadata,
                    external_job_id,
                    status,
                    progress,
                    error_message,
                    started_at,
                    completed_at,
                    created_at,
                    updated_at,
                    input_artifacts,
                    0 as depth,
                    NULL::text as role,
                    NULL::uuid as parent_id,
                    ARRAY[id] as path  -- cycle detection
                FROM boards.generations
                WHERE id = :gen_id AND tenant_id = :tenant_id

                UNION ALL

                -- Recursive case: child generations
                SELECT
                    g.id,
                    g.tenant_id,
                    g.board_id,
                    g.user_id,
                    g.generator_name,
                    g.artifact_type,
                    g.storage_url,
                    g.thumbnail_url,
                    g.additional_files,
                    g.input_params,
                    g.output_metadata,
                    g.external_job_id,
                    g.status,
                    g.progress,
                    g.error_message,
                    g.started_at,
                    g.completed_at,
                    g.created_at,
                    g.updated_at,
                    g.input_artifacts,
                    dt.depth + 1,
                    artifact->>'role' as role,
                    dt.id as parent_id,
                    dt.path || g.id
                FROM boards.generations g
                CROSS JOIN LATERAL jsonb_array_elements(g.input_artifacts) AS artifact
                JOIN descendants_tree dt ON
                    dt.id = (artifact->>'generation_id')::uuid
                    AND NOT (g.id = ANY(dt.path))  -- prevent cycles
                    AND dt.depth < :max_depth
                WHERE g.tenant_id = :tenant_id
            )
            SELECT * FROM descendants_tree ORDER BY depth, id
        """)

        result = await session.execute(
            cte_query,
            {
                "gen_id": generation.id,
                "tenant_id": auth_context.tenant_id,
                "max_depth": max_depth,
            },
        )
        rows = result.fetchall()

        if not rows:
            # Return root node with no children
            return DescendantNode(generation=generation, depth=0, role=None, children=[])

        # Build tree from flat results
        nodes_by_id: dict[UUID, tuple[Generations, int, str | None, UUID | None]] = {}
        for row in rows:
            gen_obj = Generations()
            gen_obj.id = row.id
            gen_obj.tenant_id = row.tenant_id
            gen_obj.board_id = row.board_id
            gen_obj.user_id = row.user_id
            gen_obj.generator_name = row.generator_name
            gen_obj.artifact_type = row.artifact_type
            gen_obj.storage_url = row.storage_url
            gen_obj.thumbnail_url = row.thumbnail_url
            gen_obj.additional_files = row.additional_files
            gen_obj.input_params = row.input_params
            gen_obj.output_metadata = row.output_metadata
            gen_obj.external_job_id = row.external_job_id
            gen_obj.status = row.status
            gen_obj.progress = row.progress
            gen_obj.error_message = row.error_message
            gen_obj.started_at = row.started_at
            gen_obj.completed_at = row.completed_at
            gen_obj.created_at = row.created_at
            gen_obj.updated_at = row.updated_at
            gen_obj.input_artifacts = row.input_artifacts
            nodes_by_id[row.id] = (gen_obj, row.depth, row.role, row.parent_id)

        # Build tree structure recursively
        def build_node(gen_id: UUID) -> DescendantNode:
            gen_obj, depth, role, _ = nodes_by_id[gen_id]
            gen_graphql = convert_db_to_graphql_generation(gen_obj)

            # Find child nodes (nodes that have this as parent_id)
            child_nodes = []
            for child_id, (_, _, _, parent_id) in nodes_by_id.items():
                if parent_id == gen_id:
                    child_nodes.append(build_node(child_id))

            return DescendantNode(
                generation=gen_graphql, depth=depth, role=role, children=child_nodes
            )

        return build_node(generation.id)
