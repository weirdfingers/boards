"""Storage system for Boards artifacts.

This module provides a pluggable storage architecture that supports:
- Local filesystem storage for development
- Supabase storage with auth integration
- S3 storage for enterprise deployments
- Custom storage providers via plugin system

Main components:
- StorageProvider: Abstract base class for storage implementations
- StorageManager: Central coordinator for routing and operations
- ArtifactReference: Metadata about stored artifacts
"""

from .base import (
    ArtifactReference,
    SecurityException,
    StorageConfig,
    StorageException,
    StorageManager,
    StorageProvider,
    ValidationException,
)
from .config import (
    create_example_config,
    load_storage_config,
)
from .factory import (
    create_development_storage,
    create_storage_manager,
    create_storage_provider,
    get_storage_config,
)

__all__ = [
    # Base classes and exceptions
    "StorageProvider",
    "StorageManager",
    "StorageConfig",
    "ArtifactReference",
    "StorageException",
    "SecurityException",
    "ValidationException",
    # Factory functions
    "create_storage_provider",
    "create_storage_manager",
    "create_development_storage",
    "get_storage_config",
    # Configuration
    "load_storage_config",
    "create_example_config",
]
