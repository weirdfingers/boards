import pytest

from boards.generators.loader import load_generators_from_config
from boards.generators.registry import registry


def _reset_registry():
    registry.clear()


def test_class_loading_with_options_and_name_override(tmp_path, monkeypatch):
    _reset_registry()
    cfg = tmp_path / "gens.yaml"
    cfg.write_text(
        """
strict_mode: true
allow_unlisted: false
generators:
  - class: "boards.generators.testmods.class_gen:ClassGen"
    enabled: true
    name: "custom-class-gen"
    options:
      suffix: "?"
        """,
        encoding="utf-8",
    )

    load_generators_from_config(str(cfg))

    assert "custom-class-gen" in registry
    gen = registry.get("custom-class-gen")
    assert gen is not None
    assert getattr(gen, "suffix") == "?"  # noqa: B009


def test_import_based_loading(tmp_path, monkeypatch):
    _reset_registry()
    cfg = tmp_path / "gens.yaml"
    cfg.write_text(
        """
strict_mode: true
allow_unlisted: false
generators:
  - import: "boards.generators.testmods.import_side_effect"
        """,
        encoding="utf-8",
    )

    load_generators_from_config(str(cfg))
    assert "import-gen" in registry


def test_entrypoint_loading_monkeypatched(tmp_path, monkeypatch):
    _reset_registry()

    # Monkeypatch entry_points() to return our fake class
    from importlib import metadata as importlib_metadata

    class DummyEP:
        def __init__(self, name):
            self.name = name

        def load(self):
            from boards.generators.testmods.class_gen import ClassGen

            return ClassGen

    class DummySelection(list):
        def select(self, group=None):
            if group == "boards.generators":
                return [DummyEP("dummy.ep")]  # type: ignore[list-item]
            return []

    monkeypatch.setattr(importlib_metadata, "entry_points", lambda: DummySelection())

    cfg = tmp_path / "gens.yaml"
    cfg.write_text(
        """
strict_mode: true
allow_unlisted: false
generators:
  - entrypoint: "dummy.ep"
    options:
      suffix: "#"
        """,
        encoding="utf-8",
    )

    load_generators_from_config(str(cfg))
    assert "class-gen" in registry
    gen = registry.get("class-gen")
    assert gen is not None
    assert getattr(gen, "suffix") == "#"  # noqa: B009


def test_strict_mode_fails_on_missing_class(tmp_path):
    _reset_registry()
    cfg = tmp_path / "gens.yaml"
    cfg.write_text(
        """
strict_mode: true
allow_unlisted: false
generators:
  - class: "boards.generators.testmods.missing:Nope"
        """,
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError):
        load_generators_from_config(str(cfg))


def test_non_strict_mode_logs_and_skips(tmp_path):
    _reset_registry()
    cfg = tmp_path / "gens.yaml"
    cfg.write_text(
        """
strict_mode: false
allow_unlisted: false
generators:
  - class: "boards.generators.testmods.missing:Nope"
  - class: "boards.generators.testmods.class_gen:ClassGen"
        """,
        encoding="utf-8",
    )

    load_generators_from_config(str(cfg))
    assert "class-gen" in registry
