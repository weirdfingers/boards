"""Factory for creating storage providers and managers."""

from pathlib import Path
from typing import Any

from ..logging import get_logger
from .base import StorageManager, StorageProvider
from .config import StorageConfig, load_storage_config
from .implementations.local import LocalStorageProvider

logger = get_logger(__name__)

# Singleton storage configuration
# Loaded once at module import time to avoid re-parsing YAML on every request
_storage_config: StorageConfig | None = None


def get_storage_config() -> StorageConfig:
    """Get the singleton storage configuration.

    Loads the configuration from settings.storage_config_path on first access.
    Subsequent calls return the cached configuration.

    Returns:
        StorageConfig instance
    """
    global _storage_config

    if _storage_config is None:
        from ..config import settings

        config_path = Path(settings.storage_config_path) if settings.storage_config_path else None
        _storage_config = load_storage_config(config_path)
        logger.info(
            f"Loaded storage configuration: default_provider={_storage_config.default_provider}, "
            f"providers={list(_storage_config.providers.keys())}"
        )

    return _storage_config


# Optional imports for cloud providers
try:
    from .implementations.supabase import SupabaseStorageProvider

    _supabase_available = True
except ImportError:
    SupabaseStorageProvider = None
    _supabase_available = False
    logger.warning(
        "Supabase storage not available. "
        "Install with: pip install weirdfingers-boards[storage-supabase]"
    )

try:
    from .implementations.s3 import S3StorageProvider

    _s3_available = True
except ImportError:
    S3StorageProvider = None
    _s3_available = False
    logger.warning(
        "S3 storage not available. " "Install with: pip install weirdfingers-boards[storage-s3]"
    )

try:
    from .implementations.gcs import GCSStorageProvider

    _gcs_available = True
except ImportError:
    GCSStorageProvider = None
    _gcs_available = False
    logger.warning(
        "GCS storage not available. " "Install with: pip install weirdfingers-boards[storage-gcs]"
    )


def create_storage_provider(provider_type: str, config: dict[str, Any]) -> StorageProvider:
    """Create a storage provider instance from configuration.

    Args:
        provider_type: Type of provider ('local', 'supabase', 's3')
        config: Provider configuration dictionary

    Returns:
        StorageProvider instance

    Raises:
        ValueError: If provider type is unknown or configuration is invalid
        ImportError: If required dependencies are not available
    """

    if provider_type == "local":
        return _create_local_provider(config)
    elif provider_type == "supabase":
        if not _supabase_available:
            raise ImportError(
                "Supabase storage requires additional dependencies. "
                "Install with: pip install weirdfingers-boards[storage-supabase]"
            )
        return _create_supabase_provider(config)
    elif provider_type == "s3":
        if not _s3_available:
            raise ImportError(
                "S3 storage requires additional dependencies. "
                "Install with: pip install weirdfingers-boards[storage-s3]"
            )
        return _create_s3_provider(config)
    elif provider_type == "gcs":
        if not _gcs_available:
            raise ImportError(
                "GCS storage requires additional dependencies. "
                "Install with: pip install weirdfingers-boards[storage-gcs]"
            )
        return _create_gcs_provider(config)
    else:
        raise ValueError(f"Unknown storage provider type: {provider_type}")


def _create_local_provider(config: dict[str, Any]) -> LocalStorageProvider:
    """Create local storage provider."""
    base_path = config.get("base_path", "/tmp/boards/storage")
    public_url_base = config.get("public_url_base")

    return LocalStorageProvider(base_path=Path(base_path), public_url_base=public_url_base)


def _create_supabase_provider(config: dict[str, Any]) -> StorageProvider:
    """Create Supabase storage provider."""
    if SupabaseStorageProvider is None:
        raise ImportError("Supabase storage not available")

    url = config.get("url")
    key = config.get("key")
    bucket = config.get("bucket", "boards-artifacts")

    if not url:
        raise ValueError("Supabase storage requires 'url' in configuration")
    if not key:
        raise ValueError("Supabase storage requires 'key' in configuration")

    return SupabaseStorageProvider(url=url, key=key, bucket=bucket)


