# Baseboards - Image Generation Platform

This is a self-hosted Baseboards installation, scaffolded by the Baseboards CLI.

## Quick Start

### Prerequisites

- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Node.js 20+

### First-Time Setup

1. **Configure API Keys** (Required)

   Edit `api/.env` and add at least one provider API key:

   ```bash
   # Get your API keys from:
   # - Replicate: https://replicate.com/account/api-tokens
   # - FAL: https://fal.ai/dashboard/keys
   # - OpenAI: https://platform.openai.com/api-keys
   # - Google: https://makersuite.google.com/app/apikey

   REPLICATE_API_KEY=r8_...
   FAL_KEY=...
   OPENAI_API_KEY=sk-...
   GOOGLE_API_KEY=...
   ```

2. **Start the application**

   ```bash
   npx @weirdfingers/baseboards up
   ```

3. **Access the app**

   Open http://localhost:3300 in your browser

## Commands

```bash
# Start the application
npx @weirdfingers/baseboards up

# Start in detached mode (background)
npx @weirdfingers/baseboards up --detached

# Stop the application
npx @weirdfingers/baseboards down

# View logs
npx @weirdfingers/baseboards logs

# View specific service logs
npx @weirdfingers/baseboards logs api

# Check status
npx @weirdfingers/baseboards status

# Update to latest version
npx @weirdfingers/baseboards update

# Clean up (removes volumes and containers)
npx @weirdfingers/baseboards clean --hard
```

## Configuration

### Generators

Edit `api/config/generators.yaml` to:

- Enable/disable specific image generation providers
- Add custom Replicate models
- Configure provider-specific settings

### Storage

Edit `api/config/storage_config.yaml` to:

- Switch from local storage to S3/GCS/Cloudflare R2
- Configure CDN integration
- Set up routing rules for different file types

Generated media is stored in `data/storage/` by default.

## Development

### Hot Reload

The default development mode includes hot reload for both frontend and backend:

- Frontend: Next.js Fast Refresh
- Backend: uvicorn --reload

Changes to source code are reflected immediately.

### Custom Code

You can customize any part of the application:

- Frontend: `web/src/`
- Backend: `api/src/`

**Note:** When you run `update`, custom code changes will be overwritten.
Use git to track your modifications.

## Documentation

- Full documentation: https://baseboards.dev/docs
- Adding providers: https://baseboards.dev/docs/generators
- Storage configuration: https://baseboards.dev/docs/storage
- Auth setup: https://baseboards.dev/docs/auth

## Support

- GitHub Issues: https://github.com/weirdfingers/boards/issues
- Documentation: https://baseboards.dev
