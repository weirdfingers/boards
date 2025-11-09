# @weirdfingers/baseboards

One-command launcher for the Boards image generation platform.

## Quick Start

```bash
# Create and start a new Baseboards installation
npx @weirdfingers/baseboards up my-boards-app

# You'll be prompted to enter API keys during setup
# (or you can add them later by editing api/.env)

# Access the app
open http://localhost:3300
```

## Commands

### `up [directory]`

Scaffold and start Baseboards. If the directory doesn't exist, creates a new project from templates.

```bash
baseboards up                    # Current directory
baseboards up my-app             # New directory
baseboards up --prod             # Production mode
baseboards up --detached         # Background mode
baseboards up --ports web=3300   # Custom ports
```

### `down [directory]`

Stop Baseboards.

```bash
baseboards down              # Stop services
baseboards down --volumes    # Also remove volumes (deletes data)
```

### `logs [directory] [services...]`

View service logs.

```bash
baseboards logs              # All services
baseboards logs api web      # Specific services
baseboards logs -f           # Follow logs
baseboards logs --since 1h   # Last hour
```

### `status [directory]`

Show service status.

```bash
baseboards status
```

### `clean [directory]`

Clean up Docker resources.

```bash
baseboards clean             # Remove containers and volumes
baseboards clean --hard      # Also remove images
```

### `update [directory]`

Update to the latest version (preserves configuration).

```bash
baseboards update
```

### `doctor [directory]`

Run diagnostics and show system information.

```bash
baseboards doctor
```

## Requirements

- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Node.js 20+

## What Gets Scaffolded

```
my-app/
├─ web/                       # Next.js frontend
├─ api/                       # FastAPI backend
├─ data/storage/              # Generated media (local storage)
├─ docker/                    # Docker Compose configuration
├─ compose.yaml
├─ compose.dev.yaml
└─ README.md
```

## Configuration

### Provider API Keys (Required)

During initial setup, you'll be prompted to enter API keys. You can also edit `api/.env` directly:

```bash
# Keys are stored as JSON in a single environment variable
BOARDS_GENERATOR_API_KEYS={"REPLICATE_API_KEY":"r8_...","OPENAI_API_KEY":"sk-..."}
```

Get keys from:

- **Replicate**: https://replicate.com/account/api-tokens
- **OpenAI**: https://platform.openai.com/api-keys
- **FAL**: https://fal.ai/dashboard/keys
- **Google**: https://makersuite.google.com/app/apikey

### Generators

Edit `api/config/generators.yaml` to customize providers and models.

### Storage

Edit `api/config/storage_config.yaml` to configure storage (local/S3/GCS).

## Development

This package is part of the Boards monorepo.

### Building

```bash
pnpm build
```

This will:

1. Run `prepare-templates.js` to copy templates from monorepo
2. Build TypeScript with tsup
3. Create `dist/` and `templates/` directories

### Testing Locally

```bash
# 1. Build the package
pnpm build

# 2. Run the CLI directly
node dist/index.js up test-project

# 3. When done testing, clean up
cd test-project
docker compose down -v
cd ..
rm -rf test-project
```

**Note:** The `-v` flag removes volumes (including database data). Use `docker compose down` without `-v` if you want to preserve data between tests.

### Release

All packages use unified versioning. To release:

```bash
# Bump version across all packages
pnpm version 1.2.0 -r

# Build (templates get auto-copied)
pnpm build

# Publish
pnpm publish
```

## Architecture

The CLI bundles templates from the monorepo:

- `apps/baseboards` → `templates/web/`
- `packages/backend` → `templates/api/`

Templates are copied during build time via `scripts/prepare-templates.js`.

When users run `baseboards up`, templates are copied to their machine and Docker Compose orchestrates the services.

## Community & Social

Join the Weirdfingers community:

- **TikTok**: [https://www.tiktok.com/@weirdfingers](https://www.tiktok.com/@weirdfingers)
- **X (Twitter)**: [https://x.com/_Weirdfingers_](https://x.com/_Weirdfingers_)
- **YouTube**: [https://www.youtube.com/@Weirdfingers](https://www.youtube.com/@Weirdfingers)
- **Discord**: [https://discord.gg/rvVuHyuPEx](https://discord.gg/rvVuHyuPEx)
- **Instagram**: [https://www.instagram.com/_weirdfingers_/](https://www.instagram.com/_weirdfingers_/)

## License

MIT
