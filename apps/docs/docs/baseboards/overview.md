---
sidebar_position: 1
---

# Baseboards Overview

**Baseboards** is a production-ready reference implementation of the Boards toolkit, deployable with a single command via the `@weirdfingers/baseboards` CLI.

## What is Baseboards?

Baseboards serves two purposes:

1. **Turnkey Solution** - Deploy a fully-functional Boards instance immediately for personal or production use
2. **Reference Implementation** - Demonstrates best practices for building applications with the Boards toolkit

Unlike cloning the repository for development, Baseboards provides a pre-configured, containerized deployment that "just works" out of the box.

## Quick Start

```bash
# Install and start Baseboards
npx @weirdfingers/baseboards up my-boards-app

# Access at http://localhost:3300
```

See the [Installation Guide](../installation/installing-baseboards) for detailed setup instructions.

## Architecture

Baseboards uses Docker Compose to orchestrate several services:

```
my-boards-app/
├── web/                      # Next.js frontend (from apps/baseboards)
├── api/                      # FastAPI backend (from packages/backend)
├── data/storage/             # Generated media (local storage)
├── docker/                   # Docker Compose configuration
├── compose.yaml              # Production configuration
├── compose.dev.yaml          # Development overrides
└── README.md
```

### Services

- **web** - Next.js frontend application
  - Port: 3300 (default)
  - Built from `apps/baseboards` in the monorepo
  - Responsive UI with Tailwind CSS and Radix UI components

- **api** - FastAPI backend with GraphQL
  - Port: 8088 (default)
  - Built from `packages/backend` in the monorepo
  - Handles job processing, storage, and database operations

- **db** - PostgreSQL 15 database
  - Port: 5432 (internal)
  - Persistent storage for boards, artifacts, and user data

- **redis** - Redis 7 cache and job queue
  - Port: 6379 (internal)
  - Job queue management and caching

- **worker** - Background job processor
  - Executes AI generation jobs
  - Processes uploads and storage operations

## Configuration

### Environment Variables

API keys and configuration are stored in `api/.env`:

```bash
# Generator API keys (JSON format)
BOARDS_GENERATOR_API_KEYS={"REPLICATE_API_KEY":"r8_...","OPENAI_API_KEY":"sk-..."}

# Database
DATABASE_URL=postgresql://boards:boards@db:5432/boards

# Redis
REDIS_URL=redis://redis:6379/0

# Storage (default: local)
STORAGE_PROVIDER=local
```

During initial setup, the CLI prompts for API keys. You can also edit `api/.env` directly.

### Generator Configuration

Edit `api/config/generators.yaml` to customize available generators:

```yaml
generators:
  - name: flux-schnell
    provider: replicate
    type: text-to-image
    model: black-forest-labs/flux-schnell

  - name: gpt-4o
    provider: openai
    type: text-to-text
    model: gpt-4o
```

See the [Generators documentation](../generators/overview) for more details.

### Storage Configuration

Edit `api/config/storage_config.yaml` to configure storage backends:

```yaml
# Local storage (default)
type: local
local:
  base_path: /app/data/storage

# Or use cloud storage
# type: s3
# s3:
#   bucket: my-boards-bucket
#   region: us-east-1
```

Supported storage backends:
- **Local** - File system storage
- **S3** - Amazon S3
- **GCS** - Google Cloud Storage
- **Supabase** - Supabase Storage

See the [Storage documentation](../backend/storage) for configuration details.

## CLI Commands

### `baseboards up [directory]`

Start Baseboards. Creates project from templates if directory doesn't exist.

```bash
baseboards up                    # Current directory (detached)
baseboards up my-app             # New directory (detached)
baseboards up --prod             # Production mode
baseboards up --attach           # Attach to logs (foreground)
baseboards up --ports web=3300   # Custom ports
```

### `baseboards down [directory]`

Stop Baseboards.

```bash
baseboards down              # Stop services
baseboards down --volumes    # Also remove volumes (deletes data)
```

### `baseboards logs [directory] [services...]`

View service logs.

