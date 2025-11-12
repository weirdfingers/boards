"""Authentication adapters for different providers."""

from .auth0 import Auth0OIDCAdapter
from .base import AuthAdapter, Principal
from .clerk import ClerkAuthAdapter
from .jwt import JWTAuthAdapter
from .none import NoAuthAdapter
from .oidc import OIDCAdapter

# Always available adapters
__all__ = [
    "AuthAdapter",
    "Principal",
    "JWTAuthAdapter",
    "NoAuthAdapter",
    "ClerkAuthAdapter",
    "Auth0OIDCAdapter",
    "OIDCAdapter",
]

# Optional auth providers - imported conditionally to avoid import errors
try:
    from .supabase import SupabaseAuthAdapter

    __all__.append("SupabaseAuthAdapter")
except ImportError:
    pass
