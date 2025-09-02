## Contributing Providers and Generators

This document helps you (and agentic tools) contribute Providers and Generators with minimal custom code.

### Quick Start

1. Copy `docs/examples/providers.yaml` and `docs/examples/generators.yaml`
2. Set required API keys in your environment (e.g., `REPLICATE_API_TOKEN`)
3. Start backend; registries will auto-load specs

### Provider Checklist

- Pick a unique provider key (e.g., `replicate`, `fal`)
- Define `base_url` and `api_key_env` in `providers.yaml`
- Only write a Python adapter if special auth or headers are needed

### Generator Checklist

- Choose a `name` and `artifact_type`
- Link to a `provider` defined in `providers.yaml`
- Write JSON Schema for inputs/outputs (drives UI and validation)
- Define `execution` with submit/poll/extract for REST

### Testing

- Add smoke specs that hit real APIs sparingly
- Use mocking for CI

### Docs

- Include `docs` URL pointing to upstream API reference for maintainability

For detailed steps, see `ADDING_A_PROVIDER.md` and `ADDING_A_GENERATOR.md`.

