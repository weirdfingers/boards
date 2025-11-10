# Artifact Lineage Design

## Overview

This document outlines the design for tracking and querying artifact lineage in the Boards system. Artifacts (Generations) can use other artifacts as inputs, and we need to track these relationships with metadata about the role each input artifact played.

## Current State

### Database Schema (Generations table)

The `Generations` model already has some lineage support:

```python
# From packages/backend/src/boards/dbmodels/__init__.py
class Generations(Base):
    # ... other fields ...

    parent_generation_id: Mapped[UUID | None] = mapped_column(Uuid)
    input_generation_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(Uuid()), server_default=text("'{}'::uuid[]")
    )

    # Relationships
    parent_generation: Mapped["Generations | None"] = relationship(...)
    parent_generation_reverse: Mapped[list["Generations"]] = relationship(...)
```

**Limitations:**
- `parent_generation_id`: Single-parent tracking (appears to be for "regenerate" functionality)
- `input_generation_ids`: List of UUIDs with NO metadata about the role each input played
- **No way to distinguish** that one artifact was a "first_frame" vs "last_frame" vs "source_image"

### GraphQL API

Current GraphQL types expose lineage but without role information:

```python
# From packages/backend/src/boards/graphql/types/generation.py
@strawberry.type
class Generation:
    # ... other fields ...
    parent_generation_id: UUID | None
    input_generation_ids: list[UUID]

    # Field resolvers
    parent_generation: Generation | None  # Resolves single parent
    input_generations: list[Generation]    # Resolves input array
    children: list[Generation]            # Resolves descendants
```

### Generator Input Schema

Generators declare their inputs using Pydantic models with artifact fields:

```python
# Example from fal/video/veo31_first_last_frame_to_video.py
class Veo31FirstLastFrameToVideoInput(BaseModel):
    first_frame: ImageArtifact = Field(...)
    last_frame: ImageArtifact = Field(...)
    prompt: str = Field(...)
    # ...
```

**Key Insight:** The field name IS the role! (`first_frame`, `last_frame`, etc.)

The system uses introspection via `extract_artifact_fields()` to automatically detect these artifact fields and resolve generation IDs to artifact objects.

## Requirements

Based on the user's responses:

1. **Lineage direction**: Ancestry tracking (parents → grandparents → ...). Descendants less critical.
2. **Relationships**: Many-to-many (artifact can have multiple parents, parent can have multiple children)
3. **Role metadata**: Track the specific role each parent artifact played (e.g., "first_frame", "last_frame", "source_image")
4. **Query patterns**: Support all of:
   - Complete ancestry tree (recursive ancestors)
   - All artifacts derived from this one (descendants)
   - Generation history with parameters
5. **Depth**: Up to ~25 levels of ancestry
6. **Backwards compatibility**: Avoid requiring changes to existing generators
7. **Asynchronous queries**: Performance not critical

## Proposed Solution

### 1. Database Schema Changes

#### Option A: JSONB field for structured lineage (RECOMMENDED)

Add a new `input_artifacts` JSONB field to store structured lineage metadata:

```python
# In packages/backend/src/boards/dbmodels/__init__.py

class Generations(Base):
    # ... existing fields ...

    # DEPRECATED: Keep for backwards compatibility initially
    input_generation_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(Uuid()), server_default=text("'{}'::uuid[]")
    )

    # NEW: Structured lineage with role metadata
    input_artifacts: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        comment="Structured lineage: [{generation_id: UUID, role: str, artifact_type: str}, ...]"
    )
```

**JSONB structure:**
```json
[
  {
    "generation_id": "uuid-1",
    "role": "first_frame",
    "artifact_type": "image"
  },
  {
    "generation_id": "uuid-2",
    "role": "last_frame",
    "artifact_type": "image"
  }
]
```

**Pros:**
- Flexible schema (can add more metadata later without migrations)
- Postgres JSONB is efficient and indexable
- Easy to query with JSONB operators
- Can store additional metadata (timestamp, parameters, etc.)

**Cons:**
- Less type-safe than normalized schema
- Slightly more complex queries

#### Option B: Separate lineage junction table

Create a dedicated `generation_lineage` table:

