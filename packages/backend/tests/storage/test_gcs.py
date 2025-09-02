"""Simplified tests for GCS storage provider focusing on lazy initialization."""

import pytest
from unittest.mock import patch, MagicMock

from boards.storage.implementations.gcs import GCSStorageProvider
from boards.storage.base import StorageException

# Skip tests if GCS dependencies are not available
pytest.importorskip("google.cloud.storage", reason="google-cloud-storage not available")


class TestGCSStorageProviderLazy:
    """Test GCS storage provider with focus on lazy initialization."""

    def test_instantiation_without_credentials(self):
        """Test that provider can be instantiated without real credentials."""
        # This should work now with lazy initialization
        provider = GCSStorageProvider(
            bucket="test-bucket",
            project_id="test-project",
            credentials_path="/nonexistent/path.json",
        )
        
        # Client should not be created yet
        assert provider._client is None
        assert provider._bucket is None

    @pytest.mark.asyncio
    async def test_lazy_client_creation(self):
        """Test that client is created on first use."""
        with patch("boards.storage.implementations.gcs.storage") as mock_storage:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_storage.Client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            provider = GCSStorageProvider(bucket="test-bucket", project_id="test")
            
            # Client not created yet
            assert provider._client is None
            
            # Mock the _run_sync method to prevent actual execution
            with patch.object(provider, "_run_sync") as mock_run_sync:
                # This should trigger client creation
                await provider.upload("test/key", b"content", "text/plain")
                
                # Now client should be created
                mock_storage.Client.assert_called_once()
                assert provider._client == mock_client

    @pytest.mark.asyncio
    async def test_client_initialization_error(self):
        """Test error handling during client initialization."""
        with patch("boards.storage.implementations.gcs.storage") as mock_storage:
            mock_storage.Client.side_effect = Exception("Auth failed")
            
            provider = GCSStorageProvider(bucket="test-bucket", project_id="test")
            
            with pytest.raises(StorageException, match="GCS client initialization failed"):
                await provider.upload("test/key", b"content", "text/plain")

    @pytest.mark.asyncio 
    async def test_operations_with_mocked_client(self):
        """Test that all main operations work with mocked client."""
        with patch("boards.storage.implementations.gcs.storage") as mock_storage:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_storage.Client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            provider = GCSStorageProvider(bucket="test-bucket", project_id="test")
            
            with patch.object(provider, "_run_sync") as mock_run_sync:
                # Test upload
                mock_run_sync.return_value = None
                result = await provider.upload("test/key", b"content", "text/plain")
                assert result == "https://storage.googleapis.com/test-bucket/test/key"
                
                # Test download  
                mock_run_sync.return_value = b"content"
                content = await provider.download("test/key")
                assert content == b"content"
                
                # Test delete
                mock_run_sync.return_value = None
                success = await provider.delete("test/key")
                assert success is True
                
                # Test exists
                mock_run_sync.return_value = True
                exists = await provider.exists("test/key")
                assert exists is True

    def test_invalid_import(self):
        """Test behavior when google-cloud-storage is not available."""
        with patch("boards.storage.implementations.gcs._gcs_available", False):
            with pytest.raises(ImportError, match="google-cloud-storage is required"):
                GCSStorageProvider(bucket="test")

    def test_cdn_url_generation(self):
        """Test CDN URL generation without client creation."""
        provider = GCSStorageProvider(
            bucket="test-bucket",
            project_id="test",
            cdn_domain="cdn.example.com"
        )
        
        # CDN URL should be returned without client creation for download URLs
        with patch.object(provider, "_get_client") as mock_get_client:
            # Mock should not be called for CDN URLs
            async def test_cdn():
                url = await provider.get_presigned_download_url("test/key")
                assert url == "https://cdn.example.com/test/key"
                mock_get_client.assert_not_called()
            
            import asyncio
            asyncio.run(test_cdn())