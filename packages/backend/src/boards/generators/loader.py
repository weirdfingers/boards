"""Configuration-driven generator loader.

Loads and registers generators based on configuration file.
File path is specified via settings.generators_config_path.

Supports three declaration forms: import, class, entrypoint.
Strict mode is enabled by default and will fail startup on errors.
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

from .base import BaseGenerator
from .registry import registry

logger = get_logger(__name__)


ENTRYPOINT_GROUP = "boards.generators"

VALID_ARTIFACT_TYPES: set[str] = {"image", "video", "audio", "text", "lora"}


@dataclass
class LoaderConfig:
    strict_mode: bool = True
    allow_unlisted: bool = False
    declarations: list[dict[str, Any]] | None = None


def _load_file_config(path: str) -> LoaderConfig | None:
    try:
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return None

    strict_mode = bool(data.get("strict_mode", True))
    allow_unlisted = bool(data.get("allow_unlisted", False))
    declarations = list(data.get("generators", []) or [])

    return LoaderConfig(
        strict_mode=strict_mode,
        allow_unlisted=allow_unlisted,
        declarations=declarations,
    )


def _discover_config() -> LoaderConfig | None:
    """Discover config from settings.generators_config_path."""
    if not settings.generators_config_path:
        return None

    path = Path(settings.generators_config_path)
    if not path.exists():
        logger.warning("Generators config path set but not found", path=str(path))
        return None

    cfg = _load_file_config(str(path))
    if cfg:
        logger.info("Loaded generators config from settings", path=str(path))
    return cfg


def _resolve_class(qualified_name: str) -> type[BaseGenerator]:
    if ":" in qualified_name:
        module_name, class_name = qualified_name.split(":", 1)
    else:
        # Split on last dot for module path
        module_name, class_name = qualified_name.rsplit(".", 1)

    module = import_module(module_name)
    cls = getattr(module, class_name)
    if not isinstance(cls, type) or not issubclass(cls, BaseGenerator):
        raise TypeError(f"Resolved object is not a BaseGenerator subclass: {qualified_name}")
    return cls


def _resolve_entrypoint(name: str) -> type[BaseGenerator]:
    try:
        eps = importlib_metadata.entry_points()
        # Python 3.12 returns a Selection object with .select
        group_filtered: Iterable[Any]
        if hasattr(eps, "select"):
            group_filtered = eps.select(group=ENTRYPOINT_GROUP)
        else:
            group_filtered = eps.get(ENTRYPOINT_GROUP, [])  # type: ignore[attr-defined]
    except Exception as e:  # pragma: no cover - edge cases
        raise RuntimeError(f"Failed to read entry points: {e}") from e

    for ep in group_filtered:
        if getattr(ep, "name", None) == name:
            obj = ep.load()
            if not isinstance(obj, type) or not issubclass(obj, BaseGenerator):
                raise TypeError(f"Entry point '{name}' is not a BaseGenerator class")
            return obj

    raise LookupError(f"Entry point not found: {name}")


def _validate_artifact_type(instance: BaseGenerator) -> None:
    artifact_type = getattr(instance, "artifact_type", None)
    if not artifact_type or artifact_type not in VALID_ARTIFACT_TYPES:
        raise ValueError(f"Invalid artifact_type: {artifact_type}")


def _register_instance(instance: BaseGenerator, name_override: str | None) -> None:
    if name_override:
        # Override instance name if provided
        try:
            instance.name = name_override
        except Exception as e:
            raise ValueError(f"Failed to set generator name override: {e}") from e

    _validate_artifact_type(instance)
    registry.register(instance)


def _enforce_unlisted_policy(
    allowed_names: set[str], strict_mode: bool, allow_unlisted: bool
) -> None:
    registered = set(registry.list_names())
    extras = registered - allowed_names
    if not extras:
        return

    msg = f"Found unlisted generator registrations: {sorted(extras)}"
    if allow_unlisted:
        logger.warning(msg)
        return

    # Not allowed. Attempt to unregister extras then decide based on strict_mode.
    for name in extras:
        try:
            registry.unregister(name)
        except Exception:  # pragma: no cover - defensive
            pass

    if strict_mode:
        raise RuntimeError(msg)
    else:
        logger.error(msg)


def load_generators_from_config(config_path: str | None = None) -> None:
    """Load and register generators according to configuration.

    Raises on errors when strict mode is enabled (default).
    """

    # Discover configuration
    cfg: LoaderConfig | None
    if config_path:
        cfg = _load_file_config(config_path)
        if cfg:
            logger.info("Loaded generators config from explicit path", path=config_path)
    else:
        cfg = _discover_config()

    # If nothing configured, do nothing (no implicit imports)
    if not cfg or not cfg.declarations:
        logger.info("No generators configuration found; skipping generator loading")
        return

    strict_mode = cfg.strict_mode
    allow_unlisted = cfg.allow_unlisted

    requested_names: set[str] = set()

    # Process declarations in order
    for decl in cfg.declarations:
        if not isinstance(decl, dict):
            msg = f"Invalid generator declaration type: {type(decl)}"
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
                # Back-compat path relies on module side-effect registration.
                # We cannot infer the name here reliably; collect after loop.
                logger.info("Imported generator module", import_path=import_path)
            elif "class" in decl:
                qualified = decl["class"]
                options = decl.get("options", {}) or {}
                cls = _resolve_class(qualified)
                instance = cls(**options) if options else cls()
                _register_instance(instance, name_override)
                requested_names.add(instance.name)
                logger.info(
                    "Registered generator via class",
                    class_path=qualified,
                    name=instance.name,
                )
            elif "entrypoint" in decl:
                ep_name = decl["entrypoint"]
                options = decl.get("options", {}) or {}
                cls = _resolve_entrypoint(ep_name)
                instance = cls(**options) if options else cls()
                _register_instance(instance, name_override)
                requested_names.add(instance.name)
                logger.info(
                    "Registered generator via entrypoint",
                    entrypoint=ep_name,
                    name=instance.name,
                )
            else:
                raise ValueError(
                    "Generator declaration must include one of: import, class, entrypoint"
                )

        except Exception as e:
            msg = f"Failed to load generator declaration: {e}"
            if strict_mode:
                raise RuntimeError(msg) from e
            logger.error(msg)
            continue

    # After imports, collect names to enforce allow_unlisted policy
    # requested_names may be incomplete for `import` declarations; fill with registry state
    for name in registry.list_names():
        requested_names.add(name)

    _enforce_unlisted_policy(requested_names, strict_mode, allow_unlisted)

    # Final summary
    logger.info(
        "Generators loading complete",
        requested=len(cfg.declarations or []),
        registered=len(registry),
        names=registry.list_names(),
        strict_mode=strict_mode,
        allow_unlisted=allow_unlisted,
    )