def _create_s3_provider(config: dict[str, Any]) -> StorageProvider:
    """Create S3 storage provider."""
    if S3StorageProvider is None:
        raise ImportError("S3 storage not available")

    bucket = config.get("bucket")
    if not bucket:
        raise ValueError("S3 storage requires 'bucket' in configuration")

    region = config.get("region", "us-east-1")
    aws_access_key_id = config.get("aws_access_key_id")
    aws_secret_access_key = config.get("aws_secret_access_key")
    aws_session_token = config.get("aws_session_token")
    endpoint_url = config.get("endpoint_url")
    cloudfront_domain = config.get("cloudfront_domain")
    upload_config = config.get("upload_config", {})

    return S3StorageProvider(
        bucket=bucket,
        region=region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
        endpoint_url=endpoint_url,
        cloudfront_domain=cloudfront_domain,
        upload_config=upload_config,
    )


def _create_gcs_provider(config: dict[str, Any]) -> StorageProvider:
    """Create GCS storage provider."""
    if GCSStorageProvider is None:
        raise ImportError("GCS storage not available")

    bucket = config.get("bucket")
    if not bucket:
        raise ValueError("GCS storage requires 'bucket' in configuration")

    project_id = config.get("project_id")
    credentials_path = config.get("credentials_path")
    credentials_json = config.get("credentials_json")
    cdn_domain = config.get("cdn_domain")
    upload_config = config.get("upload_config", {})

    return GCSStorageProvider(
        bucket=bucket,
        project_id=project_id,
        credentials_path=credentials_path,
        credentials_json=credentials_json,
        cdn_domain=cdn_domain,
        upload_config=upload_config,
    )


def _build_storage_manager_from_config(storage_config: StorageConfig) -> StorageManager:
    """Build a storage manager from a StorageConfig, registering all providers.

    This is an internal helper that can be used for testing.

    Args:
        storage_config: Storage configuration

    Returns:
        StorageManager instance with registered providers

    Raises:
        RuntimeError: If no storage providers were successfully registered
    """
    # Create storage manager
    manager = StorageManager(storage_config)

    # Register providers
    for provider_name, provider_config in storage_config.providers.items():
        try:
            provider_type = provider_config.get("type", provider_name)
            provider_instance = create_storage_provider(
                provider_type, provider_config.get("config", {})
            )
            manager.register_provider(provider_name, provider_instance)

            logger.info(f"Registered storage provider: {provider_name} ({provider_type})")

        except Exception as e:
            logger.error(f"Failed to register provider {provider_name}: {e}")
            # Continue with other providers rather than failing completely
            continue

    # Validate default provider is available
    if storage_config.default_provider not in manager.providers:
        available = list(manager.providers.keys())
        if not available:
            raise RuntimeError("No storage providers were successfully registered")

        logger.warning(
            f"Default provider '{storage_config.default_provider}' not available. "
            f"Using '{available[0]}' instead."
        )
        manager.default_provider = available[0]

    return manager


def create_storage_manager() -> StorageManager:
    """Create a configured storage manager using global singleton config.

    The storage configuration is loaded once from settings.storage_config_path
    and cached for the lifetime of the process.

    Returns:
        StorageManager instance with registered providers
    """
    storage_config = get_storage_config()
    return _build_storage_manager_from_config(storage_config)


def create_development_storage() -> StorageManager:
    """Create a simple storage manager for development use.

    Uses local filesystem storage with sensible defaults.
    This is primarily used for testing and creates a standalone manager
    rather than using global settings.
    """
    config = StorageConfig(
        default_provider="local",
        providers={
            "local": {
                "type": "local",
                "config": {
                    "base_path": "/tmp/boards/storage",
                    "public_url_base": "http://localhost:8088/api/storage",
                },
            }
        },
        routing_rules=[{"provider": "local"}],
    )

    # Create storage manager directly without using global settings
    manager = StorageManager(config)

    # Register the local provider
    local_provider = create_storage_provider("local", config.providers["local"]["config"])
    manager.register_provider("local", local_provider)

    return manager
