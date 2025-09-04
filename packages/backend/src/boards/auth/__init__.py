"""Authentication and authorization system for Boards."""

from .adapters.base import AuthAdapter, Principal
from .context import AuthContext
from .middleware import get_auth_context, get_auth_context_optional
from .factory import get_auth_adapter

__all__ = [
    "AuthAdapter",
    "Principal", 
    "AuthContext",
    "get_auth_context",
    "get_auth_context_optional",
    "get_auth_adapter",
]