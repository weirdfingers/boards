## Adding a Provider

This guide shows how to add a new Provider with minimal code. Providers handle authentication, base URL, and HTTP concerns; generators reference providers declaratively.

### 1) Choose a `type`

Pick a short lowercase identifier, e.g., `replicate`, `fal`, `openai`.

### 2) Implement a thin adapter (optional if identical to existing)

Create `src/boards/providers/builtin/<type>.py`:

```python
from typing import Dict, Any
from ..base import BaseProvider, ProviderConfig


class <TypeTitleCase>Provider(BaseProvider):
    name = "<type>"

    async def validate_credentials(self) -> bool:
        return self.config.api_key is not None

    def build_headers(self) -> Dict[str, str]:
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        headers.update(self.config.additional_headers or {})
        return headers

    def get_base_url(self) -> str:
        return self.config.endpoint or "<https://api.example.com>"
```

You can often reuse an existing generic provider by supplying `endpoint` and `api_key` via YAML, skipping code.

### 3) Configure in `providers.yaml`

```yaml
providers:
  <type>:
    type: <type>
    config:
      base_url: <https://api.example.com>
      api_key_env: EXAMPLE_API_KEY
```

Set `EXAMPLE_API_KEY` in your environment (e.g., `.env`, secret manager). The loader will resolve `api_key_env`.

### 4) Validate locally

- Run `uv run pytest` for unit tests if available
- Optionally add a smoke test generator spec pointing to this provider

### Tips

- Keep provider classes minimal; favor declarative generator specs.
- If rate limits or retries are special, extend the base to customize HTTP client.

