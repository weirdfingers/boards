"""Configuration-driven plugin loader.

Loads and registers artifact plugins based on configuration file.
File path is specified via settings.plugins_config_path or
BOARDS_PLUGINS_CONFIG_PATH environment variable.

Mirrors the generator loader pattern: supports import, class, and
entrypoint declaration forms with strict mode.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

import yaml

from boards.config import settings
from boards.logging import get_logger

from .base import BaseArtifactPlugin
from .registry import plugin_registry

logger = get_logger(__name__)


ENTRYPOINT_GROUP = "boards.plugins"


@dataclass
class PluginLoaderConfig:
    strict_mode: bool = True
    declarations: list[dict[str, Any]] | None = None


def _load_file_config(path: str) -> PluginLoaderConfig | None:
    try:
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return None

    strict_mode = bool(data.get("strict_mode", True))
    declarations = list(data.get("plugins", []) or [])

    return PluginLoaderConfig(
        strict_mode=strict_mode,
        declarations=declarations,
    )


def _discover_config() -> PluginLoaderConfig | None:
    """Discover config from settings.plugins_config_path."""
    if not settings.plugins_config_path:
        return None

    path = Path(settings.plugins_config_path)
    if not path.exists():
        logger.warning("Plugins config path set but not found", path=str(path))
        return None

    cfg = _load_file_config(str(path))
    if cfg:
        logger.info("Loaded plugins config from settings", path=str(path))
    return cfg


def _resolve_class(qualified_name: str) -> type[BaseArtifactPlugin]:
    if ":" in qualified_name:
        module_name, class_name = qualified_name.split(":", 1)
    else:
        module_name, class_name = qualified_name.rsplit(".", 1)

    module = import_module(module_name)
    cls = getattr(module, class_name)
    if not isinstance(cls, type) or not issubclass(cls, BaseArtifactPlugin):
        raise TypeError(
            f"Resolved object is not a BaseArtifactPlugin subclass: {qualified_name}"
        )
    return cls


def _resolve_entrypoint(name: str) -> type[BaseArtifactPlugin]:
    try:
        eps = importlib_metadata.entry_points()
        group_filtered: Iterable[Any]
        if hasattr(eps, "select"):
            group_filtered = eps.select(group=ENTRYPOINT_GROUP)
        else:
            group_filtered = eps.get(ENTRYPOINT_GROUP, [])  # type: ignore[attr-defined]
    except Exception as e:
        raise RuntimeError(f"Failed to read entry points: {e}") from e

    for ep in group_filtered:
        if getattr(ep, "name", None) == name:
            obj = ep.load()
            if not isinstance(obj, type) or not issubclass(obj, BaseArtifactPlugin):
                raise TypeError(f"Entry point '{name}' is not a BaseArtifactPlugin class")
            return obj

    raise LookupError(f"Entry point not found: {name}")


def _register_instance(instance: BaseArtifactPlugin, name_override: str | None) -> None:
    if name_override:
        try:
            instance.name = name_override
        except Exception as e:
            raise ValueError(f"Failed to set plugin name override: {e}") from e

    plugin_registry.register(instance)


def load_plugins_from_config(config_path: str | None = None) -> None:
    """Load and register plugins according to configuration.

    Raises on errors when strict mode is enabled (default).
    """
    cfg: PluginLoaderConfig | None
    if config_path:
        cfg = _load_file_config(config_path)
        if cfg:
            logger.info("Loaded plugins config from explicit path", path=config_path)
    else:
        cfg = _discover_config()

    if not cfg or not cfg.declarations:
        logger.info("No plugins configuration found; skipping plugin loading")
        return

    strict_mode = cfg.strict_mode

    for decl in cfg.declarations:
        if not isinstance(decl, dict):
            msg = f"Invalid plugin declaration type: {type(decl)}"
            if strict_mode:
                raise ValueError(msg)
            logger.error(msg)
            continue

        if decl.get("enabled") is False:
            continue

        name_override = decl.get("name")

        try:
            if "import" in decl:
                import_path = decl["import"]
                import_module(import_path)
                logger.info("Imported plugin module", import_path=import_path)
            elif "class" in decl:
                qualified = decl["class"]
                options = decl.get("options", {}) or {}
                cls = _resolve_class(qualified)
                instance = cls(**options) if options else cls()
                _register_instance(instance, name_override)
                logger.debug(
                    "Registered plugin via class",
                    class_path=qualified,
                    name=instance.name,
                )
            elif "entrypoint" in decl:
                ep_name = decl["entrypoint"]
                options = decl.get("options", {}) or {}
                cls = _resolve_entrypoint(ep_name)
                instance = cls(**options) if options else cls()
                _register_instance(instance, name_override)
                logger.debug(
                    "Registered plugin via entrypoint",
                    entrypoint=ep_name,
                    name=instance.name,
                )
            else:
                raise ValueError(
                    "Plugin declaration must include one of: import, class, entrypoint"
                )

        except Exception as e:
            msg = f"Failed to load plugin declaration: {e}"
            if strict_mode:
                raise RuntimeError(msg) from e
            logger.error(msg)
            continue

    logger.info(
        "Plugins loading complete",
        requested=len(cfg.declarations or []),
        registered=len(plugin_registry),
        names=plugin_registry.list_names(),
        strict_mode=strict_mode,
    )
