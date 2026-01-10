"""
Configuration management for Boards backend
"""

import base64
import functools
import json
import os

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def decode_api_keys(value: str) -> dict[str, str]:
    """
    Decode API keys from environment variable.

    Supports two formats:
    1. Base64-encoded JSON (preferred, handles special characters safely)
    2. Plain JSON (for backwards compatibility)

    Args:
        value: The raw value from environment variable

    Returns:
        Dictionary of API keys
    """
    if not value:
        return {}

    value = value.strip()
    if not value:
        return {}

    # Try base64 decoding first
    try:
        decoded_bytes = base64.b64decode(value, validate=True)
        decoded_str = decoded_bytes.decode("utf-8")
        return json.loads(decoded_str)
    except Exception:
        pass

    # Fall back to plain JSON parsing (backwards compatibility)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://boards:boards_dev@localhost:5433/boards_dev"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis (for job queue)
    redis_url: str = "redis://localhost:6380"

    # Storage
    storage_config_path: str | None = None

    # Auth
    auth_provider: str = "none"  # 'none', 'supabase', 'clerk', 'auth0', 'jwt'
    auth_config: dict = {}
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_tenant_claim: str | None = None  # Custom JWT claim for tenant extraction

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8088
    api_reload: bool = False
    cors_origins: list[str] = ["http://localhost:3033"]

    # Generators Configuration
    generators_config_path: str | None = None
    # Raw API keys value (base64-encoded JSON or plain JSON)
    # Uses validation_alias to read from BOARDS_GENERATOR_API_KEYS env var
    generator_api_keys_raw: str = Field(
        default="", validation_alias="BOARDS_GENERATOR_API_KEYS"
    )

    @computed_field  # type: ignore[prop-decorator]
    @functools.cached_property
    def generator_api_keys(self) -> dict[str, str]:
        """Decoded API keys dictionary."""
        return decode_api_keys(self.generator_api_keys_raw)

    # Environment
    environment: str = "development"  # 'development', 'staging', 'production'
    debug: bool = True
    sql_echo: bool = False
    log_level: str = "INFO"

    # Tenant Settings (for multi-tenant mode)
    multi_tenant_mode: bool = False
    default_tenant_slug: str = "default"

    # Tenant Registration Settings
    tenant_registration_requires_approval: bool = False
    tenant_registration_allowed_domains: list[str] | None = None
    max_tenants_per_user: int | None = None

    # Frontend Integration
    frontend_base_url: str | None = None

    # Internal API URL (for Docker environments where worker needs to reach API)
    # This allows workers to reach the API using Docker internal networking
    internal_api_url: str | None = None

    # Job Queue Settings
    job_queue_name: str = "boards-jobs"
    job_timeout: int = 3600  # 1 hour default timeout

    # File Upload Settings
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    allowed_upload_extensions: list[str] = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",  # Images
        ".mp4",
        ".mov",
        ".avi",
        ".webm",  # Videos
        ".mp3",
        ".wav",
        ".ogg",
        ".m4a",  # Audio
        ".txt",
        ".md",
        ".json",  # Text
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BOARDS_",
        case_sensitive=False,
        # Allow extra fields for provider-specific configs
        extra="allow",
    )


# Global settings instance
settings = Settings()

# Debug: Log settings initialization (only in debug mode)
if settings.debug:
    from .logging import get_logger

    _logger = get_logger(__name__)
    _logger.debug(
        "Settings initialized",
        internal_api_url=settings.internal_api_url,
        environment=settings.environment,
    )


def initialize_generator_api_keys() -> None:
    """
    Sync generator API keys from settings to os.environ.

    This allows third-party packages (like replicate) that expect
    environment variables to work correctly with our Pydantic settings.
    """
    for key, value in settings.generator_api_keys.items():
        if value:  # Only set non-empty values
            os.environ[key] = value


# Helper functions
def get_database_url(tenant_slug: str | None = None) -> str:
    """Get database URL, optionally with tenant-specific schema."""
    if settings.multi_tenant_mode and tenant_slug:
        # In multi-tenant mode, could use schemas or separate databases
        # For now, we'll use the same database with tenant isolation via queries
        return settings.database_url
    return settings.database_url
