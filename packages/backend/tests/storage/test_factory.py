"""Tests for storage factory and configuration."""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from boards.storage.base import StorageConfig
from boards.storage.factory import (
    create_development_storage,
    create_storage_manager,
    create_storage_provider,
)
from boards.storage.implementations.local import LocalStorageProvider


class TestCreateStorageProvider:
    """Test storage provider factory."""

    def test_create_local_provider(self):
        config = {
            "base_path": "/tmp/test",
            "public_url_base": "http://localhost:8000/storage",
        }

        provider = create_storage_provider("local", config)

        assert isinstance(provider, LocalStorageProvider)
        assert provider.base_path == Path("/tmp/test").resolve()
        assert provider.public_url_base == "http://localhost:8000/storage"

    def test_create_local_provider_minimal(self):
        provider = create_storage_provider("local", {})

        assert isinstance(provider, LocalStorageProvider)
        assert provider.base_path == Path("/tmp/boards/storage").resolve()
        assert provider.public_url_base is None

    def test_create_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown storage provider type"):
            create_storage_provider("unknown", {})

    @patch("boards.storage.factory._s3_available", True)
    @patch("boards.storage.factory.S3StorageProvider")
    def test_create_s3_provider(self, mock_s3):  # type: ignore[reportUnknownArgumentType]
        config = {
            "bucket": "test-bucket",
            "region": "us-west-2",
            "aws_access_key_id": "test-key",
            "aws_secret_access_key": "test-secret",
        }

        create_storage_provider("s3", config)

        mock_s3.assert_called_once()  # type: ignore[reportUnknownMemberType]

    @patch("boards.storage.factory._s3_available", False)
    def test_create_s3_not_available(self):
        with pytest.raises(ImportError, match="S3 storage requires"):
            create_storage_provider("s3", {})

    @patch("boards.storage.factory._gcs_available", True)
    @patch("boards.storage.factory.GCSStorageProvider")
    def test_create_gcs_provider(self, mock_gcs):  # type: ignore[reportUnknownArgumentType]
        config = {
            "bucket": "test-bucket",
            "project_id": "test-project",
            "credentials_path": "/path/to/creds.json",
        }

        create_storage_provider("gcs", config)

        mock_gcs.assert_called_once()  # type: ignore[reportUnknownMemberType]

    @patch("boards.storage.factory._gcs_available", False)
    def test_create_gcs_not_available(self):
        with pytest.raises(ImportError, match="GCS storage package required"):
            create_storage_provider("gcs", {})

    @patch("boards.storage.factory._supabase_available", True)
    @patch("boards.storage.factory.SupabaseStorageProvider")
    def test_create_supabase_provider(self, mock_supabase):  # type: ignore[reportUnknownArgumentType]
        config = {
            "url": "https://test.supabase.co",
            "key": "test-key",
            "bucket": "test-bucket",
        }

        create_storage_provider("supabase", config)

        mock_supabase.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            url="https://test.supabase.co", key="test-key", bucket="test-bucket"
        )

    @patch("boards.storage.factory._supabase_available", False)
    def test_create_supabase_not_available(self):
        with pytest.raises(ImportError, match="Supabase storage requires"):
            create_storage_provider("supabase", {})


class TestCreateStorageManager:
    """Test storage manager factory."""

    def test_create_with_direct_config(self):
        config = StorageConfig(
            default_provider="local",
            providers={
                "local": {"type": "local", "config": {"base_path": "/tmp/test"}}
            },
            routing_rules=[{"provider": "local"}],
        )

        manager = create_storage_manager(storage_config=config)

        assert manager.default_provider == "local"
        assert "local" in manager.providers
        assert isinstance(manager.providers["local"], LocalStorageProvider)

    def test_create_with_config_file(self):
        yaml_content = """
storage:
  default_provider: local
  providers:
    local:
      type: local
      config:
        base_path: /tmp/test
        public_url_base: http://localhost:8000/storage
  routing_rules:
    - provider: local
"""

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch("pathlib.Path.exists", return_value=True):
                manager = create_storage_manager("test_config.yaml")

        assert manager.default_provider == "local"
        assert "local" in manager.providers

    def test_create_missing_default_provider_fallback(self):
        config = StorageConfig(
            default_provider="nonexistent",
            providers={"local": {"type": "local", "config": {}}},
            routing_rules=[],
        )

        manager = create_storage_manager(storage_config=config)

        # Should fallback to available provider
        assert manager.default_provider == "local"

    def test_create_no_providers_available(self):
        config = StorageConfig(
            default_provider="local",
            providers={"broken": {"type": "unknown", "config": {}}},
            routing_rules=[],
        )

        with pytest.raises(RuntimeError, match="No storage providers"):
            create_storage_manager(storage_config=config)


class TestCreateDevelopmentStorage:
    """Test development storage factory."""

    def test_create_development_storage(self):
        manager = create_development_storage()

        assert manager.default_provider == "local"
        assert "local" in manager.providers
        assert isinstance(manager.providers["local"], LocalStorageProvider)

        # Check configuration
        local_provider = manager.providers["local"]
        assert local_provider.base_path == Path("/tmp/boards/storage").resolve()
        assert local_provider.public_url_base == "http://localhost:8000/storage"
