# npx Full‑Stack Launcher — Technical Design

**Goal:** Package a Next.js frontend + FastAPI backend (with Postgres + Redis) into a turnkey experience that runs with a single command:

```bash
npx @weirdfingers/baseboards@latest up my-app
```

This command should scaffold a project directory, generate an `.env`, pull/build Docker images, run the stack with `docker compose`, and expose the web app on `http://localhost:3300` with hot reload for local development. The solution must work on macOS, Windows (incl. WSL2), and Linux.

---

## Table of Contents

1. Objectives & Non‑Goals
2. User Experience (UX) Flows
3. High-Level Architecture
4. Components & Responsibilities
5. CLI Specification (Node.js/TypeScript)
6. Project Layout (Scaffold)
7. Docker & Compose Strategy
8. Environment & Secrets Management
9. Health Checks, Readiness, and Logs
10. Development Mode vs Production Mode
11. Update & Versioning Strategy
12. Telemetry (Opt‑In) & Diagnostics
13. Testing Strategy (Unit/Integration/E2E)
14. Release Process (CI/CD)
15. Security Considerations
16. Observability (optional)
17. Failure Modes & Recovery
18. Acceptance Criteria
19. Future Extensions

---

## 1) Objectives & Non‑Goals

### Objectives

- **One-liner start:** `npx @weirdfingers/baseboards up <dir>` brings up a full stack locally via Docker.
- **Zero global installs:** Only prerequisites are Docker Desktop / Engine + Node >= 20.
- **Scaffold + Run:** Scaffolds the Boards image generation application with full source code for local development and customization.
- **Cross‑platform:** macOS, Windows (native/WSL2), Linux.
- **Predictable images:** Use versioned images; deterministic builds.
- **Graceful teardown:** `npx @weirdfingers/baseboards down` stops and removes containers/volumes.

### Non‑Goals

- Cloud deploys (can be added later).
- Multi‑host orchestration (Kubernetes, Nomad) — out of scope.
- GPU workflows — optional future.

---

## 2) User Experience (UX) Flows

### New project

```bash
npx @weirdfingers/baseboards up my-app
# prompts for: port collisions, Postgres password, .env creation
# opens http://localhost:3300 when ready
```

### Start existing project

```bash
npx @weirdfingers/baseboards up
# detects existing scaffold in cwd and starts stack
```

### Stop stack

```bash
npx @weirdfingers/baseboards down
```

### View logs

```bash
npx @weirdfingers/baseboards logs web api db
```

### Clean everything (volumes, images for this project)

```bash
npx @weirdfingers/baseboards clean --hard
```

### Update to latest template/images

```bash
npx @weirdfingers/baseboards update
```

---

## 3) High‑Level Architecture

```
+--------------------------------------------------------------+
|                    npx Full‑Stack Launcher                   |
|  Node.js CLI (TypeScript)                                    |
|  - scaffold generator (templates)                             |
|  - interactive API key setup                                  |
|  - env management (.env files)                                |
|  - docker-compose orchestrator                                |
|  - automatic migrations                                       |
|  - health checks & port management                            |
|  - logs, status, update checker                               |
+--------------------------+-----------------------------------+
                           |
                           v
                 docker compose (v2) files
                /project/compose.yaml (+ overrides)
                           |
     +-----------+-----------+-----------+-----------+-----------+
     |           |           |           |           |           |
     v           v           v           v           v
  Next.js      FastAPI     Worker      Postgres     Redis
  (web)         (api)      (Dramatiq)   (db)        (cache)
```

- **Services:**
  - `web`: Next.js frontend (Node 20-alpine, standalone build)
  - `api`: FastAPI backend (Python 3.12-slim with uv)
  - `worker`: Dramatiq background jobs (same image as api)
  - `db`: PostgreSQL 16 (official)
  - `cache`: Redis 7 (official)
- **Compose:** Base `compose.yaml` + `compose.dev.yaml` for live‑reload and volume mounts
- **Images:** Built locally from Dockerfiles included in scaffolded project

