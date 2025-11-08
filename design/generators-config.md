## Generators Configuration Spec

### Objectives

- **Configuration-driven**: Select which generators are available without code changes.
- **Plugin support**: Load generators from external packages via Python entry points.
- **Deterministic ordering**: UI lists reflect configured order.
- **Strict-by-default**: Startup fails if configured generators cannot be loaded.
- **Container-friendly**: Runtime override via mounted files and env vars for Docker/K8s.
- **Back-compat path**: Support current side-effect registration pattern during migration.

### Scope

This spec defines configuration shape, discovery/loader behavior, error handling, and operational guidance. It does not mandate hot-reload; process restart (e.g., uvicorn reload) is sufficient.

### Terminology

- **Generator**: A class implementing `BaseGenerator` with `name`, `artifact_type`, `generate`, etc.
- **Registry**: The global `registry` where loaded generator instances are registered.
- **Loader**: Startup component that reads config and registers generators accordingly.

### Configuration source

Configuration is specified via `settings.generators_config_path` (env var: `BOARDS_GENERATORS_CONFIG_PATH`).

- If not set, no generators are loaded (explicit configuration required).
- If set but the file doesn't exist, a warning is logged and no generators are loaded.

### Configuration schema (YAML/JSON)

Top-level keys:

- `strict_mode` (bool, default: `true`): If true, startup fails on any configured generator load error.
- `allow_unlisted` (bool, default: `false`): If false, block any registration attempts not declared in config (prevents accidental side-effect registrations).
- `generators` (list): Ordered list of generator declarations. Order is preserved for UI.

Generator declaration supports three mutually exclusive forms:

1. Back-compat import (triggers module side-effect registration)

```yaml
generators:
  - import: "boards.generators.implementations.openai.audio.whisper"
    enabled: true
```

2. Class path (preferred): import a class and instantiate

```yaml
generators:
  - class: "boards.generators.implementations.replicate.image.flux_pro.ReplicateFluxProGenerator"
    enabled: true
    name: "replicate-flux-pro" # optional override; defaults to class attribute
    options: # forwarded as keyword args to the constructor
      aspect_ratio: "16:9"
      safety_tolerance: 3
```

3. Entry point (plugin)

```yaml
generators:
  - entrypoint: "myorg.whisper"
    enabled: true
    options: {}
```

Optional per-generator fields:

- `enabled` (bool, default: `true`): Skip if false.
- `name` (string, optional): Override the instance name announced to the registry/UI (must be unique if provided).
- `options` (object, optional): Keyword arguments passed to the generator constructor. Use this to carry default parameters or behavior flags.
- `input_defaults` (object, optional; future-facing): Recommended default input values for UI or server-side request merging. This is not used by constructors; it is advisory metadata consumed by API/UI layers.

### Loader behavior (startup)

For each declaration in `generators` (in order):

1. If `enabled: false` → skip.
2. If `import` → `importlib.import_module(path)`; expect the module to call `registry.register(...)` at import time (back-compat).
3. If `class` → resolve class via `importlib`, verify `issubclass(BaseGenerator)`, construct with `options` as kwargs, then `registry.register(instance)`.
4. If `entrypoint` → resolve via `importlib.metadata.entry_points(group="boards.generators")` by name; load class, instantiate with `options`, register.

Post-conditions and validation:

- Enforce unique generator names (either class-provided or overridden `name`). Duplicate names are errors.
- Validate `artifact_type` is one of known values (e.g., image, video, audio, text, lora). Unknown types are errors.
- If `allow_unlisted: false`, detect and reject any registrations that occur outside of configured declarations.

Error handling:

- With `strict_mode: true` (default), any failure to import, resolve, instantiate, or register a declared generator aborts startup with a clear error message.
- With `strict_mode: false`, log errors and skip failed entries; continue startup.
- Missing required environment (e.g., provider API keys) is treated as a load error.

Observability:

- Log each requested declaration and the resulting registration outcome. Prefer structured logs (generator identifier, mode, error details) using the centralized logger utilities.

### Plugin (entry point) contract

External packages can expose generators via a dedicated entry point group. Example `pyproject.toml`:

```toml
[project.entry-points."boards.generators"]
replicate_flux_pro = "boards.generators.implementations.replicate.image.flux_pro:ReplicateFluxProGenerator"
myorg.whisper = "my_pkg.generators.whisper:OpenAIWhisperGenerator"
```

Operational notes:

- Plugins must be installed in the Python environment of the backend process (e.g., included in the Docker image or installed at runtime).
- The loader discovers available entry points at startup.

### Strict mode (default)

- Default `strict_mode: true` ensures that deployments fail-fast when a configured generator cannot be loaded (e.g., missing API key env var, missing package, invalid options).
- Provide an override for development: `strict_mode: false`.

### Constructor options vs. input defaults

- **Constructor `options` (in spec)**: forwarded as keyword args to the generator’s constructor. Use this for global behavior, model selection, default parameters, or provider configuration at instance level.
- **`input_defaults` (advisory metadata)**: a separate optional object that can be consumed by the API/UI to pre-populate per-invocation inputs. This allows setting UI defaults without coupling to the class constructor. Actual enforcement/merging is handled outside the loader.

### Docker/Kubernetes usage

Mount a config file and point the backend to it via environment variable:

```bash
docker run \
  -e BOARDS_GENERATORS_CONFIG_PATH=/etc/boards/generators.yaml \
  -v $(pwd)/generators.yaml:/etc/boards/generators.yaml:ro \
  -e REPLICATE_API_TOKEN=... \
  -e OPENAI_API_KEY=... \
  myorg/boards-backend:latest
```

Keep secrets (API keys) in env/secret stores; the generators config should not embed secrets.

### Example configuration

```yaml
strict_mode: true
allow_unlisted: false

generators:
  # Back-compat import
  - import: "boards.generators.implementations.openai.audio.whisper"
    enabled: true

  # Class with constructor options and name override
  - class: "boards.generators.implementations.replicate.image.flux_pro.ReplicateFluxProGenerator"
    enabled: true
    name: "replicate-flux-pro"
    options:
      aspect_ratio: "16:9"
      safety_tolerance: 3
    input_defaults: # optional; used by API/UI, not the constructor
      prompt: "A high-quality product shot"

  # External plugin via entry point
  - entrypoint: "myorg.whisper"
    enabled: false
```

### Environment-specific profiles (optional pattern)

For deployments that prefer environment-tagged configs, a single file can include multiple profiles and tooling can select the desired one before handing it to the loader. Example:

```yaml
profiles:
  production:
    strict_mode: true
    generators:
      - entrypoint: "myorg.whisper"
      - class: "boards.generators.implementations.replicate.image.flux_pro.ReplicateFluxProGenerator"
  development:
    strict_mode: false
    generators:
      - import: "boards.generators.implementations.openai.audio.whisper"
```

Note: The loader itself consumes the canonical schema (without `profiles`). Profile selection is done externally (CLI, deployment templating) to keep the loader simple.

### Migration plan

1. **Phase 1 (back-compat)**: Implement loader with support for `import` declarations. Existing modules with `registry.register(...)` will load when explicitly configured.
2. **Phase 2 (preferred)**: Adopt `class` and `entrypoint` declarations. Encourage generators to avoid module-level registration and instead rely on the loader.
3. **Phase 3 (hardening)**: With `allow_unlisted: false`, detect and block side-effect registrations not declared in config; optionally emit deprecation warnings where needed.

### Testing strategy

- Unit tests:
  - Import-mode registration (back-compat).
  - Class-path loading, instantiation with options, validation failures.
  - Entry point discovery and loading by name.
  - Duplicate name detection, ordering preservation, disabled entries.
  - Strict vs non-strict error handling.
- Integration tests:
  - Startup with a sample config; assert GraphQL `generators` list matches configured order and content.
  - Negative tests for missing env vars (e.g., required API keys) causing startup failure under strict mode.

### Observability & logging

- Use centralized logging utilities for structured logs during loading.
- Emit a clear summary on startup: requested N, registered M, skipped K, errors E.

### Notes

- Hot reload is out of scope; rely on process restart (uvicorn reload in development) after config changes.
- This spec does not prescribe the exact settings system; the loader should accept either a provided path or use environment-driven discovery as defined above.
