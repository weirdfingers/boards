"""Factory for creating storage providers and managers."""

import logging
from pathlib import Path
from typing import Dict, Any

from .base import StorageManager, StorageProvider
from .config import StorageConfig, load_storage_config
from .implementations.local import LocalStorageProvider

logger = logging.getLogger(__name__)

# Optional imports for cloud providers
try:
    from .implementations.supabase import SupabaseStorageProvider

    _supabase_available = True
except ImportError:
    SupabaseStorageProvider = None
    _supabase_available = False
    logger.warning("Supabase storage not available - install supabase-py to enable")


def create_storage_provider(
    provider_type: str, config: Dict[str, Any]
) -> StorageProvider:
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
                "Supabase storage requires supabase-py. Install with: pip install supabase"
            )
        return _create_supabase_provider(config)
    elif provider_type == "s3":
        # S3 provider would be implemented here
        raise NotImplementedError("S3 storage provider not yet implemented")
    else:
        raise ValueError(f"Unknown storage provider type: {provider_type}")


def _create_local_provider(config: Dict[str, Any]) -> LocalStorageProvider:
    """Create local storage provider."""
    base_path = config.get("base_path", "/tmp/boards/storage")
    public_url_base = config.get("public_url_base")

    return LocalStorageProvider(
        base_path=Path(base_path), public_url_base=public_url_base
    )


def _create_supabase_provider(config: Dict[str, Any]) -> StorageProvider:
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


def create_storage_manager(
    config_path: str | Path | None = None, storage_config: StorageConfig | None = None
) -> StorageManager:
    """Create a configured storage manager.

    Args:
        config_path: Path to configuration file (optional)
        storage_config: Pre-built storage configuration (optional)

    Returns:
        StorageManager instance with registered providers
    """

    # Load configuration
    if storage_config is None:
        config_path = Path(config_path) if config_path else None
        storage_config = load_storage_config(config_path)

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

            logger.info(
                f"Registered storage provider: {provider_name} ({provider_type})"
            )

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


def create_development_storage() -> StorageManager:
    """Create a simple storage manager for development use.

    Uses local filesystem storage with sensible defaults.
    """
    config = StorageConfig(
        default_provider="local",
        providers={
            "local": {
                "type": "local",
                "config": {
                    "base_path": "/tmp/boards/storage",
                    "public_url_base": "http://localhost:8000/storage",
                },
            }
        },
        routing_rules=[{"provider": "local"}],
    )

    return create_storage_manager(storage_config=config)