---

## 4) Components & Responsibilities

- **CLI (`@weirdfingers/baseboards`)**

  - Bootstraps project from embedded templates.
  - Generates secrets (DB password, JWT secret) when absent.
  - Validates prerequisites (Docker, Node version, disk space, WSL check on Windows).
  - Ensures ports free (3300, 8800, 5432, 6379 by default) or selects alternatives.
  - Writes `.env` and `docker/.env` for compose.
  - Runs `docker compose` with appropriate profiles.
  - Waits for health checks; prints next steps.

- **Templates** (bundled in the npm package):

  - `web/` — The Boards Next.js frontend (App Router + Tailwind + shadcn + SSE)
  - `api/` — The Boards FastAPI backend (uvicorn, SQLAlchemy, Alembic, Dramatiq workers)
  - `compose.yaml`, `compose.dev.yaml`, Dockerfiles
  - Configuration templates from `baseline-config/`: `generators.yaml`, `storage_config.yaml` (work out-of-the-box)

  **Template Preparation (Build-Time):**

  - Templates are **auto-copied** from monorepo during CLI build via `scripts/prepare-templates.js`
  - Copies `apps/baseboards` → `templates/web/` (excluding build artifacts, tests)
  - Copies `packages/backend` → `templates/api/` (excluding .venv, **pycache**, tests, examples)
  - Copies standalone template files from `template-sources/`:
    - `compose.yaml`, `compose.dev.yaml` (with worker service)
    - `Dockerfile.web`, `Dockerfile.api` (local build configs)
    - `.env.example` files for web, api, and docker
    - `.gitignore`, `README.md`
  - **Transformations applied:**
    - `workspace:*` dependencies → `^{version}` (e.g., `@weirdfingers/boards: ^0.1.8`)
    - Next.js config: adds `output: "standalone"`, `unoptimized: true`, `rewrites` for `/api/storage`
    - Storage config: updates `base_path` from `/tmp/boards/storage` to `./data/storage`
    - Storage config: updates `public_url_base` to `http://localhost:8800/api/storage`
  - Result: Editing source apps automatically includes changes in next CLI build

- **Docker Images**
  - **Development**: Built locally from included Dockerfiles during `docker compose up`
  - Dockerfiles are part of the scaffolded project for customization
  - Future: Can be pre-built and pushed to registry for faster startup

---

## 5) CLI Specification (Node.js/TypeScript)

**Package name:** `@weirdfingers/baseboards`

**Entry:** `bin/baseboards` (invoked via `npx`).

**Commands**

- `up [dir] [--dev|--prod] [--detached] [--ports web=3300 api=8800 db=5432 redis=6379]`
- `down` — stop & remove containers
- `logs [service...] [--since 1h] [--follow]`
- `status` — container states + health
- `clean [--hard]` — remove volumes/images scoped by project label
- `update` — refresh templates & pull latest tagged images
- `doctor` — diagnostic report for support

**Implementation Outline**

```ts
// src/index.ts
import { run } from "./router";
run(process.argv);
```

```ts
// src/commands/up.ts
export async function up(args: UpArgs) {
  await assertPrerequisites(); // docker, node, platform
  const ctx = await resolveProject(args.dir);
  const isFreshScaffold = !ctx.isScaffolded;

  if (!ctx.isScaffolded) {
    await scaffoldProject(ctx); // copies templates including baseline-config YAMLs
  }

  await reservePorts(ctx); // picks non-conflicting ports (3300, 8800)
  await ensureEnvFiles(ctx); // writes .env files from .example templates, generates secrets

  if (isFreshScaffold) {
    await promptForApiKeys(ctx); // interactive prompts for REPLICATE_API_KEY, OPENAI_API_KEY
  }

  await detectMissingProviderKeys(ctx); // warns if no API keys configured
  await startDockerCompose(ctx, { detached: true }); // always start in detached mode
  await waitForHealth(ctx, { timeoutMs: 120_000 }); // web, api, db, cache, worker
  await runMigrations(ctx); // docker compose exec api alembic upgrade head
  printSuccessMessage(ctx); // http://localhost:PORTs + setup instructions
  await attachToLogs(ctx); // stream logs (graceful Ctrl+C to exit)
}
```

