"""Authentication context for request handling."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .adapters.base import Principal

# Default tenant UUID for single-tenant deployments or when tenant resolution fails
# This null UUID (00000000-0000-0000-0000-000000000000) is used when:
# - Running in single-tenant mode
# - Local development without multi-tenant setup
# - Tenant slug resolution fails
DEFAULT_TENANT_UUID = UUID("00000000-0000-0000-0000-000000000000")


@dataclass
class AuthContext:
    """Runtime authentication context for a request."""

    user_id: UUID | None
    tenant_id: UUID
    principal: Principal | None
    token: str | None

    @property
    def is_authenticated(self) -> bool:
        """Check if the request is authenticated."""
        return self.user_id is not None and self.principal is not None

    @property
    def provider(self) -> str | None:
        """Get the authentication provider name."""
        return self.principal["provider"] if self.principal else None
