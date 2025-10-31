# @weirdfingers/baseboards

One-command launcher for the Boards image generation platform.

## Quick Start

```bash
# Create and start a new Baseboards installation
npx @weirdfingers/baseboards up my-boards-app

# Configure API keys
cd my-boards-app
edit packages/api/.env

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
├─ packages/
│  ├─ web/                    # Next.js frontend
│  └─ api/                    # FastAPI backend
├─ data/storage/              # Generated media (local storage)
├─ docker/                    # Docker Compose configuration
├─ compose.yaml
├─ compose.dev.yaml
└─ README.md
```

## Configuration

### Provider API Keys (Required)

Edit `packages/api/.env` and add at least one provider key:

```bash
REPLICATE_API_KEY=r8_...       # https://replicate.com/account/api-tokens
FAL_KEY=...                    # https://fal.ai/dashboard/keys
OPENAI_API_KEY=sk-...          # https://platform.openai.com/api-keys
GOOGLE_API_KEY=...             # https://makersuite.google.com/app/apikey
```

### Generators

Edit `packages/api/config/generators.yaml` to customize providers and models.

### Storage

Edit `packages/api/config/storage_config.yaml` to configure storage (local/S3/GCS).

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
# Build the package
pnpm build

# Test the CLI
node dist/index.js up test-project

# Or link globally
pnpm link --global
baseboards up test-project
```

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

## License

MIT
