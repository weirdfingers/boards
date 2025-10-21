---
id: configuration
title: Generators Configuration
description: Configure which generators are available via file/env, with strict mode and plugin support.
---

This page explains how to control which generators are available at runtime using configuration. It covers file/env sources, strict mode, constructor options, and plugin (entry point) support.

## Overview

- Configuration-driven selection of generators (no code changes required)
- Deterministic ordering for UI
- Strict-by-default startup validation
- Works in containers with mounted config or env vars
- Supports external packages via Python entry points

See the full spec in the repo at `design/generators-config.md`.

## Configuration sources (highest precedence first)

1. `BOARDS_GENERATORS_CONFIG` → path to YAML/JSON file
2. Default file `/app/config/generators.yaml` (baked into image)
3. `BOARDS_GENERATORS` (flat, comma-separated list for simple cases)

Only the first available source is used (no merging).

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

Flat env examples (no options support):

```bash
export BOARDS_GENERATORS="boards.generators.implementations.audio.whisper,boards.generators.implementations.image.flux_pro"
export BOARDS_GENERATORS="class:my_pkg.generators.sd.SDGenerator,entrypoint:myorg.whisper"
```

## Docker/Kubernetes

Mount a config file and point the backend to it:

```bash
docker run \
  -e BOARDS_GENERATORS_CONFIG=/etc/boards/generators.yaml \
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
