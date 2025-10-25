"""Storage configuration system."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .base import StorageConfig


@dataclass
class ProviderConfig:
    """Configuration for a specific storage provider."""

    type: str
    config: dict[str, Any]


def load_storage_config(
    config_path: Path | None = None, env_prefix: str = "BOARDS_STORAGE_"
) -> StorageConfig:
    """Load storage configuration from file and environment variables.

    Args:
        config_path: Path to YAML configuration file
        env_prefix: Prefix for environment variable overrides

    Returns:
        StorageConfig instance
    """
    # Default configuration
    config_data = {
        "default_provider": "local",
        "providers": {
            "local": {
                "type": "local",
                "config": {
                    "base_path": "/tmp/boards/storage",
                    "public_url_base": "http://localhost:8088/api/storage",
                },
            }
        },
        "routing_rules": [{"provider": "local"}],  # Default rule
        "max_file_size": 100 * 1024 * 1024,  # 100MB
    }

    # Load from YAML file if provided
    if config_path and config_path.exists():
        try:
            with open(config_path) as f:
                file_config = yaml.safe_load(f)
                if file_config.get("storage"):
                    config_data.update(file_config["storage"])
        except Exception as e:
            raise ValueError(f"Failed to load storage config from {config_path}: {e}") from e

    # Override with environment variables
    config_data = _apply_env_overrides(config_data, env_prefix)

    return StorageConfig(
        default_provider=config_data["default_provider"],
        providers=config_data["providers"],
        routing_rules=config_data["routing_rules"],
        max_file_size=config_data.get("max_file_size", 100 * 1024 * 1024),
    )


def _apply_env_overrides(config_data: dict[str, Any], env_prefix: str) -> dict[str, Any]:
    """Apply environment variable overrides to configuration."""

    # Override default provider
    default_provider = os.getenv(f"{env_prefix}DEFAULT_PROVIDER")
    if default_provider:
        config_data["default_provider"] = default_provider

    # Override max file size
    max_file_size = os.getenv(f"{env_prefix}MAX_FILE_SIZE")
    if max_file_size:
        config_data["max_file_size"] = int(max_file_size)

    # Provider-specific overrides
    _apply_provider_env_overrides(config_data, env_prefix)

    return config_data


def _apply_provider_env_overrides(config_data: dict[str, Any], env_prefix: str):
    """Apply environment variable overrides for provider configurations."""

    # Supabase configuration
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    supabase_bucket = os.getenv(f"{env_prefix}SUPABASE_BUCKET")

    if supabase_url and supabase_key:
        config_data["providers"]["supabase"] = {
            "type": "supabase",
            "config": {
                "url": supabase_url,
                "key": supabase_key,
                "bucket": supabase_bucket or "boards-artifacts",
            },
        }

    # S3 configuration
    s3_bucket = os.getenv(f"{env_prefix}S3_BUCKET")
    s3_region = os.getenv(f"{env_prefix}S3_REGION")
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    if s3_bucket and aws_access_key and aws_secret_key:
        config_data["providers"]["s3"] = {
            "type": "s3",
            "config": {
                "bucket": s3_bucket,
                "region": s3_region or "us-west-2",
                "access_key_id": aws_access_key,
                "secret_access_key": aws_secret_key,
            },
        }

    # Local storage overrides
    local_base_path = os.getenv(f"{env_prefix}LOCAL_BASE_PATH")
    local_public_url = os.getenv(f"{env_prefix}LOCAL_PUBLIC_URL_BASE")

    if local_base_path or local_public_url:
        local_config = config_data["providers"].get("local", {}).get("config", {})
        if local_base_path:
            local_config["base_path"] = local_base_path
        if local_public_url:
            local_config["public_url_base"] = local_public_url

        config_data["providers"]["local"] = {"type": "local", "config": local_config}


def create_example_config() -> str:
    """Create an example storage configuration YAML."""

    config = {
        "storage": {
            "default_provider": "supabase",
            "providers": {
                "local": {
                    "type": "local",
                    "config": {
                        "base_path": "/var/boards/storage",
                        "public_url_base": "http://localhost:8088/api/storage",
                    },
                },
                "supabase": {
                    "type": "supabase",
                    "config": {
                        "url": "${SUPABASE_URL}",
                        "key": "${SUPABASE_ANON_KEY}",
                        "bucket": "boards-artifacts",
                    },
                },
                "s3": {
                    "type": "s3",
                    "config": {
                        "bucket": "boards-prod-artifacts",
                        "region": "us-west-2",
                        "access_key_id": "${AWS_ACCESS_KEY_ID}",
                        "secret_access_key": "${AWS_SECRET_ACCESS_KEY}",
                    },
                },
            },
            "routing_rules": [
                {
                    "condition": {"artifact_type": "video", "size_gt": "100MB"},
                    "provider": "s3",
                },
                {"condition": {"artifact_type": "model"}, "provider": "supabase"},
                {"provider": "supabase"},
            ],
            "max_file_size": 1073741824,  # 1GB
            "cleanup": {
                "temp_file_ttl_hours": 24,
                "cleanup_interval_hours": 1,
                "max_cleanup_batch_size": 1000,
            },
        }
    }

    return yaml.dump(config, default_flow_style=False, indent=2)
