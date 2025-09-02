"""Provider registry and YAML loader."""

from __future__ import annotations

import os
from typing import Dict, Any
import yaml

from .base import BaseProvider, ProviderConfig


class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._constructors: Dict[str, type[BaseProvider]] = {}

    def register_type(self, type_name: str, cls: type[BaseProvider]) -> None:
        self._constructors[type_name] = cls

    def register_instance(self, name: str, provider: BaseProvider) -> None:
        self._providers[name] = provider

    def get(self, name: str) -> BaseProvider:
        return self._providers[name]

    def load_from_yaml(self, yaml_path: str) -> None:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        providers = (data.get("providers") or {})
        for name, node in providers.items():
            type_name = node.get("type", name)
            config_dict: Dict[str, Any] = (node.get("config") or {}).copy()

            # Resolve api_key from environment if api_key_env is provided
            api_key_env = config_dict.pop("api_key_env", None)
            if api_key_env:
                config_dict["api_key"] = os.getenv(api_key_env)

            cfg = ProviderConfig(**config_dict)
            cls = self._constructors.get(type_name)
            if cls is None:
                raise ValueError(f"Unknown provider type: {type_name}")
            instance = cls(cfg)
            self.register_instance(name, instance)


provider_registry = ProviderRegistry()