```python
class GenerationLineage(Base):
    __tablename__ = "generation_lineage"

    id: Mapped[UUID] = mapped_column(Uuid, server_default=text("uuid_generate_v4()"))
    child_generation_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("generations.id", ondelete="CASCADE"))
    parent_generation_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("generations.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        Index("idx_lineage_child", "child_generation_id"),
        Index("idx_lineage_parent", "parent_generation_id"),
        # Composite index for ancestry queries
        Index("idx_lineage_child_parent", "child_generation_id", "parent_generation_id"),
    )
```

**Pros:**
- Normalized, type-safe schema
- Natural fit for relational queries
- Easier to add foreign key constraints

**Cons:**
- More tables to manage
- Requires joins for queries
- Less flexible (requires migration for schema changes)

#### Recommendation: **Option A (JSONB)**

The JSONB approach provides the best balance of flexibility, performance, and simplicity for this use case:
- Lineage relationships are tightly coupled to the generation
- We may want to add more metadata in the future
- Postgres JSONB performance is excellent
- Simpler migration path (just add one column)

### 2. Alembic Migration

```python
# alembic/versions/YYYYMMDD_HHMMSS_add_input_artifacts_lineage.py

"""Add input_artifacts field for lineage tracking with role metadata

Revision ID: xxxxx
Revises: yyyyy
Create Date: YYYY-MM-DD HH:MM:SS
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

def upgrade() -> None:
    # Add input_artifacts JSONB column
    op.add_column(
        'generations',
        sa.Column(
            'input_artifacts',
            JSONB,
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="Structured lineage: [{generation_id: UUID, role: str, artifact_type: str}, ...]"
        )
    )

    # Migrate existing data from input_generation_ids to input_artifacts
    # For backwards compatibility, use role="input" for legacy data
    op.execute("""
        UPDATE generations
        SET input_artifacts = (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'generation_id', gen_id::text,
                    'role', 'input',
                    'artifact_type', g.artifact_type
                )
            )
            FROM unnest(input_generation_ids) AS gen_id
            LEFT JOIN generations g ON g.id = gen_id
        )
        WHERE input_generation_ids IS NOT NULL
        AND array_length(input_generation_ids, 1) > 0
    """)

    # Add GIN index for JSONB queries
    op.execute("""
        CREATE INDEX idx_generations_input_artifacts_gin
        ON generations USING GIN (input_artifacts)
    """)

def downgrade() -> None:
    op.drop_index('idx_generations_input_artifacts_gin', table_name='generations')
    op.drop_column('generations', 'input_artifacts')
```

### 3. GraphQL API Changes

#### New GraphQL Types

```python
# packages/backend/src/boards/graphql/types/generation.py

@strawberry.type
class ArtifactLineage:
    """Represents a single input artifact relationship with role metadata."""

    generation_id: UUID
    role: str  # Field name from generator input schema (e.g., "first_frame", "source_image")
    artifact_type: ArtifactType

    # Resolved generation object
    @strawberry.field
    async def generation(self, info: strawberry.Info) -> Generation | None:
        """Resolve the full generation object for this input."""
        from ..resolvers.generation import resolve_generation_by_id
        return await resolve_generation_by_id(info, self.generation_id)


@strawberry.type
class AncestryNode:
    """Represents a node in the ancestry tree."""

    generation: Generation
    depth: int  # Distance from query origin (0 = self, 1 = parent, 2 = grandparent, ...)
    role: str | None  # Role this artifact played in its child (None for query origin)
    parents: list["AncestryNode"]  # Recursive ancestry


@strawberry.type
class Generation:
    # ... existing fields ...

    # EXISTING - keep for backwards compatibility
    parent_generation_id: UUID | None
    input_generation_ids: list[UUID]

    # NEW - structured lineage with roles
    @strawberry.field
    async def input_artifacts(self, info: strawberry.Info) -> list[ArtifactLineage]:
        """Get input artifacts with role metadata."""
        from ..resolvers.generation import resolve_input_artifacts
        return await resolve_input_artifacts(self, info)

    # NEW - recursive ancestry query
    @strawberry.field
    async def ancestry(
        self,
        info: strawberry.Info,
        max_depth: int = 25
    ) -> AncestryNode:
        """Get complete ancestry tree up to max_depth levels."""
        from ..resolvers.generation import resolve_ancestry
        return await resolve_ancestry(self, info, max_depth)

    # NEW - find all descendants
    @strawberry.field
    async def descendants(
        self,
        info: strawberry.Info,
        max_depth: int = 25
    ) -> list[Generation]:
        """Get all artifacts derived from this one."""
        from ..resolvers.generation import resolve_all_descendants
        return await resolve_all_descendants(self, info, max_depth)

    # EXISTING - direct children (keep for backwards compatibility)
    @strawberry.field
    async def children(self, info: strawberry.Info) -> list[Generation]:
        """Get direct children (one level down)."""
        from ..resolvers.generation import resolve_generation_children
        return await resolve_generation_children(self, info)
```

