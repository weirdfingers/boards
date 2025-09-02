"""Tests for S3 storage provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

from boards.storage.implementations.s3 import S3StorageProvider
from boards.storage.base import StorageException

# Skip tests if S3 dependencies are not available
pytest.importorskip("boto3", reason="boto3 not available")
pytest.importorskip("aioboto3", reason="aioboto3 not available")


class TestS3StorageProvider:
    """Test S3 storage provider functionality."""

    @pytest.fixture
    def s3_provider(self):
        """Create S3 provider with mock credentials."""
        return S3StorageProvider(
            bucket="test-bucket",
            region="us-east-1",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
        )

    @pytest.fixture
    def s3_provider_with_cloudfront(self):
        """Create S3 provider with CloudFront configuration."""
        return S3StorageProvider(
            bucket="test-bucket",
            region="us-east-1",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            cloudfront_domain="d123456.cloudfront.net",
        )

    @pytest.mark.asyncio
    async def test_upload_bytes_success(self, s3_provider):
        """Test successful upload of bytes content."""
        test_content = b"test content"
        test_key = "test/file.txt"
        test_content_type = "text/plain"

        with patch.object(s3_provider, "_get_session") as mock_session:
            mock_client = AsyncMock()
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client

            result = await s3_provider.upload(test_key, test_content, test_content_type)

            # Verify upload was called with correct parameters
            mock_client.put_object.assert_called_once()
            call_args = mock_client.put_object.call_args[1]

            assert call_args["Bucket"] == "test-bucket"
            assert call_args["Key"] == test_key
            assert call_args["ContentType"] == test_content_type
            assert call_args["Body"] == test_content

            # Verify return URL format
            assert result == f"https://test-bucket.s3.us-east-1.amazonaws.com/{test_key}"

    @pytest.mark.asyncio
    async def test_upload_with_cloudfront_url(self, s3_provider_with_cloudfront):
        """Test upload returns CloudFront URL when configured."""
        test_content = b"test content"
        test_key = "test/file.txt"
        test_content_type = "text/plain"

        with patch.object(s3_provider_with_cloudfront, "_get_session") as mock_session:
            mock_client = AsyncMock()
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client

            result = await s3_provider_with_cloudfront.upload(test_key, test_content, test_content_type)

            # Should return CloudFront URL
            assert result == f"https://d123456.cloudfront.net/{test_key}"

    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, s3_provider):
        """Test upload with custom metadata."""
        test_content = b"test content"
        test_key = "test/file.txt"
        test_content_type = "text/plain"
        test_metadata = {"artifact_id": "123", "board_id": "board-456"}

        with patch.object(s3_provider, "_get_session") as mock_session:
            mock_client = AsyncMock()
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client

            await s3_provider.upload(test_key, test_content, test_content_type, test_metadata)

            # Verify metadata was included
            call_args = mock_client.put_object.call_args[1]
            assert "Metadata" in call_args
            assert call_args["Metadata"]["artifact_id"] == "123"
            assert call_args["Metadata"]["board_id"] == "board-456"

    @pytest.mark.asyncio
    async def test_download_success(self, s3_provider):
        """Test successful file download."""
        test_key = "test/file.txt"
        test_content = b"downloaded content"

        with patch.object(s3_provider, "_get_session") as mock_session:
            mock_client = AsyncMock()
            mock_response = {"Body": AsyncMock()}
            mock_response["Body"].read = AsyncMock(return_value=test_content)
            mock_client.get_object.return_value = mock_response
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client

            result = await s3_provider.download(test_key)

            mock_client.get_object.assert_called_once_with(Bucket="test-bucket", Key=test_key)
            assert result == test_content

    @pytest.mark.asyncio
    async def test_get_presigned_upload_url(self, s3_provider):
        """Test presigned upload URL generation."""
        test_key = "test/file.txt"
        test_content_type = "text/plain"
        test_url = "https://test-bucket.s3.amazonaws.com/presigned-upload"
        test_fields = {"Content-Type": test_content_type}

        with patch.object(s3_provider, "_get_session") as mock_session:
            mock_client = AsyncMock()
            mock_client.generate_presigned_post.return_value = {
                "url": test_url,
                "fields": test_fields,
            }
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client

            result = await s3_provider.get_presigned_upload_url(test_key, test_content_type)

            assert result["url"] == test_url
            assert result["fields"] == test_fields
            assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_get_presigned_download_url(self, s3_provider):
        """Test presigned download URL generation."""
        test_key = "test/file.txt"
        test_url = "https://test-bucket.s3.amazonaws.com/presigned-download"

        with patch.object(s3_provider, "_get_session") as mock_session:
            mock_client = AsyncMock()
            mock_client.generate_presigned_url.return_value = test_url
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client

            result = await s3_provider.get_presigned_download_url(test_key)

            assert result == test_url

    @pytest.mark.asyncio
    async def test_get_presigned_download_url_with_cloudfront(self, s3_provider_with_cloudfront):
        """Test presigned download URL returns CloudFront URL when configured."""
        test_key = "test/file.txt"

        result = await s3_provider_with_cloudfront.get_presigned_download_url(test_key)

        assert result == f"https://d123456.cloudfront.net/{test_key}"

    @pytest.mark.asyncio
    async def test_delete_success(self, s3_provider):
        """Test successful file deletion."""
        test_key = "test/file.txt"

        with patch.object(s3_provider, "_get_session") as mock_session:
            mock_client = AsyncMock()
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client

            result = await s3_provider.delete(test_key)

            mock_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key=test_key)
            assert result is True

    @pytest.mark.asyncio
    async def test_exists_true(self, s3_provider):
        """Test file existence check - file exists."""
        test_key = "test/file.txt"

        with patch.object(s3_provider, "_get_session") as mock_session:
            mock_client = AsyncMock()
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client

            result = await s3_provider.exists(test_key)

            mock_client.head_object.assert_called_once_with(Bucket="test-bucket", Key=test_key)
            assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, s3_provider):
        """Test file existence check - file does not exist."""
        test_key = "test/nonexistent.txt"

        with patch.object(s3_provider, "_get_session") as mock_session:
            mock_client = AsyncMock()
            mock_client.head_object.side_effect = Exception("File not found")
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client

            result = await s3_provider.exists(test_key)

            assert result is False

    @pytest.mark.asyncio
    async def test_get_metadata(self, s3_provider):
        """Test file metadata retrieval."""
        test_key = "test/file.txt"
        test_metadata = {
            "ContentLength": 1024,
            "LastModified": "2023-01-01T00:00:00Z",
            "ContentType": "text/plain",
            "ETag": '"abcd1234"',
            "StorageClass": "STANDARD",
            "Metadata": {"custom_key": "custom_value"},
        }

        with patch.object(s3_provider, "_get_session") as mock_session:
            mock_client = AsyncMock()
            mock_client.head_object.return_value = test_metadata
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client

            result = await s3_provider.get_metadata(test_key)

            assert result["size"] == 1024
            assert result["content_type"] == "text/plain"
            assert result["etag"] == "abcd1234"
            assert result["storage_class"] == "STANDARD"
            assert result["custom_metadata"]["custom_key"] == "custom_value"

    @pytest.mark.asyncio
    async def test_upload_error_handling(self, s3_provider):
        """Test error handling during upload."""
        test_content = b"test content"
        test_key = "test/file.txt"
        test_content_type = "text/plain"

        with patch.object(s3_provider, "_get_session") as mock_session:
            mock_client = AsyncMock()
            mock_client.put_object.side_effect = Exception("S3 error")
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(StorageException) as exc_info:
                await s3_provider.upload(test_key, test_content, test_content_type)

            assert "S3 upload failed" in str(exc_info.value)

    def test_invalid_import(self):
        """Test behavior when boto3/aioboto3 is not available."""
        with patch("boards.storage.implementations.s3._s3_available", False):
            with pytest.raises(ImportError, match="boto3 and aioboto3 are required"):
                S3StorageProvider(bucket="test")