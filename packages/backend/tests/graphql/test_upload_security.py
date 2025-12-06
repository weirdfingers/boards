"""Unit tests for upload security validations."""

from boards.graphql.resolvers.upload import (
    _is_safe_url,
    _sanitize_filename,
    _validate_mime_type,
)


class TestURLSecurity:
    """Test SSRF protection and URL validation."""

    def test_allows_valid_https_url(self):
        """Valid HTTPS URLs should be allowed."""
        is_safe, error = _is_safe_url("https://example.com/image.jpg")
        assert is_safe is True
        assert error is None

    def test_allows_valid_http_url(self):
        """Valid HTTP URLs should be allowed."""
        is_safe, error = _is_safe_url("http://example.com/image.jpg")
        assert is_safe is True
        assert error is None

    def test_blocks_localhost(self):
        """Localhost URLs should be blocked."""
        test_cases = [
            "http://localhost/image.jpg",
            "http://127.0.0.1/image.jpg",
        ]
        for url in test_cases:
            is_safe, error = _is_safe_url(url)
            assert is_safe is False
            assert error is not None
            # Should be blocked with either "localhost" or "loopback" in error
            assert "localhost" in error.lower() or "loopback" in error.lower()

    def test_blocks_private_ips(self):
        """Private IP addresses should be blocked."""
        test_cases = [
            "http://10.0.0.1/image.jpg",
            "http://172.16.0.1/image.jpg",
            "http://192.168.1.1/image.jpg",
        ]
        for url in test_cases:
            is_safe, error = _is_safe_url(url)
            assert is_safe is False
            assert error is not None
            assert "private" in error.lower()

    def test_blocks_link_local_addresses(self):
        """Link-local addresses (AWS metadata) should be blocked."""
        is_safe, error = _is_safe_url("http://169.254.169.254/latest/meta-data/")
        assert is_safe is False
        assert error is not None
        # Link-local is a subset of private IPs, so either message is acceptable
        assert "link-local" in error.lower() or "private" in error.lower()

    def test_blocks_non_http_schemes(self):
        """Non-HTTP schemes should be blocked."""
        test_cases = [
            "file:///etc/passwd",
            "ftp://example.com/file",
            "data:text/plain,hello",
        ]
        for url in test_cases:
            is_safe, error = _is_safe_url(url)
            assert is_safe is False
            assert error is not None
            assert "scheme" in error.lower()

    def test_blocks_invalid_urls(self):
        """Invalid URLs should be blocked."""
        is_safe, error = _is_safe_url("not-a-url")
        assert is_safe is False
        assert error is not None


class TestMIMETypeValidation:
    """Test MIME type validation."""

    def test_validates_image_mime_types(self):
        """Valid image MIME types should be accepted."""
        valid_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
        ]
        for mime_type in valid_types:
            is_valid, error = _validate_mime_type(mime_type, "image", "test.jpg")
            assert is_valid is True
            assert error is None

    def test_validates_video_mime_types(self):
        """Valid video MIME types should be accepted."""
        valid_types = [
            "video/mp4",
            "video/quicktime",
            "video/webm",
        ]
        for mime_type in valid_types:
            is_valid, error = _validate_mime_type(mime_type, "video", "test.mp4")
            assert is_valid is True
            assert error is None

    def test_validates_audio_mime_types(self):
        """Valid audio MIME types should be accepted."""
        valid_types = [
            "audio/mpeg",
            "audio/wav",
            "audio/ogg",
        ]
        for mime_type in valid_types:
            is_valid, error = _validate_mime_type(mime_type, "audio", "test.mp3")
            assert is_valid is True
            assert error is None

    def test_validates_text_mime_types(self):
        """Valid text MIME types should be accepted."""
        valid_types = [
            "text/plain",
            "text/markdown",
            "application/json",
        ]
        for mime_type in valid_types:
            is_valid, error = _validate_mime_type(mime_type, "text", "test.txt")
            assert is_valid is True
            assert error is None

    def test_rejects_mismatched_mime_types(self):
        """MIME types not matching artifact type should be rejected."""
        is_valid, error = _validate_mime_type("video/mp4", "image", "test.mp4")
        assert is_valid is False
        assert error is not None
        assert "does not match" in error.lower()

    def test_handles_mime_type_with_charset(self):
        """MIME types with charset should be normalized."""
        is_valid, error = _validate_mime_type("text/plain; charset=utf-8", "text", "test.txt")
        assert is_valid is True
        assert error is None

    def test_rejects_unsupported_artifact_type(self):
        """Unsupported artifact types should be rejected."""
        is_valid, error = _validate_mime_type("application/pdf", "unknown", "test.pdf")
        assert is_valid is False
        assert error is not None
        assert "unsupported" in error.lower()


class TestFilenameSanitization:
    """Test filename sanitization for path traversal prevention."""

    def test_sanitizes_basic_filename(self):
        """Basic filenames should pass through unchanged."""
        result = _sanitize_filename("image.jpg")
        assert result == "image.jpg"

    def test_removes_path_components(self):
        """Path components should be removed."""
        result = _sanitize_filename("../../../etc/passwd")
        assert result == "passwd"
        assert ".." not in result
        assert "/" not in result

    def test_removes_absolute_paths(self):
        """Absolute paths should be reduced to basename."""
        result = _sanitize_filename("/var/www/html/image.jpg")
        assert result == "image.jpg"

    def test_removes_windows_paths(self):
        """Windows paths should have backslashes converted to underscores on Unix."""
        result = _sanitize_filename("C:\\Users\\test\\image.jpg")
        # On Unix, backslashes are treated as dangerous characters and replaced
        # The colon in C: is also replaced
        assert "\\" not in result
        assert ":" not in result
        assert "image.jpg" in result

    def test_removes_null_bytes(self):
        """Null bytes should be removed."""
        result = _sanitize_filename("image\x00.jpg")
        assert "\x00" not in result

    def test_removes_dangerous_characters(self):
        """Dangerous characters should be replaced."""
        result = _sanitize_filename('test<>:"|?*.jpg')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result

    def test_handles_empty_filename(self):
        """Empty filenames should get a default."""
        result = _sanitize_filename("")
        assert result == "uploaded_file"

    def test_handles_only_dots(self):
        """Filenames with only dots should get a default."""
        result = _sanitize_filename("...")
        assert result == "uploaded_file"

    def test_preserves_unicode_characters(self):
        """Unicode characters should be preserved."""
        result = _sanitize_filename("测试文件.jpg")
        assert "测试文件" in result
        assert ".jpg" in result
