# Authorization & RBAC

Boards implements role-based access control (RBAC) with board-scoped permissions. This allows fine-grained control over who can access and modify boards and their content.

## Permission Model

### Roles

| Role | Permissions |
|------|-------------|
| **owner** | Full control: manage members, delete board, manage generations |
| **editor** | Create/update generations, edit board metadata, invite members |  
| **viewer** | Read-only access to board and generations |

### Resources

- **Board**: The main container for generations
- **Generation**: AI-generated content within a board
- **Members**: Users with roles on a specific board

## Permission Matrix

### Board Operations

| Operation | Owner | Editor | Viewer | Public |
|-----------|-------|--------|--------|--------|
| Create board | ✅ (becomes owner) | ✅ (becomes owner) | ✅ (becomes owner) | ❌ |
| Read board | ✅ | ✅ | ✅ | ✅ (if public) |
| Update board metadata | ✅ | ✅ | ❌ | ❌ |
| Delete board | ✅ | ❌ | ❌ | ❌ |
| Make board public/private | ✅ | ❌ | ❌ | ❌ |

### Member Management

| Operation | Owner | Editor | Viewer |
|-----------|-------|--------|--------|
| View members | ✅ | ✅ | ✅ |
| Add members | ✅ | ✅ (viewer/editor only) | ❌ |
| Remove members | ✅ | ✅ (lower roles only) | ❌ |
| Change member roles | ✅ | ❌ | ❌ |
| Transfer ownership | ✅ | ❌ | ❌ |

### Generation Operations

| Operation | Owner | Editor | Viewer | Public |
|-----------|-------|--------|--------|--------|
| Create generation | ✅ | ✅ | ❌ | ❌ |
| Read generation | ✅ | ✅ | ✅ | ✅ (if board public) |
| Update generation | ✅ | ✅ (own only) | ❌ | ❌ |
| Delete generation | ✅ | ✅ (own only) | ❌ | ❌ |
| Cancel job | ✅ | ✅ (own only) | ❌ | ❌ |

## Implementation

### Authorization Helpers

Boards provides helper functions for checking permissions:

```python
from boards.auth.authorization import (
    require_board_role,
    can_read_board,
    can_edit_board,
    can_manage_board,
    get_user_board_role,
)

# Check if user has specific role on board
await require_board_role(db, board_id, user_id, {"owner", "editor"})

# Check read access (includes public boards)
can_read = await can_read_board(db, board_id, user_id)

# Get user's role on board (returns None if no access)
role = await get_user_board_role(db, board_id, user_id)
```

### GraphQL Resolver Usage

```python
import strawberry
from strawberry.types import Info
from boards.auth.authorization import can_read_board, require_board_role

@strawberry.type
class Query:
    @strawberry.field
    async def board(self, info: Info, id: UUID) -> Optional[Board]:
        auth = info.context["auth"]
        
        # Check read permission
        if not await can_read_board(
            info.context["db"], 
            id, 
            auth.user_id if auth.is_authenticated else None
        ):
            raise PermissionError("Not authorized to read this board")
        
        return await boards_repo.get_by_id(id)

@strawberry.type  
class Mutation:
    @strawberry.field
    async def create_generation(
        self, info: Info, board_id: UUID, input: GenerationInput
    ) -> Generation:
        auth = info.context["auth"]
        
        # Require editor or owner role
        await require_board_role(
            info.context["db"], 
            board_id, 
            auth.user_id,
            {"editor", "owner"}
        )
        
        # Create generation...
        return await generations_repo.create(board_id, input)
```

### FastAPI Endpoint Usage

```python
from fastapi import APIRouter, Depends, HTTPException
from boards.auth import get_auth_context, AuthContext
from boards.auth.authorization import can_read_board

router = APIRouter()

@router.get("/boards/{board_id}/export")
async def export_board(
    board_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db)
):
    # Check read permission
    if not await can_read_board(db, board_id, auth.user_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Export board data...
    return await export_board_data(board_id)
```

## Multi-Tenancy

Authorization is scoped to tenants. Users can only access boards within their tenant, even if they have the same auth provider subject across different tenants.

```python
# User lookup includes tenant isolation
user = await get_user_by_auth_info(
    db, 
    tenant_id=auth_context.tenant_id,
    auth_provider=principal["provider"], 
    auth_subject=principal["subject"]
)

# All board queries are tenant-scoped
boards = await db.execute(
    select(Board).where(
        and_(
            Board.tenant_id == auth_context.tenant_id,
            # ... other conditions
        )
    )
)
```

## Public Boards

Boards can be marked as public, allowing read access without authentication:

```python
@strawberry.field
async def public_boards(self, info: Info) -> List[Board]:
    # No auth required - returns public boards only
    return await db.execute(
        select(Board).where(Board.is_public == True)
    )

async def can_read_board(
    db: AsyncSession, 
    board_id: UUID, 
    user_id: Optional[UUID]
) -> bool:
    # Check if board is public first
    board = await get_board_by_id(db, board_id)
    if board and board.is_public:
        return True
    
    # Otherwise check user permissions
    if not user_id:
        return False
    
    return await get_user_board_role(db, board_id, user_id) is not None
```

## Storage Authorization

Presigned URLs for file uploads/downloads are also protected:

```python
from boards.storage import generate_presigned_url
from boards.auth.authorization import can_read_board

@router.get("/boards/{board_id}/generations/{generation_id}/download")
async def get_download_url(
    board_id: UUID,
    generation_id: UUID,
    auth: AuthContext = Depends(get_auth_context)
):
    # Check read permission on board
    if not await can_read_board(db, board_id, auth.user_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Generate presigned URL
    url = await generate_presigned_url(
        bucket="generations",
        key=f"{board_id}/{generation_id}/output.png",
        expiration=3600  # 1 hour
    )
    
    return {"download_url": url}
```

## Job Progress Authorization

Server-Sent Events (SSE) for job progress also enforce authorization:

```python
from fastapi import Request
from fastapi.responses import StreamingResponse

@router.get("/boards/{board_id}/jobs/{job_id}/progress")
async def stream_job_progress(
    board_id: UUID,
    job_id: UUID,
    request: Request,
    auth: AuthContext = Depends(get_auth_context)
):
    # Check read permission
    if not await can_read_board(db, board_id, auth.user_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    async def event_stream():
        async for progress in job_progress_stream(job_id):
            if await request.is_disconnected():
                break
            yield f"data: {progress.json()}\\n\\n"
    
    return StreamingResponse(
        event_stream(), 
        media_type="text/event-stream"
    )
```

## Testing Authorization

### Unit Tests

```python
import pytest
from boards.auth.authorization import can_read_board, require_board_role

@pytest.mark.asyncio
async def test_board_owner_can_read(db_session, sample_user, sample_board):
    # Make user owner of board
    await add_board_member(db_session, sample_board.id, sample_user.id, "owner")
    
    # Test read permission
    assert await can_read_board(db_session, sample_board.id, sample_user.id)

@pytest.mark.asyncio  
async def test_viewer_cannot_edit(db_session, sample_user, sample_board):
    # Make user viewer
    await add_board_member(db_session, sample_board.id, sample_user.id, "viewer")
    
    # Test edit permission fails
    with pytest.raises(PermissionError):
        await require_board_role(
            db_session, sample_board.id, sample_user.id, {"editor", "owner"}
        )
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_unauthorized_user_cannot_access_private_board(client, auth_headers):
    board = await create_private_board()
    
    response = await client.get(
        f"/api/boards/{board.id}",
        headers=auth_headers["different_user"]
    )
    
    assert response.status_code == 403
```

## Security Considerations

### Defense in Depth

- Authorization checks at multiple layers (GraphQL, REST, storage, SSE)
- Database-level tenant isolation  
- Audit logging of permission decisions
- Rate limiting per user/tenant

### Audit Trail

```python
import logging

audit_logger = logging.getLogger("boards.audit")

async def require_board_role(
    db: AsyncSession, 
    board_id: UUID, 
    user_id: UUID, 
    roles: set[str]
) -> None:
    user_role = await get_user_board_role(db, board_id, user_id)
    
    # Log authorization decision
    audit_logger.info(
        "Authorization check",
        extra={
            "user_id": str(user_id),
            "board_id": str(board_id), 
            "required_roles": list(roles),
            "user_role": user_role,
            "result": "granted" if user_role in roles else "denied"
        }
    )
    
    if user_role not in roles:
        raise PermissionError(f"Required roles: {roles}, user has: {user_role}")
```

### Common Pitfalls

**Always check permissions at the API boundary:**
```python
# ❌ Bad: No permission check
@strawberry.field
async def board(self, info: Info, id: UUID) -> Board:
    return await get_board_by_id(info.context["db"], id)

# ✅ Good: Permission check first
@strawberry.field  
async def board(self, info: Info, id: UUID) -> Optional[Board]:
    if not await can_read_board(info.context["db"], id, auth.user_id):
        raise PermissionError("Access denied")
    return await get_board_by_id(info.context["db"], id)
```

**Don't leak information through error messages:**
```python
# ❌ Bad: Reveals board exists
if not board:
    raise HTTPException(404, "Board not found")
if not await can_read_board(db, board_id, user_id):
    raise HTTPException(403, "Access denied")

# ✅ Good: Consistent error for unauthorized access
if not board or not await can_read_board(db, board_id, user_id):
    raise HTTPException(404, "Board not found")
```