```bash
baseboards logs              # All services
baseboards logs api web      # Specific services
baseboards logs -f           # Follow logs
baseboards logs --since 1h   # Last hour
```

### `baseboards status [directory]`

Show service status.

```bash
baseboards status
```

### `baseboards update [directory]`

Update to the latest version (preserves configuration).

```bash
baseboards update
```

### `baseboards clean [directory]`

Clean up Docker resources.

```bash
baseboards clean             # Remove containers and volumes
baseboards clean --hard      # Also remove images
```

### `baseboards doctor [directory]`

Run diagnostics and show system information.

```bash
baseboards doctor
```

## Getting API Keys

Baseboards requires API keys from AI providers to generate content:

- **Replicate**: https://replicate.com/account/api-tokens
- **OpenAI**: https://platform.openai.com/api-keys
- **FAL**: https://fal.ai/dashboard/keys
- **Google AI**: https://makersuite.google.com/app/apikey

Keys are stored in `api/.env` as a JSON object:

```bash
BOARDS_GENERATOR_API_KEYS={"REPLICATE_API_KEY":"r8_...","OPENAI_API_KEY":"sk-..."}
```

## Production Deployment

### Using Docker Compose

```bash
# Production mode
baseboards up --prod

# Custom ports
baseboards up --prod --ports web=80,api=8080
```

### Environment Setup

For production deployments:

1. **Use strong database credentials** - Edit `docker/compose.yaml`
2. **Configure external storage** - Use S3/GCS instead of local storage
3. **Set up authentication** - See [Auth documentation](../auth/overview)
4. **Enable HTTPS** - Use a reverse proxy (nginx, Caddy)
5. **Configure monitoring** - See [Monitoring documentation](../deployment/monitoring)

### Scaling

To run multiple workers for higher throughput:

```bash
# Edit docker/compose.yaml
docker compose up --scale worker=3
```

## Customization

Baseboards is designed to be customized:

1. **Clone the generated directory** to version control
2. **Modify configuration files** (`generators.yaml`, `storage_config.yaml`, etc.)
3. **Update environment variables** in `api/.env` and `web/.env`
4. **Edit Docker Compose** files for custom networking, volumes, or services
5. **Extend the codebase** by forking the Boards repository

For deeper customization, consider:
- [Building a custom application](../installation/custom-application) using the toolkit packages
- [Contributing to Boards](../guides/contributing) to add features upstream

## Differences from Repository Clone

| Aspect | Baseboards CLI | Repository Clone |
|--------|---------------|------------------|
| **Purpose** | Deploy and use Boards | Develop and contribute |
| **Setup time** | ~5 minutes | ~10-15 minutes |
| **Prerequisites** | Docker, Node.js 20+ | Docker, Node.js 18+, Python 3.12+, pnpm |
| **Updates** | `baseboards update` | `git pull` + rebuild |
| **Customization** | Configuration files | Full source code access |
| **Use case** | Production deployment | Development environment |

## Troubleshooting

### Port Conflicts

If default ports are in use:

```bash
# Use custom ports
baseboards up --ports web=3301,api=8089
```

### Service Won't Start

```bash
# Check logs
baseboards logs

# Check status
baseboards status

# Run diagnostics
baseboards doctor
```

### Database Connection Issues

```bash
# Restart services
baseboards down
baseboards up
```

### Worker Not Processing Jobs

```bash
# Check worker logs
baseboards logs worker

# Verify Redis connection
baseboards logs redis

# Restart worker
docker compose restart worker
```

## Next Steps

- 📖 **[Installation Guide](../installation/installing-baseboards)** - Complete setup instructions
- 🎨 **[Generators](../generators/overview)** - Configure AI generators
- 🔐 **[Authentication](../auth/overview)** - Set up user authentication
- 🚀 **[Deployment](../deployment/overview)** - Production deployment guide
- 🏗️ **[Backend SDK](../backend/getting-started)** - Extend the backend
- ⚛️ **[Frontend Hooks](../frontend/getting-started)** - Customize the frontend
