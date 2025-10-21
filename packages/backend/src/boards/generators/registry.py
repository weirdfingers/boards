"""
Generator registry system for discovering and managing generators.
"""

from boards.logging import get_logger

from .base import BaseGenerator

logger = get_logger(__name__)


class GeneratorRegistry:
    """
    Central registry for generator discovery and management.

    Provides methods to register generators, look them up by name,
    and list available generators by various criteria.
    """

    def __init__(self):
        self._generators: dict[str, BaseGenerator] = {}

    def register(self, generator: BaseGenerator) -> None:
        """
        Register a generator instance with the registry.

        Args:
            generator: Generator instance to register

        Raises:
            ValueError: If a generator with the same name is already registered
        """
        logger.info("Registering generator", name=generator.name)
        if generator.name in self._generators:
            raise ValueError(f"Generator '{generator.name}' is already registered")

        self._generators[generator.name] = generator

    def get(self, name: str) -> BaseGenerator | None:
        """
        Get a generator by name.

        Args:
            name: Name of the generator to retrieve

        Returns:
            BaseGenerator instance or None if not found
        """
        return self._generators.get(name)

    def list_all(self) -> list[BaseGenerator]:
        """
        List all registered generators.

        Returns:
            List of all generator instances
        """
        return list(self._generators.values())

    def list_by_artifact_type(self, artifact_type: str) -> list[BaseGenerator]:
        """
        List generators that produce a specific artifact type.

        Args:
            artifact_type: Type of artifact (image, video, audio, text, lora)

        Returns:
            List of generators that produce the specified artifact type
        """
        return [
            generator
            for generator in self._generators.values()
            if generator.artifact_type == artifact_type
        ]

    def list_names(self) -> list[str]:
        """
        List all registered generator names.

        Returns:
            List of generator names
        """
        return list(self._generators.keys())

    def unregister(self, name: str) -> bool:
        """
        Unregister a generator by name.

        Args:
            name: Name of the generator to unregister

        Returns:
            True if the generator was found and removed, False otherwise
        """
        if name in self._generators:
            del self._generators[name]
            return True
        return False

    def clear(self) -> None:
        """Clear all registered generators."""
        self._generators.clear()

    def __len__(self) -> int:
        """Return the number of registered generators."""
        return len(self._generators)

    def __contains__(self, name: str) -> bool:
        """Check if a generator with the given name is registered."""
        return name in self._generators


# Global registry instance
registry = GeneratorRegistry()
