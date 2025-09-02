"""Tests for GCS storage provider."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

from boards.storage.implementations.gcs import GCSStorageProvider
from boards.storage.base import StorageException

# Skip tests if GCS dependencies are not available
pytest.importorskip("google.cloud.storage", reason="google-cloud-storage not available")


class TestGCSStorageProvider:
    """Test GCS storage provider functionality."""

    @pytest.fixture
    def gcs_provider(self):
        """Create GCS provider with mock credentials."""
        return GCSStorageProvider(
            bucket="test-bucket",
            project_id="test-project",
            credentials_path="/path/to/credentials.json",
        )

    @pytest.fixture
    def gcs_provider_with_cdn(self):
        """Create GCS provider with CDN configuration."""
        return GCSStorageProvider(
            bucket="test-bucket",
            project_id="test-project",
            credentials_path="/path/to/credentials.json",
            cdn_domain="cdn.example.com",
        )

    @pytest.fixture
    def gcs_provider_with_json(self):
        """Create GCS provider with JSON credentials."""
        return GCSStorageProvider(
            bucket="test-bucket",
            project_id="test-project",
            credentials_json='{"type": "service_account", "project_id": "test"}',
        )

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
    async def test_upload_bytes_success(self, gcs_provider):
        """Test successful upload of bytes content."""
        test_content = b"test content"
        test_key = "test/file.txt"
        test_content_type = "text/plain"

        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync") as mock_run_sync:
                result = await gcs_provider.upload(test_key, test_content, test_content_type)

                # Verify blob configuration
                assert mock_blob.content_type == test_content_type
                
                # Verify upload was called
                mock_run_sync.assert_called_once_with(
                    mock_blob.upload_from_string, test_content, content_type=test_content_type
                )

                # Verify return URL format
                assert result == f"https://storage.googleapis.com/test-bucket/{test_key}"

    @pytest.mark.asyncio
    async def test_upload_with_cdn_url(self, gcs_provider_with_cdn):
        """Test upload returns CDN URL when configured."""
        test_content = b"test content"
        test_key = "test/file.txt"
        test_content_type = "text/plain"

        with patch.object(gcs_provider_with_cdn, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider_with_cdn, "_run_sync"):
                result = await gcs_provider_with_cdn.upload(test_key, test_content, test_content_type)

                # Should return CDN URL during upload (note: download URLs use signed URLs)
                assert result == f"https://cdn.example.com/{test_key}"

    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, gcs_provider):
        """Test upload with custom metadata."""
        test_content = b"test content"
        test_key = "test/file.txt"
        test_content_type = "text/plain"
        test_metadata = {"Artifact-ID": "123", "Board ID": "board-456"}

        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync"):
                await gcs_provider.upload(test_key, test_content, test_content_type, test_metadata)

                # Verify metadata was sanitized and set
                expected_metadata = {"artifact_id": "123", "board_id": "board-456"}
                assert mock_blob.metadata == expected_metadata

    @pytest.mark.asyncio
    async def test_upload_streaming_content(self, gcs_provider):
        """Test upload with streaming content."""
        
        async def content_generator():
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"

        test_key = "test/large_file.txt"
        test_content_type = "text/plain"

        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync") as mock_run_sync:
                await gcs_provider.upload(test_key, content_generator(), test_content_type)

                # Verify content was collected and uploaded
                mock_run_sync.assert_called_once_with(
                    mock_blob.upload_from_string, b"chunk1chunk2chunk3", content_type=test_content_type
                )

    @pytest.mark.asyncio
    async def test_download_success(self, gcs_provider):
        """Test successful file download."""
        test_key = "test/file.txt"
        test_content = b"downloaded content"

        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync") as mock_run_sync:
                mock_run_sync.return_value = test_content
                
                result = await gcs_provider.download(test_key)

                mock_run_sync.assert_called_once_with(mock_blob.download_as_bytes)
                assert result == test_content

    @pytest.mark.asyncio
    async def test_get_presigned_upload_url(self, gcs_provider):
        """Test presigned upload URL generation."""
        test_key = "test/file.txt"
        test_content_type = "text/plain"
        test_url = "https://storage.googleapis.com/upload-url"

        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync") as mock_run_sync:
                mock_run_sync.return_value = test_url
                
                result = await gcs_provider.get_presigned_upload_url(test_key, test_content_type)

                assert result["url"] == test_url
                assert result["method"] == "PUT"
                assert result["headers"]["Content-Type"] == test_content_type
                assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_get_presigned_download_url(self, gcs_provider):
        """Test presigned download URL generation."""
        test_key = "test/file.txt"
        test_url = "https://storage.googleapis.com/signed-download-url"

        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync") as mock_run_sync:
                mock_run_sync.return_value = test_url
                
                result = await gcs_provider.get_presigned_download_url(test_key)

                assert result == test_url
                mock_run_sync.assert_called_once_with(
                    mock_blob.generate_signed_url,
                    version="v4",
                    expiration=timedelta(hours=1),
                    method="GET",
                )

    @pytest.mark.asyncio
    async def test_delete_success(self, gcs_provider):
        """Test successful file deletion."""
        test_key = "test/file.txt"

        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync") as mock_run_sync:
                result = await gcs_provider.delete(test_key)

                mock_run_sync.assert_called_once_with(mock_blob.delete)
                assert result is True

    @pytest.mark.asyncio
    async def test_exists_true(self, gcs_provider):
        """Test file existence check - file exists."""
        test_key = "test/file.txt"

        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync") as mock_run_sync:
                mock_run_sync.return_value = True
                
                result = await gcs_provider.exists(test_key)

                mock_run_sync.assert_called_once_with(mock_blob.exists)
                assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, gcs_provider):
        """Test file existence check - file does not exist."""
        test_key = "test/nonexistent.txt"

        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync") as mock_run_sync:
                mock_run_sync.side_effect = Exception("File not found")
                
                result = await gcs_provider.exists(test_key)

                assert result is False

    @pytest.mark.asyncio
    async def test_get_metadata(self, gcs_provider):
        """Test file metadata retrieval."""
        test_key = "test/file.txt"

        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            # Mock blob attributes
            mock_blob.size = 1024
            mock_blob.updated = "2023-01-01T00:00:00Z"
            mock_blob.content_type = "text/plain"
            mock_blob.etag = "abcd1234"
            mock_blob.generation = 123456789
            mock_blob.storage_class = "STANDARD"
            mock_blob.cache_control = "public, max-age=3600"
            mock_blob.content_encoding = None
            mock_blob.content_disposition = None
            mock_blob.content_language = None
            mock_blob.metadata = {"custom_key": "custom_value"}
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync") as mock_run_sync:
                result = await gcs_provider.get_metadata(test_key)

                mock_run_sync.assert_called_once_with(mock_blob.reload)
                
                assert result["size"] == 1024
                assert result["content_type"] == "text/plain"
                assert result["etag"] == "abcd1234"
                assert result["storage_class"] == "STANDARD"
                assert result["cache_control"] == "public, max-age=3600"
                assert result["custom_metadata"]["custom_key"] == "custom_value"

    @pytest.mark.asyncio
    async def test_client_initialization_with_json_credentials(self, gcs_provider_with_json):
        """Test client initialization with JSON credentials."""
        with patch("boards.storage.implementations.gcs.storage") as mock_storage, \
             patch("google.oauth2.service_account") as mock_service_account:
            
            mock_credentials = MagicMock()
            mock_service_account.Credentials.from_service_account_info.return_value = mock_credentials
            mock_client = MagicMock()
            mock_storage.Client.return_value = mock_client
            
            # Trigger client initialization
            client = gcs_provider_with_json._get_client()
            
            assert client == mock_client
            mock_service_account.Credentials.from_service_account_info.assert_called_once()
            mock_storage.Client.assert_called_once_with(
                credentials=mock_credentials, project="test-project"
            )

    @pytest.mark.asyncio
    async def test_client_initialization_with_credentials_path(self, gcs_provider):
        """Test client initialization with credentials file path."""
        with patch("boards.storage.implementations.gcs.storage") as mock_storage, \
             patch("pathlib.Path.exists") as mock_exists, \
             patch.dict("os.environ", {}, clear=True):
            
            mock_exists.return_value = True
            mock_client = MagicMock()
            mock_storage.Client.return_value = mock_client
            
            # Trigger client initialization
            client = gcs_provider._get_client()
            
            assert client == mock_client
            assert os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") == "/path/to/credentials.json"
            mock_storage.Client.assert_called_once_with(project="test-project")

    @pytest.mark.asyncio
    async def test_client_initialization_with_default_credentials(self):
        """Test client initialization with default credentials."""
        provider = GCSStorageProvider(bucket="test-bucket", project_id="test-project")
        
        with patch("boards.storage.implementations.gcs.storage") as mock_storage:
            mock_client = MagicMock()
            mock_storage.Client.return_value = mock_client
            
            # Trigger client initialization
            client = provider._get_client()
            
            assert client == mock_client
            mock_storage.Client.assert_called_once_with(project="test-project")

    @pytest.mark.asyncio
    async def test_client_initialization_error(self, gcs_provider):
        """Test error handling during client initialization."""
        with patch("boards.storage.implementations.gcs.storage") as mock_storage:
            mock_storage.Client.side_effect = Exception("Auth failed")
            
            with pytest.raises(StorageException, match="GCS client initialization failed"):
                await gcs_provider.upload("test/key", b"content", "text/plain")

    @pytest.mark.asyncio
    async def test_upload_error_handling(self, gcs_provider):
        """Test error handling during upload."""
        test_content = b"test content"
        test_key = "test/file.txt"
        test_content_type = "text/plain"

        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync") as mock_run_sync:
                mock_run_sync.side_effect = Exception("GCS error")
                
                with pytest.raises(StorageException) as exc_info:
                    await gcs_provider.upload(test_key, test_content, test_content_type)

                assert "GCS upload failed" in str(exc_info.value)

    def test_invalid_import(self):
        """Test behavior when google-cloud-storage is not available."""
        with patch("boards.storage.implementations.gcs._gcs_available", False):
            with pytest.raises(ImportError, match="google-cloud-storage is required"):
                GCSStorageProvider(bucket="test")

    @pytest.mark.asyncio
    async def test_lazy_client_creation(self, gcs_provider):
        """Test that client is created on first use."""
        # Client should not exist initially
        assert gcs_provider._client is None
        
        with patch.object(gcs_provider, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            
            mock_get_client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            with patch.object(gcs_provider, "_run_sync"):
                # This should trigger client creation
                await gcs_provider.upload("test/key", b"content", "text/plain")
                
                # Verify client creation was called
                mock_get_client.assert_called()