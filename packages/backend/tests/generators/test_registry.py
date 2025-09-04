"""
Tests for the generator registry system.
"""

import pytest
from pydantic import BaseModel

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import BaseGenerator
from boards.generators.registry import GeneratorRegistry


class MockInput(BaseModel):
    """Mock input for testing."""
    prompt: str


class MockOutput(BaseModel):
    """Mock output for testing."""
    result: ImageArtifact


class MockImageGenerator(BaseGenerator):
    """Mock image generator for testing."""

    name = "mock-image"
    artifact_type = "image"
    description = "Mock image generator for testing"

    def get_input_schema(self) -> type[MockInput]:
        return MockInput

    def get_output_schema(self) -> type[MockOutput]:
        return MockOutput

    async def generate(self, inputs: MockInput) -> MockOutput:
        # Mock implementation
        artifact = ImageArtifact(
            generation_id="test",
            storage_url="http://example.com/test.png",
            width=512,
            height=512,
            format="png"
        )
        return MockOutput(result=artifact)

    async def estimate_cost(self, inputs: MockInput) -> float:
        return 0.01


class MockVideoGenerator(BaseGenerator):
    """Mock video generator for testing."""

    name = "mock-video"
    artifact_type = "video"
    description = "Mock video generator for testing"

    def get_input_schema(self) -> type[MockInput]:
        return MockInput

    def get_output_schema(self) -> type[MockOutput]:
        return MockOutput

    async def generate(self, inputs: MockInput) -> MockOutput:
        # Mock implementation - not actually used in registry tests
        raise NotImplementedError

    async def estimate_cost(self, inputs: MockInput) -> float:
        return 0.05


class TestGeneratorRegistry:
    """Tests for GeneratorRegistry."""

    def setup_method(self):
        """Set up fresh registry for each test."""
        self.registry = GeneratorRegistry()
        self.mock_image_gen = MockImageGenerator()
        self.mock_video_gen = MockVideoGenerator()

    def test_register_generator(self):
        """Test registering a generator."""
        self.registry.register(self.mock_image_gen)

        assert len(self.registry) == 1
        assert "mock-image" in self.registry
        assert self.registry.get("mock-image") is self.mock_image_gen

    def test_register_duplicate_name(self):
        """Test registering generators with duplicate names fails."""
        self.registry.register(self.mock_image_gen)

        # Create another generator with same name
        duplicate_gen = MockImageGenerator()

        with pytest.raises(ValueError, match="Generator 'mock-image' is already registered"):
            self.registry.register(duplicate_gen)

    def test_get_nonexistent_generator(self):
        """Test getting non-existent generator returns None."""
        result = self.registry.get("nonexistent")
        assert result is None

    def test_list_all_generators(self):
        """Test listing all generators."""
        self.registry.register(self.mock_image_gen)
        self.registry.register(self.mock_video_gen)

        all_generators = self.registry.list_all()

        assert len(all_generators) == 2
        assert self.mock_image_gen in all_generators
        assert self.mock_video_gen in all_generators

    def test_list_by_artifact_type(self):
        """Test listing generators by artifact type."""
        self.registry.register(self.mock_image_gen)
        self.registry.register(self.mock_video_gen)

        image_generators = self.registry.list_by_artifact_type("image")
        video_generators = self.registry.list_by_artifact_type("video")
        audio_generators = self.registry.list_by_artifact_type("audio")

        assert len(image_generators) == 1
        assert image_generators[0] is self.mock_image_gen

        assert len(video_generators) == 1
        assert video_generators[0] is self.mock_video_gen

        assert len(audio_generators) == 0

    def test_list_names(self):
        """Test listing generator names."""
        self.registry.register(self.mock_image_gen)
        self.registry.register(self.mock_video_gen)

        names = self.registry.list_names()

        assert len(names) == 2
        assert "mock-image" in names
        assert "mock-video" in names

    def test_unregister_generator(self):
        """Test unregistering a generator."""
        self.registry.register(self.mock_image_gen)
        assert len(self.registry) == 1

        result = self.registry.unregister("mock-image")

        assert result is True
        assert len(self.registry) == 0
        assert "mock-image" not in self.registry
        assert self.registry.get("mock-image") is None

    def test_unregister_nonexistent_generator(self):
        """Test unregistering non-existent generator returns False."""
        result = self.registry.unregister("nonexistent")
        assert result is False

    def test_clear_registry(self):
        """Test clearing all generators."""
        self.registry.register(self.mock_image_gen)
        self.registry.register(self.mock_video_gen)
        assert len(self.registry) == 2

        self.registry.clear()

        assert len(self.registry) == 0
        assert self.registry.get("mock-image") is None
        assert self.registry.get("mock-video") is None

    def test_registry_contains(self):
        """Test registry __contains__ method."""
        assert "mock-image" not in self.registry

        self.registry.register(self.mock_image_gen)

        assert "mock-image" in self.registry
        assert "nonexistent" not in self.registry

    def test_registry_len(self):
        """Test registry __len__ method."""
        assert len(self.registry) == 0

        self.registry.register(self.mock_image_gen)
        assert len(self.registry) == 1

        self.registry.register(self.mock_video_gen)
        assert len(self.registry) == 2


class TestGlobalRegistry:
    """Tests for the global registry instance."""

    def setup_method(self):
        """Clear global registry before each test."""
        from boards.generators.registry import registry
        registry.clear()

    def teardown_method(self):
        """Clear global registry after each test."""
        from boards.generators.registry import registry
        registry.clear()

    def test_global_registry_import(self):
        """Test importing global registry."""
        from boards.generators.registry import registry

        assert isinstance(registry, GeneratorRegistry)
        assert len(registry) == 0

    def test_global_registry_usage(self):
        """Test using global registry."""
        from boards.generators.registry import registry

        mock_gen = MockImageGenerator()
        registry.register(mock_gen)

        assert len(registry) == 1
        assert registry.get("mock-image") is mock_gen
