"""User provisioning and management."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# from ..models.users import User  # TODO: Implement when models are ready

# Temporary User model for testing
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String
from uuid import UUID

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    auth_provider: Mapped[str] = mapped_column(String)
    auth_subject: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, nullable=True)
    display_name: Mapped[str] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str] = mapped_column(String, nullable=True)
    user_metadata: Mapped[str] = mapped_column(String, nullable=True)  # JSON field
from .adapters.base import Principal

logger = logging.getLogger(__name__)


async def ensure_local_user(
    db: AsyncSession, 
    tenant_id: str, 
    principal: Principal
) -> UUID:
    """
    Ensure a local user exists for the given principal (JIT provisioning).
    
    This function creates a local user record if one doesn't exist for the
    given (tenant_id, auth_provider, auth_subject) combination.
    
    Args:
        db: Database session
        tenant_id: Tenant identifier
        principal: Authenticated principal from auth provider
        
    Returns:
        UUID of the local user
    """
    provider = principal["provider"]
    subject = principal["subject"]
    
    # Try to find existing user
    stmt = select(User).where(
        and_(
            User.tenant_id == tenant_id,
            User.auth_provider == provider,
            User.auth_subject == subject,
        )
    )
    
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # Update user info if provided in principal
        updated = False
        
        email = principal.get("email")
        if email and user.email != email:
            user.email = email
            updated = True
            
        display_name = principal.get("display_name")
        if display_name and user.display_name != display_name:
            user.display_name = display_name
            updated = True
            
        avatar_url = principal.get("avatar_url")
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            updated = True
        
        if updated:
            await db.commit()
            logger.info(f"Updated user info for user_id={user.id}")
        
        return UUID(user.id)
    
    # Create new user
    new_user_id = str(uuid4())
    user = User(
        id=new_user_id,
        tenant_id=tenant_id,
        auth_provider=provider,
        auth_subject=subject,
        email=principal.get("email"),
        display_name=principal.get("display_name"),
        avatar_url=principal.get("avatar_url"),
        user_metadata=str({
            "created_via": "jit_provisioning",
            "provider_claims": principal.get("claims", {}),
        })
    )
    
    db.add(user)
    await db.commit()
    
    logger.info(
        f"Created new user via JIT provisioning: "
        f"user_id={user.id}, tenant_id={tenant_id}, provider={provider}"
    )
    
    return UUID(user.id)


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Get a user by ID."""
    stmt = select(User).where(User.id == str(user_id))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_auth_info(
    db: AsyncSession,
    tenant_id: str,
    auth_provider: str,
    auth_subject: str
) -> Optional[User]:
    """Get a user by auth provider information."""
    stmt = select(User).where(
        and_(
            User.tenant_id == tenant_id,
            User.auth_provider == auth_provider,
            User.auth_subject == auth_subject,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()