**Key Libraries**

- `commander` (CLI parsing)
- `execa` (shelling out to `docker compose`)
- `fs-extra`, `yaml` (file ops)
- `ora`, `chalk` (UX - spinners and colors)
- `prompts` (interactive user input for API keys)
- `which` (locating executables)

**Distribution**

- `type: module`, Node 20+
- Publish to npm with `files` whitelist to include only `/dist` and `/templates`.

---

## 6) Project Layout (Scaffold)

```
my-app/
├─ web/                        # Next.js app (App Router)
│  ├─ .env.example             # frontend env template
│  ├─ .env                     # generated (gitignored)
│  └─ Dockerfile               # Next.js standalone build
├─ api/                        # FastAPI app
│  ├─ .env.example             # backend env template (API keys!)
│  ├─ .env                     # generated (gitignored)
│  ├─ Dockerfile               # Python backend build
│  └─ config/
│     ├─ generators.yaml       # works OOB, user customizes
│     └─ storage_config.yaml   # works OOB, user customizes
├─ data/
│  └─ storage/                 # local file storage (gitignored)
├─ docker/
│  ├─ env.example              # example compose env
│  └─ .env                     # generated (gitignored)
├─ .gitignore                  # ignores .env, data/storage, node_modules, etc.
├─ compose.yaml                # base services (web, api, db, cache, worker)
├─ compose.dev.yaml            # dev overrides (volume mounts, hot reload)
└─ README.md
```

**Note:** The scaffold includes a `.gitignore` that excludes:

- All `.env` files (secrets never committed)
- `data/storage/` (generated media stays local)
- Standard patterns (`node_modules`, `.venv`, `__pycache__`, `.next`, etc.)

### web/ (Next.js)

- Dev mode: bind mount `./web:/app` + `node_modules` volume for hot reload
- Built locally with `output: "standalone"` for Docker optimization
- Image optimization disabled (`unoptimized: true`) for local development
- Rewrites `/api/storage` to `http://api:8800/api/storage` for server-side image fetching

### api/ (FastAPI)

- Dev mode: bind mount `./api:/app` + `uvicorn --reload` for hot reload
- Built locally from Dockerfile during `docker compose up`
- Includes Alembic migrations, Dramatiq workers, and all dependencies

---

## 7) Docker & Compose Strategy

### compose.yaml (base)

- Services: `web`, `api`, `worker`, `db` (Postgres 16), `cache` (Redis 7)
- Networks: `internal` (private)
- Healthchecks:
  - `web`: `curl -f http://localhost:3300/`
  - `api`: `curl -f http://localhost:8800/health`
  - `worker`: `dramatiq-gevent boards.workers.actors:broker --processes 1 --threads 50`
  - `db`: `pg_isready -U $POSTGRES_USER`
  - `cache`: `redis-cli ping`
- **Automatic migrations**: CLI runs `alembic upgrade head` in API container after services are healthy
- Labels: `com.weirdfingers.baseboards.project=<dir>` to scope cleanup

### compose.dev.yaml (overrides)

- Binds local sources into containers for hot reload
- Web: `sh -c "pnpm install && pnpm dev"` for auto-install dependencies
- API: `uvicorn boards.api.app:app --host 0.0.0.0 --port 8800 --reload`
- Worker: volume mounts `./api/src:/app/src` for hot reload
- Mounts `node_modules` and `.next` as named volumes to avoid host pollution
- Binds `./data/storage` into API and worker containers for local file access

### Images

- **Built locally** during `docker compose up` (not pulled from registry)
- Dockerfiles included in scaffolded project for customization
- Web: Node 20-alpine with Next.js standalone output
- API/Worker: Python 3.12-slim with uv for fast dependency installation

