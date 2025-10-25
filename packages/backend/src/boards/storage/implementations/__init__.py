"""Storage provider implementations."""

from .local import LocalStorageProvider

# Optional cloud providers - imported conditionally to avoid import errors
__all__ = ["LocalStorageProvider"]

try:
    from .supabase import SupabaseStorageProvider

    __all__.append("SupabaseStorageProvider")
except ImportError:
    pass

try:
    from .s3 import S3StorageProvider

    __all__.append("S3StorageProvider")
except ImportError:
    pass

try:
    from .gcs import GCSStorageProvider

    __all__.append("GCSStorageProvider")
except ImportError:
    pass
