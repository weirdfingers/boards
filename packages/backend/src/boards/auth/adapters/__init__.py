"""Authentication adapters for different providers."""

from .auth0 import Auth0OIDCAdapter
from .base import AuthAdapter, Principal
from .clerk import ClerkAuthAdapter
from .jwt import JWTAuthAdapter
from .none import NoAuthAdapter
from .oidc import OIDCAdapter
from .supabase import SupabaseAuthAdapter

__all__ = [
    "AuthAdapter",
    "Principal",
    "SupabaseAuthAdapter",
    "JWTAuthAdapter",
    "NoAuthAdapter",
    "ClerkAuthAdapter",
    "Auth0OIDCAdapter",
    "OIDCAdapter",
]
