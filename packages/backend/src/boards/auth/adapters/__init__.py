"""Authentication adapters for different providers."""

from .base import AuthAdapter, Principal
from .supabase import SupabaseAuthAdapter
from .jwt import JWTAuthAdapter
from .none import NoAuthAdapter
from .clerk import ClerkAuthAdapter
from .auth0 import Auth0OIDCAdapter
from .oidc import OIDCAdapter

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