#### New GraphQL Resolvers

```python
# packages/backend/src/boards/graphql/resolvers/generation.py

async def resolve_input_artifacts(
    generation: Generation,
    info: strawberry.Info
) -> list[ArtifactLineage]:
    """Resolve input artifacts with role metadata."""
    # Parse input_artifacts JSONB field
    if not generation.input_artifacts:
        return []

    # Build ArtifactLineage objects
    lineages = []
    for artifact_data in generation.input_artifacts:
        lineages.append(
            ArtifactLineage(
                generation_id=UUID(artifact_data["generation_id"]),
                role=artifact_data["role"],
                artifact_type=ArtifactType(artifact_data["artifact_type"])
            )
        )

    return lineages


async def resolve_ancestry(
    generation: Generation,
    info: strawberry.Info,
    max_depth: int = 25
) -> AncestryNode:
    """Build recursive ancestry tree."""
    auth_context = await get_auth_context_from_info(info)

    async with get_async_session() as session:
        async def build_node(
            gen_id: UUID,
            depth: int,
            role: str | None = None
        ) -> AncestryNode | None:
            """Recursively build ancestry tree."""
            if depth > max_depth:
                return None

            # Query generation
            stmt = select(Generations).where(Generations.id == gen_id)
            result = await session.execute(stmt)
            gen = result.scalar_one_or_none()

            if not gen:
                return None

            # Check access (simplified - should use can_access_board)
            if gen.tenant_id != auth_context.tenant_id:
                return None

            # Convert to GraphQL Generation
            gen_graphql = convert_to_graphql_generation(gen)

            # Recursively build parent nodes
            parent_nodes = []
            if gen.input_artifacts:
                for artifact_data in gen.input_artifacts:
                    parent_id = UUID(artifact_data["generation_id"])
                    parent_role = artifact_data["role"]

                    parent_node = await build_node(
                        parent_id,
                        depth + 1,
                        parent_role
                    )
                    if parent_node:
                        parent_nodes.append(parent_node)

            return AncestryNode(
                generation=gen_graphql,
                depth=depth,
                role=role,
                parents=parent_nodes
            )

        return await build_node(generation.id, depth=0)


async def resolve_all_descendants(
    generation: Generation,
    info: strawberry.Info,
    max_depth: int = 25
) -> list[Generation]:
    """Find all descendants recursively."""
    auth_context = await get_auth_context_from_info(info)

    async with get_async_session() as session:
        descendants = []
        visited = set()

        async def find_children(gen_id: UUID, depth: int):
            """Recursively find all descendants."""
            if depth > max_depth or gen_id in visited:
                return

            visited.add(gen_id)

            # Query for generations that have this one as an input
            # Use JSONB containment operator
            stmt = select(Generations).where(
                Generations.input_artifacts.op('@>')(
                    sa.text(f"'[{{"generation_id": "{gen_id}"}}]'::jsonb")
                )
            )
            result = await session.execute(stmt)
            children = result.scalars().all()

            for child in children:
                # Check access
                if child.tenant_id == auth_context.tenant_id:
                    descendants.append(convert_to_graphql_generation(child))
                    await find_children(child.id, depth + 1)

        await find_children(generation.id, 0)
        return descendants
```

### 4. Backend Changes for Automatic Lineage Tracking

The key insight is: **we can automatically capture lineage without changing generators!**

#### Modify artifact resolution to capture lineage

```python
# packages/backend/src/boards/generators/artifact_resolution.py

async def resolve_input_artifacts(
    input_params: dict[str, Any],
    schema: type[BaseModel],
    session: AsyncSession,
    tenant_id: UUID,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Resolve generation IDs to artifact objects in input parameters.

    NOW RETURNS: (resolved_params, lineage_metadata)
    """
    # Automatically extract artifact fields from schema
    artifact_field_map = extract_artifact_fields(schema)

    if not artifact_field_map:
        return input_params, []

    resolved_params = dict(input_params)
    lineage_metadata = []  # NEW: Track lineage as we resolve

    for field_name, (artifact_class, expects_list) in artifact_field_map.items():
        field_value = resolved_params.get(field_name)

        if field_value is None:
            continue

        # ... existing resolution logic ...

        # NEW: Capture lineage metadata
        artifact_type_name = _get_artifact_type_name(artifact_class)

        for gen_id in generation_ids:
            lineage_metadata.append({
                "generation_id": str(gen_id),
                "role": field_name,  # Field name IS the role!
                "artifact_type": artifact_type_name
            })

        # ... rest of existing logic ...

    return resolved_params, lineage_metadata
```

