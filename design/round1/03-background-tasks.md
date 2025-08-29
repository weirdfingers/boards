# Background Tasks

- **Flow**: client submits job → API enqueues → worker runs model call → writes status/progress → finalizes artifacts/credits.
- **Queue**: RQ or Dramatiq (lightweight). Redis recommended for pub/sub progress events.
- **Progress**: workers publish percentage/phase; API exposes **SSE**/polling; frontend `useGeneration` hooks subscribe.
- **Reliability**: retries with backoff; idempotent finalization (reserve→finalize→refund); cancellation tokens.
- **Security**: scoped credentials per provider; redact prompts where required; audit logs.
