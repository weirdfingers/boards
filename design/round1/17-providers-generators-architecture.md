## Providers and Generators Architecture

This document specifies the detailed design for Providers and Generators in the Boards backend, aligning with the storage/database architecture and Strawberry GraphQL backend outline.

### Goals

- Support user choice of which providers and generators to enable at runtime via configuration.
- Make adding a new generator possible with minimal code, ideally by authoring a declarative spec that references public API docs (e.g. `https://replicate.com/black-forest-labs/flux-1.1-pro/api`, `https://fal.ai/models/fal-ai/qwen-image/api`).
- Keep provider-specific code minimal, focusing providers on authentication, base URL, and HTTP concerns.
- Provide a clear, repeatable process for adding new providers and generators, documented for humans and agentic tools.

### Key Concepts

- Provider: An integration that knows how to authenticate and call one or more external services (e.g., Replicate, FAL). Providers encapsulate HTTP base URL, auth headers, retries, and rate limits.
- Generator: A unit that produces an artifact (image, audio, video, model weights, text) from inputs. Generators are mostly declarative specs describing inputs/outputs and how to call the provider.
- Artifact Types: `image`, `audio`, `video`, `text`, `model` (LoRA, checkpoints), `intermediate`.

### Design Principles

- Configuration first: Enable/disable providers and generators via YAML without code changes.
- Declarative generators: Prefer YAML/JSON specs over Python code. Use a generic HTTP executor that reads specs.
- Thin provider adapters: Minimal Python subclasses implement auth/header policies and base URLs; generator logic is shared.
- Schema-driven UX: Pydantic models (and JSON Schema) define inputs/outputs to auto-generate frontend forms and TS types.
- Observability: Standard events for submission, polling, completion, failure, with provider job IDs recorded.

### Files and Modules

- Backend modules (new):
  - `src/boards/providers/base.py`: Base provider classes and config models
  - `src/boards/providers/registry.py`: Provider registry and YAML loader
  - `src/boards/providers/builtin/{replicate.py,fal.py}`: Minimal built-ins
  - `src/boards/generators/base.py`: Base generator types, Generic REST executor
  - `src/boards/generators/registry.py`: Generator registry and YAML loader
  - `src/boards/generators/schemas.py`: Common input/output base models

- Configuration (examples):
  - `packages/backend/docs/examples/providers.yaml`
  - `packages/backend/docs/examples/generators.yaml`

- Contributor docs:
  - `packages/backend/docs/ADDING_A_PROVIDER.md`
  - `packages/backend/docs/ADDING_A_GENERATOR.md`

### Configuration Model

providers.yaml

```yaml
providers:
  replicate:
    type: replicate
    config:
      base_url: https://api.replicate.com/v1
      api_key_env: REPLICATE_API_TOKEN
  fal:
    type: fal
    config:
      base_url: https://fal.run
      api_key_env: FAL_KEY
```

generators.yaml

```yaml
generators:
  - name: flux-1.1-pro
    display_name: Flux 1.1 Pro
    artifact_type: image
    provider: replicate
    docs: https://replicate.com/black-forest-labs/flux-1.1-pro/api
    io:
      input_schema:
        type: object
        properties:
          prompt: { type: string }
          width: { type: integer, default: 1024 }
          height: { type: integer, default: 1024 }
        required: [prompt]
      output_schema:
        type: object
        properties:
          images: { type: array, items: { type: string, format: uri } }
    execution:
      type: rest
      submit:
        method: POST
        path: /predictions
        json:
          version: "<model-version-hash>"
          input:
            prompt: "${input.prompt}"
            width: "${input.width}"
            height: "${input.height}"
      poll:
        method: GET
        path: /predictions/${job.id}
      extract:
        output_paths: ["output"]
```

Notes:
- `${…}` expressions reference input fields and prior step fields (e.g., `${job.id}` from submit response).
- The generic executor handles submission, polling until a terminal state, and output extraction.

### Runtime Flow

1. Registry loads providers and generators from YAML at startup (path from `Settings.providers_config_path`).
2. A request to create a generation selects a generator by name. The generator references a provider.
3. The Generic REST executor:
   - Builds HTTP requests using provider base URL and auth headers
   - Submits the job; stores provider job ID in DB
   - Polls according to the spec until completion or error
   - Extracts output URLs/bytes; stores artifacts via `StorageManager`
4. The resulting `Generation` entity records input params, provider, generator, artifacts, status, progress.

### Minimal Provider Adapter Interface

- Configure base URL and auth headers (e.g., Bearer token from env)
- Optionally override retry, rate limiting, or webhook verification

### Minimal Generator Spec → Executor

- Support `execution.type: rest` initially (submit/poll/extract). Future: `webhook`, `stream`, `websocket`.
- Input/output schemas are JSON Schema and optionally Pydantic class names.
- Token substitution `${input.*}` and `${prev.*}` for building payloads.

### Error Handling & Observability

- Normalize statuses: `queued`, `running`, `succeeded`, `failed`, `canceled`.
- Map provider states to normalized states via spec or defaults.
- Emit structured logs and progress events with provider/job IDs.

### Frontend Integration

- Input forms generated from JSON Schema, with sensible widgets for `image`, `audio`, `video`, `enum`.
- Type generation script (future) maps JSON Schema → TS types for hooks.

### Extensibility

- New provider: create minimal adapter subclass (auth/base URL), add to YAML.
- New generator: add a YAML spec with schemas and execution mapping; no Python code required.

### Security

- Provider secrets via env or secret manager; never stored in DB.
- Storage keys validated by `StorageManager`.
- Content types validated before upload.

### Migration and Back-compat

- Generators and providers identified by stable `name`. Changes are additive when possible.
- Version a generator by suffix (e.g., `flux-1.1-pro@2025-01`).