#### Update worker actor to store lineage

```python
# packages/backend/src/boards/workers/actors.py

@dramatiq.actor
async def process_generation(generation_id: str):
    """Process a generation job."""
    async with get_async_session() as session:
        generation = await jobs_repo.get_generation(session, generation_id)

        # ... existing code ...

        # Resolve artifacts WITH lineage capture
        resolved_params, lineage_metadata = await resolve_input_artifacts(
            generation.input_params,
            input_schema,
            session,
            generation.tenant_id,
        )

        # Store lineage metadata
        if lineage_metadata:
            generation.input_artifacts = lineage_metadata
            await session.commit()

        # ... rest of existing code ...
```

### 5. Frontend Changes

#### Update GraphQL Operations

```typescript
// packages/frontend/src/graphql/operations.ts

// Fragment for lineage metadata
export const ArtifactLineageFragment = gql`
  fragment ArtifactLineageFragment on ArtifactLineage {
    generation_id
    role
    artifact_type
    generation {
      ...GenerationFragment
    }
  }
`;

// Fragment for ancestry node
export const AncestryNodeFragment = gql`
  fragment AncestryNodeFragment on AncestryNode {
    depth
    role
    generation {
      ...GenerationFragment
    }
    parents {
      depth
      role
      generation {
        ...GenerationFragment
      }
      # Limit recursion depth to prevent huge queries
    }
  }
`;

// Update Generation fragment to include new fields
export const GenerationFragment = gql`
  fragment GenerationFragment on Generation {
    id
    # ... existing fields ...

    # NEW fields
    input_artifacts {
      ...ArtifactLineageFragment
    }
  }
`;

// Query for ancestry tree
export const GetAncestryQuery = gql`
  query GetAncestry($id: UUID!, $maxDepth: Int = 25) {
    generation(id: $id) {
      ancestry(maxDepth: $maxDepth) {
        ...AncestryNodeFragment
      }
    }
  }
`;

// Query for descendants
export const GetDescendantsQuery = gql`
  query GetDescendants($id: UUID!, $maxDepth: Int = 25) {
    generation(id: $id) {
      descendants(maxDepth: $maxDepth) {
        ...GenerationFragment
      }
    }
  }
`;
```

#### New React Hooks

```typescript
// packages/frontend/src/hooks/useArtifactLineage.ts

export interface ArtifactLineage {
  generation_id: string;
  role: string;
  artifact_type: string;
  generation?: Generation;
}

export interface AncestryNode {
  generation: Generation;
  depth: number;
  role?: string;
  parents: AncestryNode[];
}

export function useArtifactLineage(generationId: string) {
  const [result] = useQuery({
    query: GetGenerationQuery,
    variables: { id: generationId },
  });

  return {
    inputArtifacts: result.data?.generation?.input_artifacts ?? [],
    loading: result.fetching,
    error: result.error,
  };
}

export function useAncestry(generationId: string, maxDepth: number = 25) {
  const [result] = useQuery({
    query: GetAncestryQuery,
    variables: { id: generationId, maxDepth },
  });

  return {
    ancestry: result.data?.generation?.ancestry,
    loading: result.fetching,
    error: result.error,
  };
}

export function useDescendants(generationId: string, maxDepth: number = 25) {
  const [result] = useQuery({
    query: GetDescendantsQuery,
    variables: { id: generationId, maxDepth },
  });

  return {
    descendants: result.data?.generation?.descendants ?? [],
    loading: result.fetching,
    error: result.error,
  };
}
```

### 6. Migration Strategy & Backwards Compatibility

#### Phase 1: Add new field (Non-breaking)
1. Add `input_artifacts` JSONB field with migration
2. Migrate existing `input_generation_ids` data with role="input"
3. Keep both fields during transition
4. Update backend to write to both fields

#### Phase 2: Switch to new field
1. Update all resolvers to read from `input_artifacts`
2. Update frontend to use new GraphQL fields
3. Keep old fields but mark as deprecated

