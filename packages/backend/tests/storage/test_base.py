"""Tests for storage base classes and manager."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock
from pathlib import Path

from boards.storage.base import (
    StorageConfig,
    ArtifactReference, 
    StorageManager,
    StorageException,
    SecurityException,
    ValidationException,
)


class TestStorageConfig:
    """Test storage configuration."""
    
    def test_default_config(self):
        config = StorageConfig(
            default_provider="local",
            providers={"local": {"type": "local"}},
            routing_rules=[{"provider": "local"}]
        )
        
        assert config.default_provider == "local"
        assert config.max_file_size == 100 * 1024 * 1024
        assert "image/jpeg" in config.allowed_content_types
        assert "application/octet-stream" in config.allowed_content_types
    
    def test_custom_allowed_types(self):
        config = StorageConfig(
            default_provider="local",
            providers={},
            routing_rules=[],
            allowed_content_types={"text/plain"}
        )
        
        assert config.allowed_content_types == {"text/plain"}


class TestArtifactReference:
    """Test artifact reference data class."""
    
    def test_creation(self):
        ref = ArtifactReference(
            artifact_id="test123",
            storage_key="tenant/image/test123",
            storage_provider="local",
            storage_url="http://example.com/file.jpg",
            content_type="image/jpeg",
            size=1024
        )
        
        assert ref.artifact_id == "test123"
        assert ref.storage_key == "tenant/image/test123"
        assert ref.storage_provider == "local"
        assert ref.size == 1024
        assert isinstance(ref.created_at, datetime)
    
    def test_auto_created_at(self):
        ref = ArtifactReference(
            artifact_id="test",
            storage_key="key",
            storage_provider="local",
            storage_url="url",
            content_type="image/jpeg"
        )
        
        # Should have been set automatically
        assert ref.created_at is not None
        assert abs((datetime.now(timezone.utc) - ref.created_at).total_seconds()) < 1


class TestStorageManager:
    """Test storage manager functionality."""
    
    @pytest.fixture
    def config(self):
        return StorageConfig(
            default_provider="local",
            providers={"local": {"type": "local"}},
            routing_rules=[{"provider": "local"}],
            max_file_size=1024 * 1024,  # 1MB for testing
            allowed_content_types={"image/jpeg", "text/plain"}
        )
    
    @pytest.fixture
    def manager(self, config):
        return StorageManager(config)
    
    @pytest.fixture
    def mock_provider(self):
        provider = AsyncMock()
        provider.upload.return_value = "http://example.com/file.jpg"
        return provider
    
    def test_init(self, manager, config):
        assert manager.default_provider == "local"
        assert manager.config == config
        assert len(manager.providers) == 0
    
    def test_register_provider(self, manager, mock_provider):
        manager.register_provider("test", mock_provider)
        assert "test" in manager.providers
        assert manager.providers["test"] == mock_provider
    
    def test_validate_storage_key_valid(self, manager):
        # Valid keys should pass
        assert manager._validate_storage_key("tenant/image/file.jpg") == "tenant/image/file.jpg"
        assert manager._validate_storage_key("simple-file_name.ext") == "simple-file_name.ext"
    
    def test_validate_storage_key_path_traversal(self, manager):
        # Path traversal attempts should fail
        with pytest.raises(SecurityException):
            manager._validate_storage_key("../etc/passwd")
        
        with pytest.raises(SecurityException):
            manager._validate_storage_key("tenant/../other")
        
        with pytest.raises(SecurityException):
            manager._validate_storage_key("/absolute/path")
        
        with pytest.raises(SecurityException):
            manager._validate_storage_key("windows\\path")
    
    def test_validate_content_type_allowed(self, manager):
        # Should not raise for allowed types
        manager._validate_content_type("image/jpeg")
        manager._validate_content_type("text/plain")
    
    def test_validate_content_type_disallowed(self, manager):
        with pytest.raises(ValidationException):
            manager._validate_content_type("application/executable")
    
    def test_validate_file_size_ok(self, manager):
        # Should not raise for allowed sizes
        manager._validate_file_size(1024)  # 1KB
        manager._validate_file_size(1024 * 1024)  # 1MB (limit)
    
    def test_validate_file_size_too_large(self, manager):
        with pytest.raises(ValidationException):
            manager._validate_file_size(2 * 1024 * 1024)  # 2MB > 1MB limit
    
    def test_generate_storage_key_with_board(self, manager):
        key = manager._generate_storage_key(
            artifact_id="test123",
            artifact_type="image", 
            tenant_id="tenant1",
            board_id="board456"
        )
        
        # Should follow pattern: tenant/type/board/artifact_timestamp_uuid/variant
        parts = key.split('/')
        assert parts[0] == "tenant1"
        assert parts[1] == "image"
        assert parts[2] == "board456"
        assert parts[3].startswith("test123_")
        assert parts[4] == "original"
    
    def test_generate_storage_key_without_board(self, manager):
        key = manager._generate_storage_key(
            artifact_id="model789",
            artifact_type="model",
            tenant_id="tenant1"
        )
        
        # Should follow pattern: tenant/type/artifact_timestamp_uuid/variant  
        parts = key.split('/')
        assert parts[0] == "tenant1"
        assert parts[1] == "model"
        assert parts[2].startswith("model789_")
        assert parts[3] == "original"
    
    def test_generate_storage_key_default_tenant(self, manager):
        key = manager._generate_storage_key(
            artifact_id="test",
            artifact_type="image"
        )
        
        assert key.startswith("default/image/")
    
    def test_select_provider_default(self, manager):
        provider = manager._select_provider("image", b"small content")
        assert provider == "local"
    
    def test_select_provider_with_rules(self):
        config = StorageConfig(
            default_provider="local", 
            providers={"local": {}, "s3": {}},
            routing_rules=[
                {
                    "condition": {"artifact_type": "video"},
                    "provider": "s3"
                },
                {
                    "provider": "local"
                }
            ]
        )
        manager = StorageManager(config)
        
        # Video should go to S3
        assert manager._select_provider("video", b"content") == "s3"
        
        # Other types should use default
        assert manager._select_provider("image", b"content") == "local"
    
    def test_parse_size(self, manager):
        assert manager._parse_size("1024") == 1024
        assert manager._parse_size("1KB") == 1024  
        assert manager._parse_size("1MB") == 1024 * 1024
        assert manager._parse_size("1GB") == 1024 * 1024 * 1024
    
    @pytest.mark.asyncio
    async def test_store_artifact_success(self, manager, mock_provider):
        manager.register_provider("local", mock_provider)
        
        content = b"test image content"
        
        ref = await manager.store_artifact(
            artifact_id="test123",
            content=content,
            artifact_type="image",
            content_type="image/jpeg",
            tenant_id="tenant1", 
            board_id="board456"
        )
        
        # Verify artifact reference
        assert ref.artifact_id == "test123"
        assert ref.storage_provider == "local"
        assert ref.content_type == "image/jpeg"
        assert ref.size == len(content)
        assert ref.storage_url == "http://example.com/file.jpg"
        
        # Verify provider was called correctly
        mock_provider.upload.assert_called_once()
        call_args = mock_provider.upload.call_args
        
        # Check arguments: upload(key, content, content_type, metadata)
        assert call_args[0][2] == "image/jpeg"  # content_type argument
        assert call_args[0][1] == content  # content argument
    
    @pytest.mark.asyncio
    async def test_store_artifact_validation_failure(self, manager, mock_provider):
        manager.register_provider("local", mock_provider)
        
        # Invalid content type should fail
        with pytest.raises(ValidationException):
            await manager.store_artifact(
                artifact_id="test",
                content=b"content", 
                artifact_type="image",
                content_type="application/evil",
                tenant_id="tenant1"
            )
        
        # Provider should not be called
        mock_provider.upload.assert_not_called()
    
    @pytest.mark.asyncio 
    async def test_store_artifact_provider_not_found(self, manager):
        # No providers registered - should fail
        with pytest.raises(StorageException, match="Provider not found"):
            await manager.store_artifact(
                artifact_id="test",
                content=b"content",
                artifact_type="image", 
                content_type="image/jpeg"
            )
    
    @pytest.mark.asyncio
    async def test_get_download_url(self, manager, mock_provider):
        manager.register_provider("local", mock_provider)
        mock_provider.get_presigned_download_url.return_value = "http://example.com/download"
        
        url = await manager.get_download_url("test/key", "local")
        
        assert url == "http://example.com/download"
        mock_provider.get_presigned_download_url.assert_called_once_with("test/key")
    
    @pytest.mark.asyncio
    async def test_delete_artifact(self, manager, mock_provider):
        manager.register_provider("local", mock_provider)
        mock_provider.delete.return_value = True
        
        result = await manager.delete_artifact("test/key", "local")
        
        assert result is True
        mock_provider.delete.assert_called_once_with("test/key")