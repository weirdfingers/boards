"""Authentication context for request handling."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .adapters.base import Principal


@dataclass
class AuthContext:
    """Runtime authentication context for a request."""

    user_id: UUID | None
    tenant_id: str
    principal: Principal | None
    token: str | None

    @property
    def is_authenticated(self) -> bool:
        """Check if the request is authenticated."""
        return self.user_id is not None and self.principal is not None

    @property
    def provider(self) -> str | None:
        """Get the authentication provider name."""
        return self.principal['provider'] if self.principal else None