#### Phase 3: Cleanup (Future)
1. Remove deprecated `input_generation_ids` field
2. Remove old GraphQL fields
3. Final migration to drop old column

#### Backwards Compatibility Checklist

- ✅ No changes required to existing generator code
- ✅ Lineage captured automatically during artifact resolution
- ✅ Old `input_generation_ids` field preserved for compatibility
- ✅ Old GraphQL fields (`input_generation_ids`, `input_generations`) still work
- ✅ New GraphQL fields are additive (no breaking changes)
- ✅ Frontend can adopt new hooks incrementally

## Performance Considerations

### Database Indexes

```sql
-- GIN index for JSONB containment queries (finding descendants)
CREATE INDEX idx_generations_input_artifacts_gin
ON generations USING GIN (input_artifacts);

-- B-tree index for specific generation_id lookups
CREATE INDEX idx_generations_input_artifacts_generation_id
ON generations USING btree ((input_artifacts->>'generation_id'));
```

### Query Optimization

1. **Ancestry queries**: Use recursive CTEs for efficient traversal
2. **Descendant queries**: Use JSONB containment operators with GIN index
3. **Depth limiting**: Always enforce max_depth to prevent runaway queries
4. **Caching**: Consider caching ancestry trees for popular artifacts

### Expected Performance

- Direct lineage lookup: O(1) with GIN index
- Ancestry tree (depth N): O(N) database queries with current design
- Could optimize with recursive CTE for single-query traversal

## Testing Strategy

### Unit Tests

```python
# tests/test_lineage.py

async def test_input_artifacts_captured_automatically():
    """Test that lineage is captured during artifact resolution."""
    # Create parent generations
    parent1 = await create_test_generation(artifact_type="image")
    parent2 = await create_test_generation(artifact_type="image")

    # Create child generation with inputs
    input_params = {
        "first_frame": str(parent1.id),
        "last_frame": str(parent2.id),
        "prompt": "test"
    }

    child = await create_generation_with_inputs(
        generator_name="fal-veo31-first-last-frame-to-video",
        input_params=input_params
    )

    # Verify lineage captured
    assert len(child.input_artifacts) == 2
    assert child.input_artifacts[0]["role"] == "first_frame"
    assert child.input_artifacts[1]["role"] == "last_frame"

async def test_ancestry_query_recursive():
    """Test recursive ancestry traversal."""
    # Create 3-level ancestry chain
    gen1 = await create_test_generation()
    gen2 = await create_child_generation(inputs=[gen1])
    gen3 = await create_child_generation(inputs=[gen2])

    # Query ancestry
    ancestry = await resolve_ancestry(gen3)

    assert ancestry.depth == 0
    assert len(ancestry.parents) == 1
    assert ancestry.parents[0].depth == 1
    assert len(ancestry.parents[0].parents) == 1
    assert ancestry.parents[0].parents[0].depth == 2
```

### Integration Tests

- Test end-to-end generation with lineage capture
- Test GraphQL queries for ancestry and descendants
- Test access control (can't see lineage across tenants)
- Test migration from old to new schema

## Open Questions

1. **Should we store additional metadata?**
   - Timestamp when lineage was created?
   - Input parameters used for that specific role?
   - Generator version?

2. **Do we need lineage versioning?**
   - If a parent artifact is deleted, what happens?
   - Should we keep historical lineage even if artifacts are gone?

3. **Should descendants query be limited?**
   - Could be expensive for very popular artifacts
   - Maybe add pagination or max results limit?

4. **Do we need lineage search/filtering?**
   - Find all artifacts that used X as input?
   - Find all artifacts in a lineage chain that match criteria?

## Summary

This design provides:

✅ **Role-based lineage tracking** - Know what role each parent played
✅ **Recursive ancestry queries** - Complete lineage tree with depth tracking
✅ **Descendant queries** - Find all artifacts derived from a source
✅ **Zero generator changes** - Automatic capture via existing introspection
✅ **Backwards compatible** - Phased migration with no breaking changes
✅ **Performant** - JSONB with GIN indexes for efficient queries
✅ **GraphQL-first** - Clean API with hooks for frontend consumption

The key innovation is leveraging the existing `extract_artifact_fields()` introspection to automatically capture lineage metadata (including role names) during artifact resolution, eliminating the need for generators to declare lineage explicitly.