---

## 8) Environment & Secrets Management

- `web/.env` (frontend):
  - `NEXT_PUBLIC_API_URL=http://localhost:8800`
  - `NEXT_PUBLIC_GRAPHQL_URL=http://localhost:8800/graphql`
  - `NEXT_PUBLIC_AUTH_PROVIDER=none` (for local development)
- `api/.env` (backend - **critical for users**):
  - `BOARDS_JWT_SECRET=...` (auto-generated by CLI)
  - `BOARDS_API_PORT=8800`
  - `BOARDS_CORS_ORIGINS=["http://localhost:3300"]`
  - `BOARDS_AUTH_PROVIDER=none` (for local development)
  - **Generator API Keys** (JSON format, user prompted during scaffold):
    - `BOARDS_GENERATOR_API_KEYS={"REPLICATE_API_KEY":"r8_...","OPENAI_API_KEY":"sk-..."}`
    - CLI prompts for `REPLICATE_API_KEY` and `OPENAI_API_KEY` during initial scaffold
    - Users can skip and add later by editing `api/.env`
  - Optional auth configuration (Clerk/Supabase/Auth0 keys)
- `docker/.env` (compose-level):
  - `PROJECT_NAME=<dir-name>`
  - `VERSION=<cli-version>` (for image tags)
  - `WEB_PORT=3300`
  - `API_PORT=8800`
  - `POSTGRES_USER=baseboards`
  - `POSTGRES_PASSWORD=<generated>`
  - `POSTGRES_DB=baseboards`
  - `BOARDS_DATABASE_URL=postgresql://baseboards:<pw>@db:5432/baseboards` (note BOARDS\_ prefix)
  - `BOARDS_REDIS_URL=redis://cache:6379/0` (note BOARDS\_ prefix)
- Generated by CLI on first run; never committed.
- **Interactive setup**: CLI prompts for API keys during initial scaffold with helpful URLs
- **Detection**: CLI warns if no provider keys are configured but allows startup

### Configuration Files

YAML configuration files in `api/config/` are copied from `baseline-config/` templates:

- **`generators.yaml`** — Defines available image generation providers and models
  - Works out-of-the-box with common providers (Replicate, FAL, OpenAI, Google)
  - Users enable providers by adding API keys to `BOARDS_GENERATOR_API_KEYS` in `.env`
  - Optional customization: add custom models, toggle specific workflows
  - Source: `packages/backend/baseline-config/generators.yaml`
- **`storage_config.yaml`** — Configures where generated images are stored
  - **Default: local filesystem at `./data/storage/`** (relative to project root)
  - CLI automatically updates path from `/tmp/boards/storage` to `./data/storage` during scaffold
  - Works immediately; generated media is accessible in the project directory
  - Optional customization: switch to S3, GCS, Cloudflare R2, or Supabase
  - Users can customize routing rules (e.g., large files → S3, images → CDN)
  - Source: `packages/backend/baseline-config/storage_config.yaml`

The CLI copies these files on first scaffold. They work immediately but are fully customizable for production deployments.

---

## 9) Health Checks, Readiness, and Logs

- **API** exposes `/health` returning `{"ok": true}`.
- **Web** exposes `/api/health` proxying to API (ensures end‑to‑end wiring).
- CLI `waitForHealth()` polls Docker health statuses until `healthy`.
- `logs` command tails selected services using `docker compose logs` with project label.

---

## 10) Development Mode vs Production Mode

- `--dev` (default): bind mounts, hot reload, minimal optimizations.
- `--prod`: uses prebuilt images (no bind mounts), `NODE_ENV=production`, `gunicorn` for API, Next.js `start` serving compiled output.
- Ports are configurable; defaults: `3300` (web), `8800` (api).

---

## 11) Update & Versioning Strategy

### Unified Versioning

All packages use **unified versioning** - CLI, libraries, images, and templates share the same version number:

