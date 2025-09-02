"""Helpers to load providers and generators from example YAML during dev."""

from __future__ import annotations

from pathlib import Path
from .providers.registry import provider_registry
from .generators.registry import generator_registry


def load_examples(base: str | Path) -> None:
    base = Path(base)
    providers_yaml = base / "docs" / "examples" / "providers.yaml"
    generators_yaml = base / "docs" / "examples" / "generators.yaml"
    if providers_yaml.exists():
        provider_registry.load_from_yaml(str(providers_yaml))
    if generators_yaml.exists():
        generator_registry.load_from_yaml(str(generators_yaml))

