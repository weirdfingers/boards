# @weirdfingers/baseboards

One-command launcher for Boards, an AI-powered creative toolkit for generating, storing, and sharing images, video, audio, and text.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands Reference](#commands-reference)
- [Template System](#template-system)
- [Development Modes](#development-modes)
- [Common Workflows](#common-workflows)
- [Configuration](#configuration)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)
- [Community & Social](#community--social)

## Overview

Baseboards CLI provides a streamlined way to scaffold, deploy, and manage Boards applications. With a single command, you can have a full-stack AI creative platform running locally with Docker.

## Key Features

- **Multiple template options** - Choose from feature-rich or minimal starter templates
- **Docker-based backend** - Zero-configuration PostgreSQL, Redis, and API server
- **Local development mode** - Run frontend locally with `--app-dev` for fast iteration
- **Template caching** - Downloaded templates are cached for offline use
- **Interactive setup** - Guided prompts for API keys and template selection
- **Health monitoring** - Built-in diagnostics with the `doctor` command

## Installation

No installation required! Use npx to run Baseboards directly:

```bash
npx @weirdfingers/baseboards@latest up my-project
```

### Prerequisites

**Required:**
- Docker Desktop (macOS/Windows) or Docker Engine (Linux)

**Optional (for `--app-dev` mode only):**
- Node.js 20+
- Package manager (npm, pnpm, yarn, or bun)

## Quick Start

```bash
# Start with full-featured template (recommended)
npx @weirdfingers/baseboards up my-app --template baseboards

# Minimal starter for custom development
npx @weirdfingers/baseboards up my-app --template basic

# Local frontend development with native dev server
npx @weirdfingers/baseboards up my-app --template basic --app-dev

# Interactive template selection (no flag)
npx @weirdfingers/baseboards up my-app
```

After starting, access the app at [http://localhost:3300](http://localhost:3300)

## Commands Reference

### `up [directory]`

Scaffold and start Baseboards. If the directory doesn't exist, creates a new project from the selected template. Runs in detached mode (background) by default.

```bash
baseboards up [directory] [options]
```

**Options:**

| Flag | Description | Example |
|------|-------------|---------|
| `--template <name>` | Select template (baseboards, basic) | `--template basic` |
| `--app-dev` | Run frontend locally instead of in Docker | `--app-dev` |
| `--attach` | Attach to logs (runs in foreground) | `--attach` |
| `--ports <string>` | Custom port mappings | `--ports web=3300 api=8800` |
| `--fresh` | Delete existing volumes before starting | `--fresh` |
| `--dev-packages` | Use unpublished local packages (requires `--app-dev` and monorepo) | `--dev-packages` |

**Examples:**

```bash
# Create in current directory with default template
baseboards up

# Create in new directory with explicit template
baseboards up my-app --template baseboards

# Local frontend development
baseboards up my-app --app-dev

# Custom ports
baseboards up my-app --ports web=3000 api=8000

# Fresh start (clears database and volumes)
baseboards up my-app --fresh

# Attach to logs to see output in foreground
baseboards up my-app --attach
```

**Note:** The `--fresh` flag removes existing Docker volumes before starting, which is useful if you encounter database password mismatch errors or want a clean slate.

### `down [directory]`

Stop Baseboards services.

```bash
baseboards down [directory] [options]
```

**Options:**

| Flag | Description |
|------|-------------|
| `--volumes` | Also remove volumes (deletes all data) |

**Examples:**

```bash
# Stop services (preserves data)
baseboards down

# Stop and remove all data
baseboards down --volumes
```

### `logs [directory] [services...]`

View service logs. Supports filtering by specific services and following live output.

```bash
baseboards logs [directory] [services...] [options]
```

**Services:** `web`, `api`, `db`, `cache`

**Options:**

| Flag | Description | Example |
|------|-------------|---------|
| `-f, --follow` | Follow log output (live tail) | `-f` |
| `--since <time>` | Show logs since timestamp | `--since 1h`, `--since 30m` |
| `--tail <lines>` | Number of lines to show from end | `--tail 50` |

**Examples:**

```bash
# View all service logs
baseboards logs

# Follow logs in real-time
baseboards logs -f

# View only API and database logs
baseboards logs api db

# Last hour of logs
baseboards logs --since 1h

# Last 50 lines, following live
baseboards logs -f --tail 50
```

### `status [directory]`

Show the status of all services (running, stopped, health).

```bash
baseboards status [directory]
```

**Example output:**

```
Service Status:
  web    running  (healthy)
  api    running  (healthy)
  db     running  (healthy)
  cache  running  (healthy)
```

### `clean [directory]`

Clean up Docker resources associated with the project.

```bash
baseboards clean [directory] [options]
```

**Options:**

| Flag | Description |
|------|-------------|
| `--hard` | Also remove Docker images (WARNING: requires re-download) |

**Examples:**

```bash
# Remove containers and volumes
baseboards clean

# Remove everything including images (requires re-download)
baseboards clean --hard
```

**Warning:** The `--hard` flag will delete Docker images, requiring them to be re-downloaded on next `up`. This can take significant time depending on your internet connection.

### `templates`

List available templates with details about size, features, and frameworks.

```bash
baseboards templates [options]
```

**Options:**

| Flag | Description |
|------|-------------|
| `--refresh` | Clear cache and re-fetch template list |
| `--version <version>` | Show templates for specific CLI version |

**Examples:**

```bash
# List available templates
baseboards templates

# Refresh cache and fetch latest
baseboards templates --refresh

# Show templates for specific version
baseboards templates --version 0.8.0
```

**Example output:**

```
📦 Available templates for v0.8.0:

baseboards (recommended)
  Full-featured Boards application with UI
  Frameworks: Next.js, React, TailwindCSS
  Features: Authentication, Boards UI, Image Generation
  Size: 12.5 MB

basic
  Minimal starter for custom apps
  Frameworks: Next.js, React
  Features: GraphQL Client, Hooks
  Size: 45.2 KB
```

### `upgrade [directory]`

Upgrade Baseboards installation to a newer version. This updates templates and Docker Compose configurations while preserving your data and settings.

```bash
baseboards upgrade [directory] [options]
```

**Options:**

| Flag | Description |
|------|-------------|
| `--version <version>` | Upgrade to specific version (default: latest) |
| `--dry-run` | Preview upgrade without making changes |
| `--force` | Skip confirmation prompts and compatibility warnings |

**Examples:**

```bash
# Upgrade to latest version
baseboards upgrade

# Upgrade to specific version
baseboards upgrade --version 0.8.0

# Preview what would change
baseboards upgrade --dry-run

# Preview upgrade to specific version
baseboards upgrade --dry-run --version 0.8.0
```

### `doctor [directory]`

Run diagnostics and show system information. Useful for troubleshooting issues.

```bash
baseboards doctor [directory]
```

**Checks:**

- Docker installation and version
- Docker Compose availability
- Node.js version (for `--app-dev` mode)
- Service health status
- Port availability
- Configuration validity

**Example output:**

```
🏥 Baseboards Doctor

System Information:
  Platform: darwin (macOS)
  Docker: 24.0.2 ✓
  Docker Compose: 2.18.1 ✓
  Node.js: 20.5.0 ✓

Project Status:
  Directory: /Users/user/my-app
  Scaffolded: Yes
  Mode: Docker (default)
  Services:
    ✓ web (healthy)
    ✓ api (healthy)
    ✓ db (healthy)
    ✓ cache (healthy)

Configuration:
  Ports: web=3300 api=8800 db=5432 redis=6379
  Template: baseboards
  Version: 0.8.0
```

## Template System

Templates are pre-configured frontend applications that work with the Boards backend. They are downloaded on-demand from GitHub Releases and cached locally for offline use.

### Available Templates

| Template | Size | Description | Best For |
|----------|------|-------------|----------|
| **baseboards** | ~12 MB | Full-featured application with authentication, boards UI, and image generation | Quick start, demos, production use |
| **basic** | ~45 KB | Minimal Next.js starter with GraphQL client and hooks | Custom apps, learning, minimal footprint |

### Template Selection

**Interactive (recommended):**

```bash
baseboards up my-app
# You'll be prompted to select a template
```

**Explicit flag:**

```bash
baseboards up my-app --template basic
```

### Template Caching

Templates are automatically cached in `~/.cache/baseboards/templates/` after first download. This enables:

- **Offline usage** - Work without internet after initial download
- **Faster setup** - Subsequent projects use cached templates
- **Version pinning** - Each CLI version caches its compatible templates

**Clear cache:**

```bash
baseboards templates --refresh
```

### How to Choose

**Choose `baseboards` if you want:**
- A complete, production-ready application
- Built-in authentication and user management
- Full boards UI with image generation
- Minimal configuration

**Choose `basic` if you want:**
- A minimal starting point for custom apps
- Full control over UI/UX design
- Smaller download size
- To learn how Boards works

## Development Modes

Baseboards supports two development modes optimized for different workflows.

### Docker Mode (Default)

All services run in Docker containers, including the frontend.

```bash
baseboards up my-app
```

**Characteristics:**
- Frontend runs in Docker with hot reload
- All services orchestrated via Docker Compose
- No Node.js required on host machine
- Best for: Quick testing, demos, production-like environments

**How it works:**
- Frontend dev server runs inside Docker container
- Changes to `web/` directory trigger hot reload
- Access at http://localhost:3300

### App-Dev Mode

Backend runs in Docker, frontend runs locally on your machine.

```bash
baseboards up my-app --app-dev
```

**Characteristics:**
- Backend services (API, DB, Redis) run in Docker
- Frontend runs as native dev server on host
- Native package manager integration (npm, pnpm, yarn, bun)
- Best for: Active frontend development, faster iteration

**How it works:**
1. Backend services start in Docker
2. CLI installs frontend dependencies using your preferred package manager
3. Frontend dev server starts locally
4. Hot reload works natively with your editor/IDE

**Prerequisites:**
- Node.js 20+
- Package manager (you'll be prompted to select one)

**Switching between modes:**

You can switch between modes by running `down` then `up` with different flags:

```bash
# Switch to app-dev mode
baseboards down
baseboards up --app-dev

# Switch back to Docker mode
baseboards down
baseboards up
```

## Common Workflows

### Starting a New Project

```bash
# Create and start new project
npx @weirdfingers/baseboards up my-boards-app

# Follow prompts for:
# 1. Template selection (baseboards or basic)
# 2. API key entry (Replicate, OpenAI, etc.)

# Access the application
open http://localhost:3300
```

### Stopping and Starting

```bash
# Stop services (preserves data)
baseboards down

# Start again (no re-scaffolding needed)
baseboards up

# Stop and remove all data
baseboards down --volumes
```

### Viewing Logs

```bash
# View all logs
baseboards logs

# Follow logs in real-time
baseboards logs -f

# View specific service
baseboards logs api

# Last 2 hours of API logs
baseboards logs api --since 2h
```

### Cleaning Up

```bash
# Remove project completely
baseboards down --volumes
cd ..
rm -rf my-boards-app

# Clean Docker resources (in project directory)
baseboards clean

# Full cleanup including images
baseboards clean --hard
```

### Using Custom Ports

```bash
# Frontend on 3000, API on 8000
baseboards up --ports web=3000 api=8000

# Just change frontend port
baseboards up --ports web=4000
```

### Local Development Workflow

For active frontend development:

```bash
# 1. Start in app-dev mode
baseboards up my-app --app-dev

# 2. Backend runs in Docker (API, DB, Redis)
# 3. Frontend runs locally (native dev server)
# 4. Make changes to web/ directory
# 5. Hot reload works natively

# When done, stop services
baseboards down
```

For backend development, edit files in `api/` - changes will trigger reload in Docker.

## Configuration

### Environment Variables

API keys and configuration are stored in `api/.env`:

```bash
# Provider API keys (JSON format)
BOARDS_GENERATOR_API_KEYS={"REPLICATE_API_KEY":"r8_...","OPENAI_API_KEY":"sk-..."}

# Database (auto-configured)
POSTGRES_USER=boards
POSTGRES_PASSWORD=<generated>
POSTGRES_DB=boards

# Redis (auto-configured)
REDIS_PASSWORD=<generated>

# API secrets (auto-configured)
BOARDS_SECRET_KEY=<generated>
```

**Get API keys:**

- **Replicate**: https://replicate.com/account/api-tokens
- **OpenAI**: https://platform.openai.com/api-keys
- **FAL**: https://fal.ai/dashboard/keys
- **Google**: https://makersuite.google.com/app/apikey

### Configuration Files

```
my-app/
├─ api/.env                      # Environment variables
├─ api/config/generators.yaml    # Generator providers and models
├─ api/config/storage_config.yaml # Storage configuration (local/S3/GCS)
├─ compose.yaml                  # Docker Compose orchestration
└─ docker/                       # Service-specific Docker configs
```

### Port Configuration

**Default ports:**

| Service | Port | Description |
|---------|------|-------------|
| web | 3300 | Frontend application |
| api | 8800 | Backend GraphQL API |
| db | 5432 | PostgreSQL (internal only) |
| cache | 6379 | Redis (internal only) |

**Custom ports:**

```bash
baseboards up --ports web=3000 api=8000
```

**Port conflicts:**

If ports are already in use, you'll see an error. Use `--ports` to specify different ports:

```bash
# Error: port 3300 already in use
baseboards up --ports web=3301
```

### Backend Version Pinning

The backend Docker image version is automatically matched to your CLI version. To use a different backend version:

1. Edit `compose.yaml` in your project
2. Change the image tag for the `api` service:

```yaml
services:
  api:
    image: ghcr.io/weirdfingers/boards-backend:0.8.0  # Pin to specific version
```

## Advanced Usage

### Offline Usage with Cached Templates

After downloading a template once, you can work offline:

```bash
# First time (requires internet)
baseboards up project1 --template basic

# Later (works offline if cached)
baseboards up project2 --template basic
```

Cache location: `~/.cache/baseboards/templates/`

### CI/CD Usage (Non-Interactive)

For automated deployments, specify template explicitly to avoid prompts:

```bash
# Non-interactive mode (no prompts)
baseboards up deployment --template baseboards

# Set API keys via environment
export BOARDS_GENERATOR_API_KEYS='{"REPLICATE_API_KEY":"r8_..."}'
```

### Custom Backend Versions

For testing or pinning specific backend versions:

```bash
# Start project
baseboards up my-app

# Edit compose.yaml
cd my-app
# Change image: ghcr.io/weirdfingers/boards-backend:latest
# to image: ghcr.io/weirdfingers/boards-backend:0.7.5

# Restart with specific version
baseboards down
baseboards up
```

### Developer Mode (Monorepo Contributors)

For Boards contributors testing unpublished package changes:

```bash
# From monorepo root
cd boards

# Build packages
pnpm build

# Create test project with local packages
pnpm cli up test-app --app-dev --dev-packages

# Changes to packages/frontend are reflected immediately
```

**Note:** `--dev-packages` requires:
- Running from Boards monorepo
- `--app-dev` mode enabled
- Monorepo packages built

### Template Caching Management

```bash
# View available templates and cache status
baseboards templates

# Refresh cache (re-download all templates)
baseboards templates --refresh

# View templates for different version
baseboards templates --version 0.7.0

# Manually clear cache
rm -rf ~/.cache/baseboards/templates
```

## Troubleshooting

### Common Issues

#### Port Conflicts

**Symptoms:** Error message "port 3300 already in use"

**Solutions:**

```bash
# Option 1: Stop conflicting service
# Find what's using the port
lsof -i :3300  # macOS/Linux
netstat -ano | findstr :3300  # Windows

# Option 2: Use different ports
baseboards up --ports web=3301 api=8801
```

#### Docker Not Running

**Symptoms:** "Cannot connect to the Docker daemon"

**Solutions:**

1. Start Docker Desktop (macOS/Windows)
2. Start Docker Engine (Linux): `sudo systemctl start docker`
3. Verify: `docker ps`

Run diagnostics:

```bash
baseboards doctor
```

#### Template Download Failures

**Symptoms:** "Failed to download template" or "Network error"

**Solutions:**

```bash
# Check internet connection
ping github.com

# Clear cache and retry
baseboards templates --refresh

# Try different template
baseboards up my-app --template basic

# Check GitHub status
# https://www.githubstatus.com/
```

#### Permission Errors

**Symptoms:** "Permission denied" when creating directories

**Solutions:**

```bash
# Ensure you have write permissions
mkdir test-dir && rmdir test-dir

# Try different directory
baseboards up ~/Documents/my-app

# Linux: Check Docker group membership
groups  # Should include "docker"
sudo usermod -aG docker $USER  # Add to docker group
# Log out and back in
```

#### Database Password Mismatch

**Symptoms:** "password authentication failed for user boards"

**Solution:**

```bash
# Clean start (removes volumes)
baseboards down --volumes
baseboards up --fresh
```

#### Node.js Version Issues (App-Dev Mode)

**Symptoms:** "Node.js 20+ required for --app-dev mode"

**Solutions:**

```bash
# Check version
node --version

# Upgrade Node.js
# Using nvm (recommended)
nvm install 20
nvm use 20

# Or download from https://nodejs.org/
```

#### Out of Disk Space

**Symptoms:** "no space left on device"

**Solutions:**

```bash
# Clean up Docker resources
docker system prune -a --volumes

# Remove old Baseboards projects
baseboards clean --hard
cd old-project && baseboards down --volumes
```

### Getting Help

**Run diagnostics:**

```bash
baseboards doctor
```

**View logs:**

```bash
baseboards logs -f
```

**Report issues:**

- GitHub Issues: https://github.com/weirdfingers/boards/issues
- Include output from `baseboards doctor`
- Include relevant logs from `baseboards logs`

**Documentation:**

- Full docs: https://baseboards.dev/docs
- API reference: https://baseboards.dev/docs/api
- Guides: https://baseboards.dev/docs/guides

**Community:**

- Discord: https://discord.gg/rvVuHyuPEx
- GitHub Discussions: https://github.com/weirdfingers/boards/discussions

## Community & Social

Join the Weirdfingers community:

- **Discord**: [https://discord.gg/rvVuHyuPEx](https://discord.gg/rvVuHyuPEx)
- **GitHub**: [https://github.com/weirdfingers/boards](https://github.com/weirdfingers/boards)
- **TikTok**: [https://www.tiktok.com/@weirdfingers](https://www.tiktok.com/@weirdfingers)
- **X (Twitter)**: [https://x.com/_Weirdfingers_](https://x.com/_Weirdfingers_)
- **YouTube**: [https://www.youtube.com/@Weirdfingers](https://www.youtube.com/@Weirdfingers)
- **Instagram**: [https://www.instagram.com/_weirdfingers_/](https://www.instagram.com/_weirdfingers_/)

## License

MIT

---

## For Contributors

This package is part of the Boards monorepo.

### Building

```bash
# Install dependencies
pnpm install

# Build package
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

# Run CLI directly
node dist/index.js up test-project

# Clean up
cd test-project
docker compose down -v
cd ..
rm -rf test-project
```

### Release

All packages use unified versioning:

```bash
# Bump version across all packages
pnpm version 1.2.0 -r

# Build
pnpm build

# Publish
pnpm publish
```

### Architecture

The CLI bundles templates from the monorepo:

- `apps/baseboards` → `templates/web/`
- `packages/backend` → `templates/api/`

Templates are copied during build time via `scripts/prepare-templates.js`.

When users run `baseboards up`, templates are copied to their machine and Docker Compose orchestrates the services.