- `@weirdfingers/baseboards` (CLI): v1.2.0
- `@weirdfingers/frontend`: v1.2.0
- `@weirdfingers/auth-clerk`: v1.2.0
- Docker images: `weirdfingers/baseboards-web:1.2.0`

**Benefits:**

- Guaranteed compatibility between all components
- Simpler mental model for users
- Single version number to track
- Templates always reference matching package versions

**Release workflow:**

1. Bump all packages simultaneously: `pnpm version 1.2.0 -r`
2. Build CLI (templates auto-copied from apps/baseboards and packages/backend)
3. Publish all packages: `pnpm publish -r`
4. Build and push Docker images with matching tags
5. Create git tag: `git tag v1.2.0`

### Update Command

The `update` command upgrades user installations to the latest version while **preserving configuration**.

**Files that are OVERWRITTEN (source code):**

- `packages/web/src/` — Frontend application code
- `packages/api/src/` — Backend application code
- `package.json`, `pyproject.toml` — Dependencies
- `compose.yaml`, `compose.dev.yaml` — Docker orchestration

**Files that are PRESERVED (user configuration):**

- All `.env` files (secrets and API keys)
- `config/generators.yaml` — Provider configuration
- `config/storage_config.yaml` — Storage configuration
- `data/storage/` — Generated media files

**UX Flow:**

```bash
$ npx @weirdfingers/baseboards update

🔍 Checking for updates...
📦 New version available: v1.2.0 (currently v1.1.0)

✅ Your configuration will be preserved:
   • .env files (API keys, secrets)
   • config/*.yaml files
   • data/storage/ (generated media)

⚠️  Source code will be updated to latest version.
   Custom code modifications will be overwritten.

Scanning for modifications... Done.
✅ No custom source code changes detected.

Update now? (Y/n): y
✨ Updating... Done!
```

**For users with custom code changes:**

- CLI detects modified source files (git diff or timestamp comparison)
- Warns user explicitly about conflicts
- If git repo detected: offers 3-way merge with conflict markers
- If no git repo: creates timestamped backup before proceeding
- User can use `--force` to skip safety checks

---

## 12) Telemetry (Opt‑In) & Diagnostics

- First run prompts: "Share anonymous usage to improve the tool? (y/N)"
- Data: command name, duration, OS, success/failure. No PII.
- `doctor` emits: Docker version, Compose version, platform, port usage, disk space, truncated logs, **missing provider API keys**, config file validation.

---

## 13) Testing Strategy

- **Unit Tests (Jest):** CLI arg parsing, env generation, port allocator.
- **Integration (local docker):** Spin up with ephemeral project name, assert health.
- **E2E (GitHub Actions):** Matrix for macOS/Linux/Windows (with WSL), run `npx ... up`, poll health, run smoke tests (`/health`, DB insert).

---

## 14) Release Process (CI/CD)

- **Repo:** `weirdfingers/baseboards`
- **Pipelines:**
  1. Build & test CLI (tsc + jest).
  2. Build images `weirdfingers/baseboards-web`, `weirdfingers/baseboards-api`; push to GHCR with tag = package.json version.
  3. Publish npm on `git tag vX.Y.Z`.
  4. Create GitHub Release with changelog + compose templates.

---

## 15) Security Considerations

- Default credentials are randomly generated.
- Compose network is isolated; DB not published outside Docker network by default.
- CORS configured to allow `http://localhost:3300` in dev.
- Images run as non‑root users when possible.
- Supply chain: lock base images by digest; renovate bot for updates.

---

## 16) Observability (optional)

- Add `otel-collector` service + `OTEL_EXPORTER_OTLP_ENDPOINT` wiring.
- Add `pgadmin` and `redisinsight` profiles for debugging.

---

## 17) Failure Modes & Recovery

- **Port collisions** → auto‑increment ports or prompt user.
- **Docker missing** → actionable error with install link guidance.
- **WSL not configured** → prompt to enable WSL2 & integrate Docker Desktop.
- **Image pull fails** → retry with exponential backoff; fall back to local build if sources present.
- **Health timeout** → print per‑service logs and common fixes.

