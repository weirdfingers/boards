"""
Configuration management for Boards backend
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://boards:boards_dev@localhost/boards_dev"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis (for job queue)
    redis_url: str = "redis://localhost:6379"
    
    # Storage
    storage_provider: str = "local"  # 'local', 'supabase', 's3', 'gcs'
    storage_config: dict = {}
    local_storage_path: str = "/tmp/boards-storage"
    
    # Auth
    auth_provider: str = "none"  # 'none', 'supabase', 'clerk', 'auth0', 'jwt'
    auth_config: dict = {}
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    
    # Providers Configuration
    providers_config_path: str = "providers.yaml"
    
    # Environment
    environment: str = "development"  # 'development', 'staging', 'production'
    debug: bool = True
    log_level: str = "INFO"
    
    # Tenant Settings (for multi-tenant mode)
    multi_tenant_mode: bool = False
    default_tenant_slug: str = "default"
    
    # Job Queue Settings
    job_queue_name: str = "boards-jobs"
    job_timeout: int = 3600  # 1 hour default timeout
    
    # File Upload Settings
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    allowed_upload_extensions: list[str] = [
        ".jpg", ".jpeg", ".png", ".gif", ".webp",  # Images
        ".mp4", ".mov", ".avi", ".webm",  # Videos
        ".mp3", ".wav", ".ogg", ".m4a",  # Audio
        ".txt", ".md", ".json",  # Text
    ]
    
    class Config:
        env_file = ".env"
        env_prefix = "BOARDS_"
        case_sensitive = False
        
        # Allow extra fields for provider-specific configs
        extra = "allow"

# Global settings instance
settings = Settings()

# Helper functions
def get_database_url(tenant_slug: Optional[str] = None) -> str:
    """Get database URL, optionally with tenant-specific schema."""
    if settings.multi_tenant_mode and tenant_slug:
        # In multi-tenant mode, could use schemas or separate databases
        # For now, we'll use the same database with tenant isolation via queries
        return settings.database_url
    return settings.database_url

def get_storage_path(tenant_slug: Optional[str] = None) -> Path:
    """Get storage path for local storage provider."""
    base_path = Path(settings.local_storage_path)
    if settings.multi_tenant_mode and tenant_slug:
        return base_path / tenant_slug
    return base_path