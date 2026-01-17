# CLI Launcher Revamp — Technical Design

**Goal:** Modernize the `@weirdfingers/baseboards` CLI with a streamlined developer experience, pre-built backend Docker images, and extensible frontend templates.

```bash
# Quick start with full-featured template (pre-built images, no hot-reload)
npx @weirdfingers/baseboards up my-app --template baseboards

# Minimal starter for custom apps (pre-built images, no hot-reload)
npx @weirdfingers/baseboards up my-app --template basic

# Frontend development mode: runs locally with hot-reload, backend in Docker
npx @weirdfingers/baseboards up my-app --template basic --app-dev
```

---

## Table of Contents

1. [Summary of Changes](#1-summary-of-changes)
2. [Architecture Overview](#2-architecture-overview)
   - Service Configuration
   - Extensibility Support
3. [CLI Interface](#3-cli-interface)
4. [Template System](#4-template-system)
5. [Docker Image Strategy](#5-docker-image-strategy)
6. [Development Modes](#6-development-modes)
7. [Release Process Changes](#7-release-process-changes)
8. [Implementation Plan](#8-implementation-plan)
9. [Migration Notes](#9-migration-notes)
10. [Upgrade Workflow](#10-upgrade-workflow)
11. [Future Extensions](#11-future-extensions)

---

## 1) Summary of Changes

### What's Changing

| Aspect | Before | After |
|--------|--------|-------|
| **Modes** | `--dev` (hot reload) vs `--prod` (prebuilt) | Single mode (pre-built images) |
| **Backend** | Built locally from source | Pre-built Docker image from registry |
| **Frontend Templates** | Only `baseboards` (full app) | Multiple: `baseboards`, `basic`, future frameworks |
| **Template Source** | Bundled in npm package | Downloaded from GitHub Releases |
| **Frontend Execution** | Always in Docker | Pre-built image (default) or local dev (`--app-dev`) |
| **Hot Reload** | Dev mode only | Only with `--app-dev` flag (frontend only) |

### What's Staying the Same

- CLI command structure (`up`, `down`, `logs`, `status`, `clean`, `doctor`)
- Port management and auto-discovery
- Environment variable generation
- API key prompting on first scaffold
- Health check and migration workflow
- Docker Compose orchestration

---

## 2) Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     @weirdfingers/baseboards CLI                        │
│                                                                         │
│  • Template selection & download (from GitHub Releases)                 │
│  • Environment configuration                                            │
│  • Docker Compose orchestration                                         │
│  • Port management & health checks                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────┐
              │         GitHub Releases Storage         │
              │                                         │
              │  • template-baseboards-v0.7.0.tar.gz    │
              │  • template-basic-v0.7.0.tar.gz         │
              │  • template-expo-v0.7.0.tar.gz (future) │
              └─────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────────┐      ┌───────────────────────┐
        │   Default Mode        │      │   --app-dev Mode      │
        │                       │      │                       │
        │  ┌─────────────────┐  │      │  ┌─────────────────┐  │
        │  │   web (Docker)  │  │      │  │  web (local)    │  │
        │  │  pre-built img  │  │      │  │  pnpm/npm dev   │  │
        │  └─────────────────┘  │      │  └─────────────────┘  │
        └───────────────────────┘      └───────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
        ┌─────────────────────────────────────────────────────────┐
        │              Docker Services (always)                    │
        │                                                         │
        │  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌───────────┐  │
        │  │   api    │  │  worker  │  │   db   │  │   cache   │  │
        │  │ (image)  │  │ (image)  │  │ pg:16  │  │  redis:7  │  │
        │  └──────────┘  └──────────┘  └────────┘  └───────────┘  │
        │                                                         │
        │  Image: ghcr.io/weirdfingers/boards-backend:0.7.0       │
        └─────────────────────────────────────────────────────────┘
```

### Service Configuration

| Service | Image Source | Mounts | Purpose |
|---------|--------------|--------|---------|
| **db** | `postgres:16` | `db-data` volume | PostgreSQL database |
| **cache** | `redis:7` | None | Job queue, caching |
| **api** | `ghcr.io/weirdfingers/boards-backend:X.Y.Z` | `./config`, `./data/storage`, `./extensions` | GraphQL API server |
| **worker** | `ghcr.io/weirdfingers/boards-backend:X.Y.Z` | `./config`, `./data/storage`, `./extensions` | Background job processor |
| **web** | Built locally (default) OR local dev server (`--app-dev`) | None | Frontend application |

**Volume Mount Details:**

- **`./config`** (read-only): Generator and storage configuration YAML files
- **`./data/storage`** (read-write): Generated media artifacts (images, videos, audio) - persisted across container restarts
- **`./extensions/generators`** (read-only): Custom generator implementations (Python modules)
- **`./extensions/plugins`** (read-only): Plugin implementations (Python modules) - see [PR #231](https://github.com/weirdfingers/boards/pull/231)

### Extensibility Support

Boards supports loading custom code modules from outside the core source tree:

**Custom Generators** - Implement generators not included in the core package:

```yaml
# config/generators.yaml
generators:
  # Core generator (built into image)
  - class: "boards.generators.implementations.fal.image.flux_pro.FalFluxProGenerator"
    enabled: true

  # Custom generator (loaded from ./extensions/generators/)
  - class: "custom_generators.my_generator.MyCustomGenerator"
    enabled: true

  # External package generator (via Python entry point)
  - entrypoint: "myorg.custom_whisper"
    enabled: true
```

**Custom Plugins** - Extend Boards functionality with custom plugins (PR #231):

```python
# extensions/plugins/my_plugin.py
from boards.plugins import BasePlugin

class MyCustomPlugin(BasePlugin):
    def initialize(self):
        # Plugin initialization logic
        pass
```

**Backend Loading Mechanism:**

1. `PYTHONPATH` environment variable includes `/app/extensions`
2. Backend discovers Python modules in `./extensions/generators/` and `./extensions/plugins/`
3. Generators configured via `generators.yaml` are imported and registered
4. Plugins are loaded via entry point discovery mechanism

**Storage Configuration:**

The `storage_config.yaml` must use Docker volume paths to ensure persistence:

```yaml
# config/storage_config.yaml
storage:
  default_provider: "local"
  providers:
    local:
      type: "local"
      config:
        base_path: "/app/data/storage"  # ← Docker volume mount
        public_url_base: "http://localhost:8800/api/storage"
```

**Documentation:**

- Custom generators: [https://boards-docs.weirdfingers.com/docs/generators/configuration](https://boards-docs.weirdfingers.com/docs/generators/configuration)
- Entry points: [https://boards-docs.weirdfingers.com/docs/generators/configuration#plugin-entry-point-contract](https://boards-docs.weirdfingers.com/docs/generators/configuration#plugin-entry-point-contract)

---

## 3) CLI Interface

### Updated Command Reference

```bash
# Main command - scaffold and start
baseboards up [directory] [options]

Options:
  --template <name>     Frontend template: "baseboards", "basic" (default: interactive)
  --app-dev             Run frontend locally instead of in Docker
  --backend-version <v> Backend image version (default: CLI version)
  --attach              Attach to logs after startup
  --ports <string>      Custom ports: "web=3300 api=8800"
  --fresh               Delete existing volumes before starting

# Upgrade existing installation
baseboards upgrade [directory] [options]
  --version <version>   Target version (default: latest)
  --dry-run             Show what would be upgraded without making changes
  --force               Skip compatibility checks (dangerous)

# List available templates
baseboards templates [options]
  --refresh             Re-fetch template list from remote

# Other commands (unchanged)
baseboards down [directory] [--volumes]
baseboards logs [directory] [services...] [-f] [--since] [--tail]
baseboards status [directory]
baseboards clean [directory] [--hard]
baseboards doctor [directory]
```

### Removed Flags

| Flag | Reason |
|------|--------|
| `--dev` | Removed - pre-built images are now default |
| `--prod` | Removed - pre-built images are now default |

### New Flags

| Flag | Purpose |
|------|---------|
| `--template <name>` | Select frontend template |
| `--app-dev` | Run frontend locally with native tooling |
| `--backend-version <v>` | Pin backend image to specific version |

### Interactive Flows

#### Template Selection (when `--template` not provided)

```
$ npx @weirdfingers/baseboards up my-app

? Select a frontend template:
❯ baseboards    Full-featured Boards application (recommended)
  basic         Minimal Next.js starter with @weirdfingers/boards

Downloading template... Done!
```

#### Package Manager Selection (when `--app-dev` is used)

```
$ npx @weirdfingers/baseboards up my-app --template basic --app-dev

? Select your package manager:
❯ pnpm
  npm
  yarn
  bun

Installing dependencies with pnpm... Done!

To start the frontend:
  cd my-app/web
  pnpm dev
```

---

## 4) Template System

### Template Registry

Templates are stored as tarballs attached to GitHub Releases:

```
Release: v0.7.0
Assets:
  - template-baseboards-v0.7.0.tar.gz   (12 MB)
  - template-basic-v0.7.0.tar.gz        (45 KB)
  - template-manifest.json              (1 KB)
```

#### Template Manifest (`template-manifest.json`)

```json
{
  "version": "0.7.0",
  "templates": [
    {
      "name": "baseboards",
      "description": "Full-featured Boards application (recommended)",
      "file": "template-baseboards-v0.7.0.tar.gz",
      "size": 12582912,
      "checksum": "sha256:abc123...",
      "frameworks": ["next.js"],
      "features": ["auth", "generators", "boards", "themes"]
    },
    {
      "name": "basic",
      "description": "Minimal Next.js starter with @weirdfingers/boards",
      "file": "template-basic-v0.7.0.tar.gz",
      "size": 46080,
      "checksum": "sha256:def456...",
      "frameworks": ["next.js"],
      "features": ["minimal"]
    }
  ]
}
```

### Template Download Flow

```typescript
async function downloadTemplate(
  templateName: string,
  version: string,
  targetDir: string
): Promise<void> {
  // 1. Check local cache first
  const cacheDir = path.join(os.homedir(), ".baseboards", "templates");
  const cachedPath = path.join(cacheDir, `template-${templateName}-v${version}.tar.gz`);

  if (await fs.pathExists(cachedPath)) {
    // Verify checksum and extract
    await extractTemplate(cachedPath, targetDir);
    return;
  }

  // 2. Fetch manifest from GitHub Release
  const manifest = await fetchManifest(version);
  const template = manifest.templates.find((t) => t.name === templateName);

  if (!template) {
    throw new Error(`Template "${templateName}" not found in version ${version}`);
  }

  // 3. Download tarball
  const downloadUrl = `https://github.com/weirdfingers/boards/releases/download/v${version}/${template.file}`;
  await downloadFile(downloadUrl, cachedPath);

  // 4. Verify checksum
  await verifyChecksum(cachedPath, template.checksum);

  // 5. Extract to target
  await extractTemplate(cachedPath, targetDir);
}
```

### Template Cache

```
~/.baseboards/
├── templates/
│   ├── template-baseboards-v0.7.0.tar.gz
│   ├── template-basic-v0.7.0.tar.gz
│   └── manifest-v0.7.0.json
└── config.json  (user preferences)
```

- Templates cached in `~/.baseboards/templates/`
- Cache is version-specific (different versions can coexist)
- `baseboards templates --refresh` clears cache and re-downloads

### Template Structure

#### `baseboards` Template (Full Application)

```
template-baseboards/
├── web/                          # Full Boards frontend
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages
│   │   ├── components/           # UI components
│   │   └── lib/                  # Utilities
│   ├── package.json              # @weirdfingers/boards dependency
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── .env.example
├── config/                       # Backend configuration
│   ├── generators.yaml
│   └── storage_config.yaml
├── extensions/                   # Custom code (volume-mounted)
│   ├── generators/               # Custom generator implementations
│   │   └── README.md             # Instructions for adding custom generators
│   └── plugins/                  # Plugin implementations
│       └── README.md             # Instructions for adding plugins
├── data/
│   └── storage/.gitkeep          # Generated media (volume-mounted)
├── docker/
│   └── .env.example
├── compose.yaml                  # Docker Compose (no web service)
├── compose.web.yaml              # Web service overlay (for non-app-dev)
├── Dockerfile.web                # Production build for web container
├── .gitignore
└── README.md
```

#### `basic` Template (Minimal Starter)

```
template-basic/
├── web/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx        # Root layout with BoardsProvider
│   │   │   ├── page.tsx          # Simple board list example
│   │   │   └── globals.css       # Tailwind imports
│   │   └── components/
│   │       └── ui/               # shadcn components (button, card)
│   ├── package.json              # @weirdfingers/boards + shadcn deps
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── components.json           # shadcn config
│   └── .env.example
├── config/
│   ├── generators.yaml
│   └── storage_config.yaml
├── extensions/                   # Custom code (volume-mounted)
│   ├── generators/               # Custom generator implementations
│   │   └── README.md             # Instructions for adding custom generators
│   └── plugins/                  # Plugin implementations
│       └── README.md             # Instructions for adding plugins
├── data/
│   └── storage/.gitkeep          # Generated media (volume-mounted)
├── docker/
│   └── .env.example
├── compose.yaml
├── compose.web.yaml
├── Dockerfile.web                # Production build for web container
├── .gitignore
└── README.md
```

#### Basic Template `page.tsx` Example

```tsx
// web/src/app/page.tsx
"use client";

import { useBoards, useCreateBoard } from "@weirdfingers/boards";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function Home() {
  const { boards, loading, error } = useBoards();
  const { createBoard, loading: creating } = useCreateBoard();

  if (loading) return <div className="p-8">Loading boards...</div>;
  if (error) return <div className="p-8 text-red-500">Error: {error.message}</div>;

  return (
    <main className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">My Boards</h1>
        <Button
          onClick={() => createBoard({ title: "New Board" })}
          disabled={creating}
        >
          Create Board
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {boards.map((board) => (
          <Card key={board.id}>
            <CardHeader>
              <CardTitle>{board.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                {board.generationsCount} generations
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}
```

### Template Preparation (Build-Time)

During the release process, templates are prepared and packaged:

```bash
# scripts/prepare-release-templates.sh

# 1. Prepare baseboards template (from apps/baseboards)
prepare_baseboards_template() {
  TEMPLATE_DIR="dist/templates/baseboards"
  mkdir -p "$TEMPLATE_DIR"

  # Copy web app (excluding build artifacts)
  rsync -av --exclude='.next' --exclude='node_modules' \
    apps/baseboards/ "$TEMPLATE_DIR/web/"

  # Transform workspace dependencies to published versions
  node scripts/transform-package-json.js "$TEMPLATE_DIR/web/package.json"

  # Copy shared template files
  cp -r packages/cli-launcher/template-sources/config "$TEMPLATE_DIR/"
  cp packages/cli-launcher/template-sources/compose.yaml "$TEMPLATE_DIR/"
  cp packages/cli-launcher/template-sources/compose.web.yaml "$TEMPLATE_DIR/"
  cp packages/cli-launcher/template-sources/Dockerfile.web "$TEMPLATE_DIR/"

  # Create tarball
  tar -czvf "dist/template-baseboards-v${VERSION}.tar.gz" -C dist/templates baseboards
}

# 2. Prepare basic template (from packages/cli-launcher/basic-template)
prepare_basic_template() {
  TEMPLATE_DIR="dist/templates/basic"
  mkdir -p "$TEMPLATE_DIR"

  # Copy basic template source
  cp -r packages/cli-launcher/basic-template/* "$TEMPLATE_DIR/"

  # Update version in package.json
  node scripts/set-package-version.js "$TEMPLATE_DIR/web/package.json" "$VERSION"

  # Create tarball
  tar -czvf "dist/template-basic-v${VERSION}.tar.gz" -C dist/templates basic
}

# 3. Generate manifest
generate_manifest() {
  node scripts/generate-template-manifest.js \
    --version "$VERSION" \
    --templates dist/template-*.tar.gz \
    --output dist/template-manifest.json
}
```

---

## 5) Docker Image Strategy

### Image Naming and Registry

| Registry | Image | Purpose |
|----------|-------|---------|
| **GHCR** (primary) | `ghcr.io/weirdfingers/boards-backend` | CLI default, GitHub integration |
| **Docker Hub** (mirror) | `weirdfingers/boards-backend` | Discoverability, no GitHub auth |

### Single Image, Multiple Roles

The `boards-backend` image runs both `api` and `worker` services:

```yaml
# compose.yaml
services:
  api:
    image: ghcr.io/weirdfingers/boards-backend:${BACKEND_VERSION:-0.7.0}
    command: ["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800"]
    # ...

  worker:
    image: ghcr.io/weirdfingers/boards-backend:${BACKEND_VERSION:-0.7.0}
    command: ["dramatiq-gevent", "boards.workers.actors:broker", "--processes", "1", "--threads", "50"]
    # ...
```

### Version Tags

| Tag | Purpose | Example |
|-----|---------|---------|
| `X.Y.Z` | Specific version (immutable) | `0.7.0`, `1.0.0` |
| `latest` | Most recent stable release | Points to `0.7.0` |
| `X.Y` | Latest patch in minor series | `0.7` points to `0.7.2` |

**Default behavior:** CLI uses the version matching its own version (lockstep).

```typescript
const DEFAULT_BACKEND_VERSION = pkg.version; // e.g., "0.7.0"
```

### External Configuration Mounts

The backend image expects configuration and extensibility directories to be mounted externally:

```yaml
services:
  api:
    image: ghcr.io/weirdfingers/boards-backend:${BACKEND_VERSION}
    volumes:
      - ./config/generators.yaml:/app/config/generators.yaml:ro
      - ./config/storage_config.yaml:/app/config/storage_config.yaml:ro
      - ./data/storage:/app/data/storage
      - ./extensions:/app/extensions:ro
    environment:
      BOARDS_GENERATORS_CONFIG_PATH: /app/config/generators.yaml
      BOARDS_STORAGE_CONFIG_PATH: /app/config/storage_config.yaml
      PYTHONPATH: /app:/app/extensions
```

**Volume purposes:**

- **`./config`**: YAML configuration files for generators and storage
- **`./data/storage`**: Persistent storage for generated media (images, videos, audio) - ensures artifacts survive container restarts
- **`./extensions`**: Custom Python modules (generators and plugins) loaded at runtime - enables extensibility without rebuilding the Docker image

### Dockerfile for Backend Image

```dockerfile
# packages/backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN useradd -m -u 1000 boards && chown -R boards:boards /app
USER boards

# Default command (overridden in compose)
CMD ["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800"]

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s \
  CMD curl -f http://localhost:8800/health || exit 1
```

### Multi-Architecture Build

```yaml
# .github/workflows/version-bump.yml (addition)
publish-docker:
  needs: bump-and-release
  runs-on: ubuntu-latest
  permissions:
    contents: read
    packages: write

  steps:
    - uses: actions/checkout@v4
      with:
        ref: "v${{ needs.bump-and-release.outputs.version }}"

    - name: Set up QEMU
      uses: docker/setup-qemu-action@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to GHCR
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_TOKEN }}

    - name: Extract version
      id: version
      run: echo "version=${{ needs.bump-and-release.outputs.version }}" >> $GITHUB_OUTPUT

    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: packages/backend
        file: packages/backend/Dockerfile
        platforms: linux/amd64,linux/arm64
        push: true
        tags: |
          ghcr.io/weirdfingers/boards-backend:${{ steps.version.outputs.version }}
          ghcr.io/weirdfingers/boards-backend:latest
          weirdfingers/boards-backend:${{ steps.version.outputs.version }}
          weirdfingers/boards-backend:latest
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

---

## 6) Development Modes

### Default Mode (Pre-built Images)

When `--app-dev` is NOT specified:

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose                         │
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌────────┐  ┌─────────────────┐  │
│  │   api   │  │ worker  │  │   db   │  │      web        │  │
│  │ (image) │  │ (image) │  │ pg:16  │  │  (built image)  │  │
│  └─────────┘  └─────────┘  └────────┘  └─────────────────┘  │
│       │            │            │              │            │
│       └────────────┴────────────┴──────────────┘            │
│                         internal network                    │
└─────────────────────────────────────────────────────────────┘
        │                                        │
        ▼                                        ▼
   localhost:8800                          localhost:3300
      (API)                                    (Web)
```

**Docker Compose configuration:**

```yaml
# compose.yaml (base - always loaded)
name: ${PROJECT_NAME:-baseboards}

services:
  db:
    image: postgres:16
    env_file: docker/.env
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]
      interval: 5s
      timeout: 5s
      retries: 20
    networks:
      - internal

  cache:
    image: redis:7
    command: ["redis-server", "--appendonly", "yes"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20
    networks:
      - internal

  api:
    image: ghcr.io/weirdfingers/boards-backend:${BACKEND_VERSION:-latest}
    command: ["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800"]
    env_file:
      - docker/.env
      - api/.env
    volumes:
      - ./config:/app/config:ro
      - ./data/storage:/app/data/storage
      - ./extensions:/app/extensions:ro
    environment:
      - PYTHONPATH=/app:/app/extensions
      - BOARDS_GENERATORS_CONFIG_PATH=/app/config/generators.yaml
      - BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    ports:
      - "${API_PORT:-8800}:8800"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8800/health"]
      interval: 5s
      timeout: 3s
      retries: 50
    networks:
      - internal

  worker:
    image: ghcr.io/weirdfingers/boards-backend:${BACKEND_VERSION:-latest}
    command: ["dramatiq-gevent", "boards.workers.actors:broker", "--processes", "1", "--threads", "50"]
    env_file:
      - docker/.env
      - api/.env
    volumes:
      - ./config:/app/config:ro
      - ./data/storage:/app/data/storage
      - ./extensions:/app/extensions:ro
    environment:
      - PYTHONPATH=/app:/app/extensions
      - BOARDS_GENERATORS_CONFIG_PATH=/app/config/generators.yaml
      - BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "pgrep", "-f", "dramatiq"]
      interval: 10s
      timeout: 5s
      retries: 30
    networks:
      - internal

networks:
  internal:

volumes:
  db-data:
```

```yaml
# compose.web.yaml (overlay - loaded when NOT --app-dev)
services:
  web:
    build:
      context: ./web
      dockerfile: ../Dockerfile.web
    env_file: web/.env
    environment:
      - INTERNAL_API_URL=http://api:8800
    depends_on:
      api:
        condition: service_healthy
    ports:
      - "${WEB_PORT:-3300}:3000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/"]
      interval: 5s
      timeout: 3s
      retries: 50
    networks:
      - internal
```

**Dockerfile.web (Production Build):**

```dockerfile
# Dockerfile.web
FROM node:20-slim AS base

# Install pnpm
RUN corepack enable && corepack prepare pnpm@9 --activate

FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000

CMD ["node", "server.js"]
```

### App-Dev Mode (Frontend Local)

When `--app-dev` IS specified:

```
┌─────────────────────────────────────────┐
│            Docker Compose               │
│                                         │
│  ┌─────────┐  ┌─────────┐  ┌────────┐   │
│  │   api   │  │ worker  │  │   db   │   │
│  │ (image) │  │ (image) │  │ pg:16  │   │
│  └─────────┘  └─────────┘  └────────┘   │
│       │            │            │       │
│       └────────────┴────────────┘       │
│              internal network           │
└─────────────────────────────────────────┘
        │
        ▼
   localhost:8800
      (API)

┌─────────────────────────────────────────┐
│         Local Development               │
│                                         │
│    $ cd my-app/web && pnpm dev          │
│                                         │
│    ┌─────────────────────────────────┐  │
│    │   Next.js Dev Server            │  │
│    │   http://localhost:3000         │  │
│    │                                 │  │
│    │   • Fast HMR                    │  │
│    │   • Native debugging            │  │
│    │   • IDE TypeScript integration  │  │
│    └─────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**CLI behavior with `--app-dev`:**

```typescript
async function upWithAppDev(ctx: ProjectContext): Promise<void> {
  // 1. Scaffold template (same as default)
  await scaffoldTemplate(ctx);

  // 2. Setup env files (same as default)
  await ensureEnvFiles(ctx);

  // 3. Prompt for package manager
  const packageManager = await promptPackageManager();

  // 4. Start Docker services (WITHOUT web)
  // Uses only compose.yaml, NOT compose.web.yaml
  await startDockerServices(ctx, { includeWeb: false });

  // 5. Wait for backend health
  await waitForHealth(ctx, { services: ["api", "db", "cache", "worker"] });

  // 6. Run migrations
  await runMigrations(ctx);

  // 7. Install frontend dependencies
  console.log(`\nInstalling frontend dependencies with ${packageManager}...`);
  await exec(packageManager, ["install"], { cwd: path.join(ctx.dir, "web") });

  // 8. Print instructions
  printAppDevInstructions(ctx, packageManager);
}

function printAppDevInstructions(ctx: ProjectContext, pm: string): void {
  console.log(`
✅ Backend services are running!

   API:      http://localhost:${ctx.ports.api}
   GraphQL:  http://localhost:${ctx.ports.api}/graphql

To start the frontend:

   cd ${ctx.dir}/web
   ${pm} dev

The frontend will be available at http://localhost:3000
`);
}
```

### Package Manager Detection

```typescript
type PackageManager = "pnpm" | "npm" | "yarn" | "bun";

async function promptPackageManager(): Promise<PackageManager> {
  const { packageManager } = await prompts({
    type: "select",
    name: "packageManager",
    message: "Select your package manager:",
    choices: [
      { title: "pnpm", value: "pnpm" },
      { title: "npm", value: "npm" },
      { title: "yarn", value: "yarn" },
      { title: "bun", value: "bun" },
    ],
    initial: 0,
  });

  return packageManager;
}
```

### Comparison Table

| Aspect | Default Mode | App-Dev Mode |
|--------|--------------|--------------|
| **Docker services** | db, cache, api, worker, web | db, cache, api, worker |
| **Frontend runs in** | Docker container (built image) | Local dev server |
| **Hot reload** | None (pre-built image) | Yes (native) |
| **Prerequisites** | Docker only | Docker + Node.js + package manager |
| **IDE integration** | None | Full (TypeScript, debugging) |
| **Use case** | Quick start, testing, production-like environment | Active frontend development |

---

## 7) Release Process Changes

### Updated Release Workflow

The release process now includes:

1. Version bump (all packages)
2. Build and publish Python package (PyPI)
3. Build and publish npm packages (npm)
4. **Build and publish Docker image (GHCR + Docker Hub)**
5. **Build and upload template tarballs (GitHub Release assets)**
6. Publish documentation

### Updated `version-bump.yml`

```yaml
name: Version Bump and Release

on:
  workflow_dispatch:
    inputs:
      bump_type:
        description: "Bump type"
        required: true
        type: choice
        options:
          - patch
          - minor
          - major

jobs:
  bump-and-release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    outputs:
      version: ${{ steps.bump.outputs.version }}
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Configure Git
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"

      - name: Install pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 9

      - name: Bump all package versions
        id: bump
        run: |
          NEW_VERSION=$(python3 scripts/bump_version.py ${{ inputs.bump_type }})
          echo "version=$NEW_VERSION" >> $GITHUB_OUTPUT

      - name: Commit and tag
        run: |
          git add .
          git commit -m "chore: bump to v${{ steps.bump.outputs.version }}"
          git tag "v${{ steps.bump.outputs.version }}"
          git push origin main --tags

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          tag_name: "v${{ steps.bump.outputs.version }}"
          name: "v${{ steps.bump.outputs.version }}"
          generate_release_notes: true
          draft: false
          prerelease: false
          token: ${{ secrets.GITHUB_TOKEN }}

  # ... existing publish-python, publish-npm, publish-cli-launcher jobs ...

  publish-docker:
    needs: bump-and-release
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4
        with:
          ref: "v${{ needs.bump-and-release.outputs.version }}"

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push backend image
        uses: docker/build-push-action@v5
        with:
          context: packages/backend
          file: packages/backend/Dockerfile
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            ghcr.io/weirdfingers/boards-backend:${{ needs.bump-and-release.outputs.version }}
            ghcr.io/weirdfingers/boards-backend:latest
            weirdfingers/boards-backend:${{ needs.bump-and-release.outputs.version }}
            weirdfingers/boards-backend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  publish-templates:
    needs: bump-and-release
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
        with:
          ref: "v${{ needs.bump-and-release.outputs.version }}"

      - name: Install pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 9

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20.x"
          cache: "pnpm"

      - name: Install dependencies
        run: pnpm install

      - name: Build templates
        run: |
          VERSION=${{ needs.bump-and-release.outputs.version }}
          ./scripts/prepare-release-templates.sh "$VERSION"

      - name: Generate compatibility manifest
        run: |
          VERSION=${{ needs.bump-and-release.outputs.version }}
          node scripts/generate-compatibility-manifest.js \
            --version "$VERSION" \
            --output dist/compatibility-manifest.json

      - name: Upload templates to release
        uses: softprops/action-gh-release@v1
        with:
          tag_name: "v${{ needs.bump-and-release.outputs.version }}"
          files: |
            dist/template-baseboards-v${{ needs.bump-and-release.outputs.version }}.tar.gz
            dist/template-basic-v${{ needs.bump-and-release.outputs.version }}.tar.gz
            dist/template-manifest.json
            dist/compatibility-manifest.json
          token: ${{ secrets.GITHUB_TOKEN }}
```

### Release Artifact Summary

After a release, the following artifacts are published:

| Artifact | Destination | Example |
|----------|-------------|---------|
| Python package | PyPI | `boards==0.7.0` |
| Frontend hooks | npm | `@weirdfingers/boards@0.7.0` |
| CLI | npm | `@weirdfingers/baseboards@0.7.0` |
| Backend image | GHCR | `ghcr.io/weirdfingers/boards-backend:0.7.0` |
| Backend image | Docker Hub | `weirdfingers/boards-backend:0.7.0` |
| Baseboards template | GitHub Release | `template-baseboards-v0.7.0.tar.gz` |
| Basic template | GitHub Release | `template-basic-v0.7.0.tar.gz` |
| Template manifest | GitHub Release | `template-manifest.json` |
| Compatibility manifest | GitHub Release | `compatibility-manifest.json` |

---

## 8) Implementation Plan

### Phase 1: Docker Image Publishing

**Goal:** Publish `boards-backend` image on every release.

**Tasks:**
1. Create `packages/backend/Dockerfile` optimized for production
2. Add `publish-docker` job to `version-bump.yml`
3. Configure GHCR and Docker Hub credentials
4. Test multi-arch builds locally with `docker buildx`
5. Verify image works with existing compose files

**Files to create/modify:**
- `packages/backend/Dockerfile` (new)
- `.github/workflows/version-bump.yml` (modify)

### Phase 2: Template System

**Goal:** Download templates from GitHub Releases instead of bundling.

**Tasks:**
1. Create `basic` template in `packages/cli-launcher/basic-template/`
2. Add `extensions/generators/` and `extensions/plugins/` directories to templates with README files
3. Update `storage_config.yaml` in templates to use Docker volume path (`/app/data/storage`)
4. Create `scripts/prepare-release-templates.sh`
5. Create `scripts/generate-template-manifest.js`
6. Add `publish-templates` job to workflow
7. Implement template download logic in CLI
8. Implement local cache in `~/.baseboards/templates/`
9. Add `baseboards templates` command

**Files to create/modify:**
- `packages/cli-launcher/basic-template/` (new directory)
- `packages/cli-launcher/basic-template/extensions/generators/README.md` (new)
- `packages/cli-launcher/basic-template/extensions/plugins/README.md` (new)
- `packages/cli-launcher/template-sources/storage_config.yaml` (modify - update base_path)
- `packages/cli-launcher/src/commands/templates.ts` (new)
- `packages/cli-launcher/src/utils/template-downloader.ts` (new)
- `packages/cli-launcher/src/commands/up.ts` (modify)
- `scripts/prepare-release-templates.sh` (new)
- `scripts/generate-template-manifest.js` (new)
- `.github/workflows/version-bump.yml` (modify)

### Phase 3: Remove Prod Mode, Update Compose

**Goal:** Simplify to single mode with pre-built images (no hot-reload by default).

**Tasks:**
1. Remove `--dev` and `--prod` flags from CLI
2. Remove `compose.dev.yaml` (merge into `compose.yaml`)
3. Update `compose.yaml` to use pre-built backend image (no `--reload`)
4. Add volume mounts for `./extensions` and update `PYTHONPATH` environment variable
5. Add environment variables for `BOARDS_GENERATORS_CONFIG_PATH` and `BOARDS_STORAGE_CONFIG_PATH`
6. Create `compose.web.yaml` overlay for web service (production build)
7. Create `Dockerfile.web` for production Next.js build
8. Update `up` command logic

**Files to modify:**
- `packages/cli-launcher/src/commands/up.ts`
- `packages/cli-launcher/template-sources/compose.yaml` (add extensions volume, env vars)
- `packages/cli-launcher/template-sources/compose.web.yaml` (new, production build)
- `packages/cli-launcher/template-sources/Dockerfile.web` (new, production Next.js)

### Phase 4: App-Dev Mode

**Goal:** Support running frontend locally outside Docker.

**Tasks:**
1. Add `--app-dev` flag to `up` command
2. Implement package manager selection prompt
3. Modify compose file loading logic (skip web overlay when `--app-dev`)
4. Add frontend dependency installation
5. Update success messages with local dev instructions

**Files to modify:**
- `packages/cli-launcher/src/commands/up.ts`
- `packages/cli-launcher/src/utils.ts`

### Phase 5: Template Selection UX

**Goal:** Interactive template selection and `--template` flag.

**Tasks:**
1. Add `--template` flag to `up` command
2. Implement interactive template selector
3. Display template descriptions from manifest
4. Handle template download errors gracefully

**Files to modify:**
- `packages/cli-launcher/src/commands/up.ts`
- `packages/cli-launcher/src/commands/templates.ts`

### Phase 6: Documentation and Testing

**Goal:** Update docs and add tests for new functionality.

**Tasks:**
1. Update CLI README
2. Update docs site with new commands
3. Add integration tests for template download
4. Add integration tests for `--app-dev` mode
5. Test on macOS, Linux, Windows (WSL)

### Phase 7: Upgrade Command

**Goal:** Implement in-place upgrade workflow.

**Tasks:**
1. Replace legacy `update` command with new `upgrade` command
2. Implement mode detection (default vs app-dev)
3. Implement version compatibility checking
4. Create compatibility manifest schema and fetch logic
5. Implement default mode upgrade flow (rebuild frontend image)
6. Implement app-dev mode upgrade flow (manual instructions)
7. Add `--dry-run` and `--force` flags
8. Create compatibility manifest generation script for releases
9. Update release workflow to publish compatibility manifests
10. Add integration tests for upgrade flows

**Files to create/modify:**
- `packages/cli-launcher/src/commands/upgrade.ts` (replace update.ts)
- `packages/cli-launcher/src/utils/compatibility.ts` (new)
- `packages/cli-launcher/src/utils/mode-detection.ts` (new)
- `scripts/generate-compatibility-manifest.js` (new)
- `.github/workflows/version-bump.yml` (modify - add compatibility manifest upload)

---

## 9) Migration Notes

### For Existing Users

Since we're not maintaining backward compatibility, existing users should:

1. **Back up configuration files:**
   ```bash
   cp -r my-app/api/.env my-app/config/ ~/backup/
   ```

2. **Clean up old scaffold:**
   ```bash
   npx @weirdfingers/baseboards clean --hard
   rm -rf my-app
   ```

3. **Re-scaffold with new CLI:**
   ```bash
   npx @weirdfingers/baseboards@latest up my-app --template baseboards
   ```

4. **Restore configuration:**
   ```bash
   cp ~/backup/.env my-app/api/
   cp ~/backup/generators.yaml my-app/config/
   cp ~/backup/storage_config.yaml my-app/config/
   ```

### Breaking Changes Summary

| Change | Impact | Mitigation |
|--------|--------|------------|
| No `--prod` flag | Scripts using `--prod` will fail | Remove flag from scripts |
| Backend from image | Custom backend code won't work | Fork and build own image |
| Templates from release | Offline install won't work | Pre-download templates |
| New project structure | Old scaffolds incompatible | Re-scaffold project |

---

## 10) Upgrade Workflow

### Philosophy

Users should be able to upgrade Baseboards installations in-place without data loss. The upgrade process differs based on deployment mode:

- **Default mode (Docker)**: Automated upgrade with new images and rebuilt frontend
- **App-dev mode**: Semi-automated upgrade with manual dependency updates

**Version policy**: All-or-nothing versioning. CLI, backend images, and frontend templates must match versions. No mixing (e.g., CLI v0.8.0 with backend v0.7.0 is not supported).

**Data preservation**: Storage and configuration are mounted as volumes, so they persist across upgrades (assuming storage format compatibility).

### Command Interface

```bash
# Upgrade to latest version
baseboards upgrade [directory]

# Upgrade to specific version
baseboards upgrade [directory] --version 0.8.0

# Dry run (show what would be upgraded)
baseboards upgrade [directory] --dry-run

# Force upgrade (skip compatibility checks)
baseboards upgrade [directory] --force
```

**Note:** The `upgrade` command replaces the legacy `update` command.

### Upgrade Flow (Default Mode)

For projects running with Docker-based frontend (no `--app-dev`):

```
┌─────────────────────────────────────────────────────────────────┐
│                     Upgrade Process (Default)                    │
└─────────────────────────────────────────────────────────────────┘
  │
  ├─ 1. Detect current version (from docker/.env: BACKEND_VERSION)
  │
  ├─ 2. Determine target version (--version flag or latest)
  │
  ├─ 3. Check compatibility (breaking changes, migration notes)
  │
  ├─ 4. Stop services (baseboards down)
  │
  ├─ 5. Pull new backend Docker images
  │    └─ ghcr.io/weirdfingers/boards-backend:0.8.0
  │
  ├─ 6. Download new template manifest
  │    └─ Check for template structure changes
  │
  ├─ 7. Rebuild frontend Docker image (Dockerfile.web)
  │    ├─ Update web/package.json (@weirdfingers/boards version)
  │    └─ docker compose build web
  │
  ├─ 8. Update docker/.env (BACKEND_VERSION=0.8.0)
  │
  ├─ 9. Start services (baseboards up --no-scaffold)
  │
  ├─ 10. Run database migrations (auto-run via backend healthcheck)
  │
  └─ 11. Verify health (all services healthy)
```

**Implementation:**

```typescript
async function upgradeDefaultMode(ctx: UpgradeContext): Promise<void> {
  const { currentVersion, targetVersion, projectDir } = ctx;

  console.log(chalk.blue(`\n📦 Upgrading from v${currentVersion} to v${targetVersion}\n`));

  // 1. Check compatibility
  await checkCompatibility(currentVersion, targetVersion);

  // 2. Stop services
  console.log(chalk.gray('⏸️  Stopping services...'));
  await stopServices(projectDir);

  // 3. Pull new backend images
  console.log(chalk.gray('⬇️  Pulling new backend images...'));
  await pullBackendImages(targetVersion);

  // 4. Update web/package.json with new @weirdfingers/boards version
  console.log(chalk.gray('📝 Updating frontend dependencies...'));
  await updateWebPackageJson(projectDir, targetVersion);

  // 5. Rebuild frontend Docker image
  console.log(chalk.gray('🔨 Rebuilding frontend image...'));
  await rebuildWebImage(projectDir);

  // 6. Update docker/.env with new version
  console.log(chalk.gray('⚙️  Updating configuration...'));
  await updateEnvVersion(projectDir, targetVersion);

  // 7. Start services (migrations run automatically)
  console.log(chalk.gray('🚀 Starting services...'));
  await startServices(projectDir, { skipScaffold: true });

  // 8. Wait for health
  console.log(chalk.gray('🏥 Waiting for services to be healthy...'));
  await waitForHealth(projectDir);

  console.log(chalk.green(`\n✅ Successfully upgraded to v${targetVersion}!\n`));
  printUpgradeSuccess(ctx);
}
```

### Upgrade Flow (App-Dev Mode)

For projects running with local frontend (`--app-dev`):

```
┌─────────────────────────────────────────────────────────────────┐
│                    Upgrade Process (App-Dev)                     │
└─────────────────────────────────────────────────────────────────┘
  │
  ├─ 1. Detect current version
  │
  ├─ 2. Determine target version
  │
  ├─ 3. Check compatibility
  │
  ├─ 4. Stop Docker services (backend only)
  │
  ├─ 5. Pull new backend Docker images
  │
  ├─ 6. Update docker/.env (BACKEND_VERSION=0.8.0)
  │
  ├─ 7. Start Docker services (backend only)
  │
  ├─ 8. Run database migrations (auto-run)
  │
  ├─ 9. Print manual instructions for frontend
  │    └─ User must update @weirdfingers/boards manually
  │
  └─ 10. Verify backend health
```

**Implementation:**

```typescript
async function upgradeAppDevMode(ctx: UpgradeContext): Promise<void> {
  const { currentVersion, targetVersion, projectDir } = ctx;

  console.log(chalk.blue(`\n📦 Upgrading backend from v${currentVersion} to v${targetVersion}\n`));

  // 1. Check compatibility
  await checkCompatibility(currentVersion, targetVersion);

  // 2. Stop backend services
  console.log(chalk.gray('⏸️  Stopping backend services...'));
  await stopServices(projectDir);

  // 3. Pull new backend images
  console.log(chalk.gray('⬇️  Pulling new backend images...'));
  await pullBackendImages(targetVersion);

  // 4. Update docker/.env
  console.log(chalk.gray('⚙️  Updating configuration...'));
  await updateEnvVersion(projectDir, targetVersion);

  // 5. Start backend services
  console.log(chalk.gray('🚀 Starting backend services...'));
  await startServices(projectDir, { skipScaffold: true, skipWeb: true });

  // 6. Wait for health
  console.log(chalk.gray('🏥 Waiting for backend to be healthy...'));
  await waitForHealth(projectDir, { services: ['api', 'worker', 'db', 'cache'] });

  console.log(chalk.green(`\n✅ Backend upgraded to v${targetVersion}!\n`));

  // 7. Print manual frontend upgrade instructions
  printAppDevUpgradeInstructions(ctx);
}

function printAppDevUpgradeInstructions(ctx: UpgradeContext): void {
  const { targetVersion, projectDir, packageManager } = ctx;

  console.log(chalk.yellow('⚠️  Frontend requires manual upgrade:\n'));
  console.log(chalk.gray('   1. Stop your dev server (Ctrl+C)'));
  console.log(chalk.gray('   2. Update the frontend package:\n'));
  console.log(chalk.cyan(`      cd ${projectDir}/web`));
  console.log(chalk.cyan(`      ${packageManager} update @weirdfingers/boards@${targetVersion}\n`));
  console.log(chalk.gray('   3. Check for breaking changes:'));
  console.log(chalk.gray(`      https://github.com/weirdfingers/boards/releases/tag/v${targetVersion}\n`));
  console.log(chalk.gray('   4. Restart your dev server:\n'));
  console.log(chalk.cyan(`      ${packageManager} dev\n`));
}
```

### Mode Detection

```typescript
function detectProjectMode(projectDir: string): 'default' | 'app-dev' {
  // Check for presence of web service in running containers
  const composeFiles = getComposeFiles(projectDir);

  // If compose.web.yaml is NOT loaded, project is in app-dev mode
  if (!composeFiles.includes('compose.web.yaml')) {
    return 'app-dev';
  }

  return 'default';
}
```

### Version Compatibility Checks

```typescript
interface CompatibilityCheck {
  fromVersion: string;
  toVersion: string;
  breaking: boolean;
  warnings: string[];
  migrationNotes?: string;
}

async function checkCompatibility(
  currentVersion: string,
  targetVersion: string
): Promise<CompatibilityCheck> {
  // 1. Fetch compatibility manifest from GitHub Release
  const manifest = await fetchCompatibilityManifest(targetVersion);

  // 2. Check for breaking changes
  const breaking = manifest.breakingChanges?.some((bc) =>
    semver.satisfies(currentVersion, bc.affectedVersions)
  );

  // 3. Collect warnings
  const warnings: string[] = [];

  if (breaking) {
    warnings.push('⚠️  This upgrade contains breaking changes!');
    warnings.push(`   See: https://github.com/weirdfingers/boards/releases/tag/v${targetVersion}`);
  }

  // 4. Check storage format compatibility
  if (manifest.storageFormatVersion !== currentStorageFormatVersion) {
    warnings.push('⚠️  Storage format has changed - data migration required');
  }

  return {
    fromVersion: currentVersion,
    toVersion: targetVersion,
    breaking,
    warnings,
    migrationNotes: manifest.migrationNotes,
  };
}
```

### Compatibility Manifest

Each release includes a `compatibility-manifest.json` in GitHub Release assets:

```json
{
  "version": "0.8.0",
  "storageFormatVersion": "2",
  "breakingChanges": [
    {
      "affectedVersions": ">=0.7.0 <0.8.0",
      "description": "GraphQL schema: Board.tags field removed",
      "mitigation": "Use Board.metadata.tags instead"
    }
  ],
  "migrationNotes": "https://github.com/weirdfingers/boards/releases/tag/v0.8.0#migration-notes",
  "requiredActions": [
    "Manual .env update required if using custom auth provider"
  ]
}
```

### Rollback Strategy

If upgrade fails or user needs to rollback:

```bash
# Rollback to previous version
baseboards upgrade [directory] --version 0.7.0

# Or manually:
# 1. Update docker/.env: BACKEND_VERSION=0.7.0
# 2. Pull old images: docker compose pull
# 3. Rebuild frontend (default mode): docker compose build web
# 4. Restart: baseboards down && baseboards up
```

**Database migrations**: Rollback is NOT automatically supported. If migrations have run, users must manually restore from backup or run manual SQL to revert schema changes.

### Data Preservation

The following are preserved across upgrades (mounted as volumes):

| Path | Preserved | Notes |
|------|-----------|-------|
| `data/storage/` | ✅ Yes | Generated media (images, videos, audio) |
| `config/*.yaml` | ✅ Yes | Generator and storage configuration |
| `extensions/generators/` | ✅ Yes | Custom generator implementations |
| `extensions/plugins/` | ✅ Yes | Custom plugin implementations |
| `api/.env` | ✅ Yes | API keys, secrets |
| `web/.env` | ✅ Yes | Frontend environment variables |
| `docker/.env` | ⚠️  Merged | Updated with new version, but preserved values |
| `web/src/` | ❌ No (default mode) | Rebuilt from template (customizations lost) |
| `web/src/` | ✅ Yes (app-dev) | User manages via git/version control |

**Recommendations:**

- **Default mode**: If users have customized frontend code, they should switch to `--app-dev` mode or maintain a fork.
- **Extensions**: Custom generators and plugins in `./extensions/` are preserved and do not require special handling during upgrades. They continue to work across versions as long as the Boards plugin API remains compatible.

### CLI Help Output

```
$ baseboards upgrade --help

Usage: baseboards upgrade [directory] [options]

Upgrade an existing Baseboards installation to a new version.

Options:
  --version <version>   Target version (default: latest)
  --dry-run             Show what would be upgraded without making changes
  --force               Skip compatibility checks (dangerous)
  -h, --help            Show help

Examples:
  $ baseboards upgrade my-app
  $ baseboards upgrade my-app --version 0.8.0
  $ baseboards upgrade my-app --dry-run

Notes:
  - All services will be stopped during upgrade
  - Configuration and storage data are preserved
  - Frontend customizations are lost in default mode
  - Use --app-dev mode for frontend customization persistence
```

### Edge Cases

#### 1. Upgrade with running services

If services are running, the CLI should:
1. Warn user that services will be stopped
2. Prompt for confirmation (unless `--force`)
3. Proceed with upgrade

#### 2. Upgrade with uncommitted changes (app-dev)

If user has uncommitted changes in `web/`:
1. Warn user to commit changes before updating dependencies
2. Do NOT automatically update `web/package.json`
3. Print instructions for manual update

#### 3. Upgrade across multiple major versions

If jumping multiple versions (e.g., 0.7.0 → 1.2.0):
1. Fetch compatibility manifests for all intermediate versions
2. Aggregate breaking changes and warnings
3. Recommend step-by-step upgrade if too many breaking changes

#### 4. Downgrade

Downgrading (e.g., 0.8.0 → 0.7.0) is treated as an upgrade:
1. Compatibility checks still apply
2. Database migrations may need manual rollback
3. Warn user about potential data loss

### Testing the Upgrade Flow

```bash
# Test upgrade in a test project
cd /tmp
npx @weirdfingers/baseboards@0.7.0 up test-project --template basic

cd test-project
# Upgrade to latest
npx @weirdfingers/baseboards@latest upgrade . --dry-run
npx @weirdfingers/baseboards@latest upgrade .

# Verify
npx @weirdfingers/baseboards@latest status .
```

---

## 11) Future Extensions

### Planned Templates

| Template | Framework | Status |
|----------|-----------|--------|
| `baseboards` | Next.js (App Router) | Phase 1 |
| `basic` | Next.js (minimal) | Phase 1 |
| `expo` | React Native/Expo | Future |
| `svelte` | SvelteKit | Future |
| `remix` | Remix | Future |
| `cra` | Create React App | Future |

### Template Contribution Guide

Third-party templates can be added by:

1. Creating a template directory structure
2. Ensuring it works with the backend API
3. Submitting a PR to add it to the manifest
4. Templates are reviewed for security and quality

### Potential Features

- **Cloud deployment:** `baseboards deploy --provider fly.io`
- **GPU support:** `--gpu` flag for local GPU inference
- **Custom backend:** `--backend-image my-registry/my-backend:1.0`
- **Template scaffolding without Docker:** `baseboards init --template basic`

---

## Appendix A: Updated Project Structure

```
my-app/                           # Scaffolded project
├── web/                          # Frontend (from template)
│   ├── src/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── .env                      # Generated
├── config/                       # Backend configuration (mounted read-only)
│   ├── generators.yaml           # Generator configuration
│   └── storage_config.yaml       # Storage provider configuration
├── extensions/                   # Custom code (mounted read-only)
│   ├── generators/               # Custom generator implementations
│   │   └── README.md             # Instructions for adding custom generators
│   └── plugins/                  # Plugin implementations
│       └── README.md             # Instructions for adding plugins
├── api/                          # API environment only
│   └── .env                      # Generated (API keys, secrets)
├── data/
│   └── storage/                  # Generated media (volume-mounted, gitignored)
├── docker/
│   └── .env                      # Generated (DB password, ports, versions)
├── compose.yaml                  # Base services (api, worker, db, cache)
├── compose.web.yaml              # Web service overlay (for non-app-dev)
├── Dockerfile.web                # Production Next.js build
├── .gitignore
└── README.md
```

**Volume-mounted directories:**

- **`./config`**: Backend configuration files (read-only)
- **`./data/storage`**: Persistent generated media (read-write)
- **`./extensions`**: Custom generators and plugins (read-only)

## Appendix B: Environment Variables Reference

### `docker/.env`

```bash
PROJECT_NAME=baseboards
BACKEND_VERSION=0.7.0
WEB_PORT=3300
API_PORT=8800
POSTGRES_USER=baseboards
POSTGRES_PASSWORD=<generated>
POSTGRES_DB=baseboards
BOARDS_DATABASE_URL=postgresql://baseboards:<pw>@db:5432/baseboards
BOARDS_REDIS_URL=redis://cache:6379/0
```

### `api/.env`

```bash
BOARDS_API_PORT=8800
BOARDS_CORS_ORIGINS=["http://localhost:3300"]
BOARDS_JWT_SECRET=<generated>
BOARDS_AUTH_PROVIDER=none
BOARDS_GENERATOR_API_KEYS={"REPLICATE_API_KEY":"...","FAL_KEY":"..."}
BOARDS_GENERATORS_CONFIG_PATH=/app/config/generators.yaml
BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml
```

**Note:** `PYTHONPATH=/app:/app/extensions` is set in `compose.yaml` environment variables to enable loading custom generators and plugins from the `./extensions/` directory.

### `web/.env`

```bash
NEXT_PUBLIC_API_URL=http://localhost:8800
NEXT_PUBLIC_GRAPHQL_URL=http://localhost:8800/graphql
INTERNAL_API_URL=http://api:8800
NEXT_PUBLIC_AUTH_PROVIDER=none
```

## Appendix C: CLI Help Output

```
$ npx @weirdfingers/baseboards --help

Usage: baseboards [command] [options]

Commands:
  up [dir]          Scaffold and start a Boards project
  upgrade [dir]     Upgrade existing installation to new version
  down [dir]        Stop running services
  logs [dir]        View service logs
  status [dir]      Show service status
  clean [dir]       Remove containers and optionally volumes
  templates         List available templates
  doctor [dir]      Run diagnostics

Options:
  -v, --version     Show version number
  -h, --help        Show help

Examples:
  $ baseboards up my-app --template baseboards
  $ baseboards up my-app --template basic --app-dev
  $ baseboards upgrade my-app
  $ baseboards upgrade my-app --version 0.8.0 --dry-run
  $ baseboards down my-app --volumes
  $ baseboards logs my-app api worker -f

Documentation: https://boards.weirdfingers.com/docs/cli
```