---

## 18) Acceptance Criteria

- Running `npx @weirdfingers/baseboards up my-app` on macOS/Windows/Linux:
  - scaffolds files, generates `.env`s
  - starts containers and reaches `healthy` within 2 minutes on a typical laptop
  - web is reachable at `http://localhost:<web_port>`; API at `/api/hello`; DB accepts connections.
- `down`, `logs`, `status`, `clean` behave as specified.

---

## 19) Future Extensions

- **brew tap** for `brew install baseboards` wrapper around npm.
- **pip**-installable Python CLI that delegates to the Node CLI.
- **Cloud deploy** subcommand to push to Fly.io/Render/Vercel + Railway.
- **Profiles** for optional services (MinIO, n8n, alternative storage backends).

---

## Appendix A — Example `compose.yaml` (excerpt)

```yaml
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

  cache:
    image: redis:7
    command: ["redis-server", "--appendonly", "yes"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20

  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    env_file:
      - docker/.env
      - api/.env
    volumes:
      - ./data/storage:/app/data/storage
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

  worker:
    build:
      context: ./api
      dockerfile: Dockerfile
    env_file:
      - docker/.env
      - api/.env
    command:
      [
        "dramatiq-gevent",
        "boards.workers.actors:broker",
        "--processes",
        "1",
        "--threads",
        "50",
      ]
    volumes:
      - ./data/storage:/app/data/storage
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

  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    env_file: web/.env
    depends_on:
      api:
        condition: service_healthy
    ports:
      - "${WEB_PORT:-3300}:3300"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3300/"]
      interval: 5s
      timeout: 3s
      retries: 50

volumes:
  db-data:
```

## Appendix B — CLI Pseudocode: Port Reservation

```ts
async function pickPort(preferred: number): Promise<number> {
  const isFree = await checkPort(preferred);
  if (isFree) return preferred;
  for (let p = preferred + 1; p < preferred + 50; p++) {
    if (await checkPort(p)) return p;
  }
  throw new Error(`No free port near ${preferred}`);
}
```

## Appendix C — Template: FastAPI `main.py` (excerpt)

```py
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/hello")
def hello():
    return {"message": "Hello from FastAPI"}
```

## Appendix D — Template: Next.js route (health proxy)

```ts
// app/api/health/route.ts
export async function GET() {
  try {
    const r = await fetch(process.env.NEXT_PUBLIC_API_URL + "/health");
    const data = await r.json();
    return Response.json({ ok: data.ok === true });
  } catch {
    return Response.json({ ok: false }, { status: 503 });
  }
}
```

## Appendix E — README Quickstart (generated)

````md
# My App — Boards Image Generation

## Prerequisites

- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Node.js 20+

## Quick Start

```bash
npx @weirdfingers/baseboards up my-app
cd my-app
```

During setup, you'll be prompted to enter API keys for image generation providers:

- **Replicate**: Get from https://replicate.com/account/api-tokens
- **OpenAI**: Get from https://platform.openai.com/api-keys

You can skip these prompts and add keys later by editing `api/.env`.

The CLI will:

1. Scaffold the project with full source code
2. Generate environment files with secure secrets
3. Build and start all services (web, api, worker, database, cache)
4. Run database migrations automatically
5. Open your app at http://localhost:3300

Press Ctrl+C to stop viewing logs (services continue running in background).

## Managing Your App

```bash
# View logs
npx @weirdfingers/baseboards logs

# Stop services
npx @weirdfingers/baseboards down

# Check status
npx @weirdfingers/baseboards status
```

## Adding More API Keys

Edit `api/.env` and add keys to the JSON object:

```
BOARDS_GENERATOR_API_KEYS={"REPLICATE_API_KEY":"r8_...","OPENAI_API_KEY":"sk-...","FAL_KEY":"..."}
```

Then restart: `npx @weirdfingers/baseboards down && npx @weirdfingers/baseboards up`
````
