"""Factory for creating auth adapters based on configuration."""

from __future__ import annotations

import json
import os

from .adapters.auth0 import Auth0OIDCAdapter
from .adapters.base import AuthAdapter
from .adapters.clerk import ClerkAuthAdapter
from .adapters.jwt import JWTAuthAdapter
from .adapters.none import NoAuthAdapter
from .adapters.oidc import OIDCAdapter

# Optional Supabase adapter - imported conditionally
try:
    from .adapters.supabase import SupabaseAuthAdapter

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    SupabaseAuthAdapter = None  # type: ignore


def get_auth_adapter() -> AuthAdapter:
    """Create and return the configured auth adapter."""
    provider = os.getenv("BOARDS_AUTH_PROVIDER", "none")  # Default to no-auth for dev
    config_str = os.getenv("BOARDS_AUTH_CONFIG", "{}")

    try:
        config = json.loads(config_str)
    except json.JSONDecodeError:
        config = {}

    if provider == "none":
        # No-auth mode for local development
        return NoAuthAdapter(
            default_user_id=config.get("default_user_id", "dev-user"),
            default_tenant=config.get("default_tenant", "default"),
        )

    elif provider == "jwt":
        secret_key = config.get("secret_key") or os.getenv("BOARDS_JWT_SECRET")
        if not secret_key:
            raise ValueError(
                "JWT secret key is required. Set BOARDS_JWT_SECRET or provide in config."
            )

        return JWTAuthAdapter(
            secret_key=secret_key,
            algorithm=config.get("algorithm", "HS256"),
            issuer=config.get("issuer", "boards"),
            audience=config.get("audience", "boards-api"),
        )

    elif provider == "supabase":
        if not SUPABASE_AVAILABLE:
            raise ValueError(
                "Supabase auth provider is not available. "
                "Install the supabase package: pip install 'weirdfingers-boards[auth-supabase]'"
            )

        url = config.get("url") or os.getenv("SUPABASE_URL")
        service_role_key = config.get("service_role_key") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not service_role_key:
            raise ValueError(
                "Supabase URL and service role key are required. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY or provide in config."
            )

        return SupabaseAuthAdapter(url=url, service_role_key=service_role_key)  # type: ignore

    elif provider == "clerk":
        secret_key = config.get("secret_key") or os.getenv("CLERK_SECRET_KEY")
        if not secret_key:
            raise ValueError(
                "Clerk secret key is required. " "Set CLERK_SECRET_KEY or provide in config."
            )

        return ClerkAuthAdapter(
            secret_key=secret_key,
            jwks_url=config.get("jwks_url"),
        )

    elif provider == "auth0":
        domain = config.get("domain") or os.getenv("AUTH0_DOMAIN")
        audience = config.get("audience") or os.getenv("AUTH0_AUDIENCE")

        if not domain or not audience:
            raise ValueError(
                "Auth0 domain and audience are required. "
                "Set AUTH0_DOMAIN and AUTH0_AUDIENCE or provide in config."
            )

        return Auth0OIDCAdapter(
            domain=domain,
            audience=audience,
            client_id=config.get("client_id") or os.getenv("AUTH0_CLIENT_ID"),
            client_secret=config.get("client_secret") or os.getenv("AUTH0_CLIENT_SECRET"),
        )

    elif provider == "oidc":
        issuer = config.get("issuer") or os.getenv("OIDC_ISSUER")
        client_id = config.get("client_id") or os.getenv("OIDC_CLIENT_ID")

        if not issuer or not client_id:
            raise ValueError(
                "OIDC issuer and client_id are required. "
                "Set OIDC_ISSUER and OIDC_CLIENT_ID or provide in config."
            )

        return OIDCAdapter(
            issuer=issuer,
            client_id=client_id,
            client_secret=config.get("client_secret") or os.getenv("OIDC_CLIENT_SECRET"),
            audience=config.get("audience") or os.getenv("OIDC_AUDIENCE"),
            jwks_url=config.get("jwks_url") or os.getenv("OIDC_JWKS_URL"),
        )

    else:
        raise ValueError(f"Unsupported auth provider: {provider}")


def get_auth_adapter_cached() -> AuthAdapter:
    """Get the auth adapter instance (no global caching for thread safety)."""
    # Create fresh adapter each time to avoid global state issues
    # The cost of adapter creation is minimal and this ensures thread/test safety
    return get_auth_adapter()
