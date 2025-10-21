---
id: configuration
title: Generators Configuration
description: Configure which generators are available via YAML config file with strict mode and plugin support.
---

This page explains how to control which generators are available at runtime using a YAML configuration file. It covers file path configuration, strict mode, constructor options, and plugin (entry point) support.

## Overview

- Configuration-driven selection of generators (no code changes required)
- Deterministic ordering for UI
- Strict-by-default startup validation
- Works in containers with mounted config files
- Supports external packages via Python entry points

See the full spec in the repo at `design/generators-config.md`.

## Configuration source

Set the path to your generators config file via the `BOARDS_GENERATORS_CONFIG_PATH` environment variable:

```bash
export BOARDS_GENERATORS_CONFIG_PATH=/path/to/generators.yaml
```

If not set, no generators will be loaded by default (explicit configuration required).

## Schema (YAML)

```yaml
strict_mode: true # fail startup if a configured generator can’t load
allow_unlisted: false # block registrations not declared in config

generators:
  # Back-compat import (module triggers registry.register on import)
  - import: "boards.generators.implementations.audio.whisper"
    enabled: true

  # Class-based (preferred): class path + constructor options
  - class: "boards.generators.implementations.image.flux_pro.FluxProGenerator"
    enabled: true
    name: "flux-pro" # optional override for UI/registry
    options: # forwarded to constructor as kwargs
      aspect_ratio: "16:9"
      safety_tolerance: 3

  # Plugin entry point (external package)
  - entrypoint: "myorg.whisper"
    enabled: false
```

## Docker/Kubernetes

Mount a config file and point the backend to it via environment variable:

```bash
docker run \
  -e BOARDS_GENERATORS_CONFIG_PATH=/etc/boards/generators.yaml \
  -v $(pwd)/generators.yaml:/etc/boards/generators.yaml:ro \
  -e REPLICATE_API_TOKEN=... \
  -e OPENAI_API_KEY=... \
  myorg/boards-backend:latest
```

Keep API keys in env/secret stores; do not embed secrets in the generators config.

## Plugin (entry point) contract

External packages expose generators via entry points:

```toml
[project.entry-points."boards.generators"]
myorg.whisper = "my_pkg.generators.whisper:WhisperGenerator"
```

Then reference by name in the config:

```yaml
generators:
  - entrypoint: "myorg.whisper"
```

## Example file

See `packages/backend/examples/generators.yaml` for a complete example.
