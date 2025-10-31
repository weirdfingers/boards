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
|  - env management (.env/.env.local)                           |
|  - docker-compose orchestrator                                |
|  - health checks & port management                            |
|  - logs, status, update checker                               |
+--------------------------+-----------------------------------+
                           |
                           v
                 docker compose (v2) files
                /project/compose.yaml (+ overrides)
                           |
     +-----------+-----------+-----------+-----------+
     |           |           |           |           |
     v           v           v           v
  Next.js      FastAPI     Postgres     Redis
  (web)         (api)        (db)        (cache)
```

- **Images:**
  - `weirdfingers/baseboards-web:TAG` (Next.js, Node 20-alpine)
  - `weirdfingers/baseboards-api:TAG` (FastAPI, Python 3.12-slim)
  - `postgres:16` (official)
  - `redis:7` (official)
- **Compose:** One base `compose.yaml` plus `compose.dev.yaml` for live‑reload and host mounts.

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

  - `packages/web` — The Boards Next.js frontend (App Router + Tailwind + shadcn).
  - `packages/api` — The Boards FastAPI backend (with uvicorn, SQLAlchemy, Alembic, Dramatiq).
  - `compose.yaml` & `compose.dev.yaml`.
  - `Makefile` helpers (optional).
  - Configuration templates from `baseline-config/`: `generators.yaml`, `storage_config.yaml` (work out-of-the-box).

  **Template Preparation (Build-Time):**

  - Templates are **auto-copied** from monorepo during CLI build via `scripts/prepare-templates.js`
  - Copies `apps/baseboards` → `templates/web/` (excluding build artifacts)
  - Copies `packages/backend` → `templates/api/` (excluding .venv, **pycache**)
  - Transforms `workspace:*` dependencies → `^{version}` (published package versions)
  - Generates `.env.example` files from templates
  - Updates `storage_config.yaml` paths to be relative to project root
  - Result: Editing source apps automatically includes changes in next CLI build

- **Docker Images**
  - Built in CI and pushed to GHCR or Docker Hub.
  - Tagged by semantic version matching the CLI version (e.g., `1.2.0`).

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
  await assertPrereqs(); // docker, node, platform
  const ctx = await resolveProject(args.dir);
  await scaffoldIfMissing(ctx); // copies templates including baseline-config YAMLs
  await ensureEnvFiles(ctx); // writes .env files from .example templates
  await ensureDataDirectory(ctx); // creates data/storage/ for local files
  await reservePorts(ctx); // picks non-conflicting ports
  await writeComposeOverrides(ctx); // compose.dev.yaml if --dev
  await dockerComposeUp(ctx, { detached: args.detached });
  await waitForHealth(ctx, { timeoutMs: 120_000 });
  await detectMissingProviderKeys(ctx); // warns if no API keys configured
  printEndpoints(ctx); // http://localhost:PORTs + setup instructions
}
```

**Key Libraries**

- `commander` (CLI parsing)
- `execa` (shelling out to `docker compose`)
- `fs-extra`, `yaml` (file ops)
- `ora`, `chalk` (UX)
- `which` (locating executables)

**Distribution**

- `type: module`, Node 20+
- Publish to npm with `files` whitelist to include only `/dist` and `/templates`.

---

## 6) Project Layout (Scaffold)

```
my-app/
├─ packages/
│  ├─ web/                     # Next.js app (App Router)
│  │  ├─ .env.example          # frontend env template
│  │  └─ .env                  # generated (gitignored)
│  └─ api/                     # FastAPI app
│     ├─ .env.example          # backend env template (API keys!)
│     ├─ .env                  # generated (gitignored)
│     └─ config/
│        ├─ generators.yaml    # works OOB, user customizes
│        └─ storage_config.yaml # works OOB, user customizes
├─ data/
│  └─ storage/                 # local file storage (gitignored)
├─ docker/
│  ├─ env.example              # example compose env
│  └─ .env                     # generated (gitignored)
├─ .gitignore                  # ignores .env, data/storage, node_modules, etc.
├─ compose.yaml
├─ compose.dev.yaml
├─ Makefile                    # optional helpers
└─ README.md
```

**Note:** The scaffold includes a `.gitignore` that excludes:

- All `.env` files (secrets never committed)
- `data/storage/` (generated media stays local)
- Standard patterns (`node_modules`, `.venv`, `__pycache__`, `.next`, etc.)

### packages/web (Next.js)

- Dev server in dev mode with bind mount `./packages/web:/app` + `node_modules` volume.
- Production build baked in `weirdfingers/baseboards-web:TAG`.

### packages/api (FastAPI)

- `uvicorn app.main:app --host 0.0.0.0 --port 8800 --reload` in dev.
- `gunicorn -k uvicorn.workers.UvicornWorker app.main:app` in prod.

---

## 7) Docker & Compose Strategy

### compose.yaml (base)

- Services: `web`, `api`, `db` (Postgres 16), `cache` (Redis 7).
- Networks: `internal` (private).
- Healthchecks:
  - `web`: `curl -f http://localhost:3300/api/health`
  - `api`: `curl -f http://localhost:8800/health`
  - `db`: `pg_isready -U $POSTGRES_USER`
  - `cache`: `redis-cli ping`
- Labels: `com.weirdfingers.baseboards.project=<dir>` to scope cleanup.

### compose.dev.yaml (overrides)

- Binds local sources into containers for hot reload.
- Mounts `node_modules` and `.next` as named volumes to avoid host pollution.
- Binds `./data/storage` into API container for local file access.
- Uses `pip install -e .` or `uvicorn --reload` patterns for API.

### Images

- Prebuilt for quick start. For contributors, `docker buildx bake` can rebuild.

---

## 8) Environment & Secrets Management

- `packages/web/.env` (frontend):
  - `NEXT_PUBLIC_API_URL=http://localhost:8800`
  - `NEXT_PUBLIC_GRAPHQL_URL=http://localhost:8800/graphql`
- `packages/api/.env` (backend - **critical for users**):
  - `JWT_SECRET=...` (generated)
  - **Provider API keys** (user must configure at least one):
    - `REPLICATE_API_KEY=r8_...` — Get from replicate.com
    - `FAL_KEY=...` — Get from fal.ai
    - `OPENAI_API_KEY=sk-...` — Get from openai.com
    - `GOOGLE_API_KEY=...` — For Gemini models
  - Auth configuration (Clerk/Supabase/Auth0 keys)
- `docker/.env` (compose-level):
  - `POSTGRES_USER=baseboards`
  - `POSTGRES_PASSWORD=<generated>`
  - `POSTGRES_DB=baseboards`
  - `DB_URL=postgresql://baseboards:<pw>@db:5432/baseboards`
  - `REDIS_URL=redis://cache:6379/0`
- Generated by CLI on first run; never committed.
- **First-run UX**: CLI detects missing provider keys and prints setup instructions with docs link.

### Configuration Files

YAML configuration files in `packages/api/config/` are copied from `baseline-config/` templates:

- **`generators.yaml`** — Defines available image generation providers and models
  - Works out-of-the-box with common providers (Replicate, FAL, OpenAI, Google)
  - Users enable providers by adding API keys to `.env`
  - Optional customization: add custom models, toggle specific workflows
  - Source: `baseline-config/generators.yaml`
- **`storage_config.yaml`** — Configures where generated images are stored
  - **Default: local filesystem at `data/storage/`** (relative to project root)
  - Works immediately; generated media is accessible in the project directory
  - Optional customization: switch to S3, GCS, Cloudflare R2, or Supabase
  - Users can customize routing rules (e.g., large files → S3, images → CDN)
  - Source: `baseline-config/storage_config.yaml`

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
    image: weirdfingers/baseboards-api:${VERSION}
    env_file: docker/.env
    environment:
      - DB_URL=${DB_URL}
      - REDIS_URL=${REDIS_URL}
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

  web:
    image: weirdfingers/baseboards-web:${VERSION}
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${API_PORT:-8800}
    depends_on:
      api:
        condition: service_healthy
    ports:
      - "${WEB_PORT:-3300}:3300"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3300/api/health"]
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
npx @weirdfingers/baseboards up
```

After scaffolding, **configure your API keys** in `packages/api/.env`:

- Add at least one provider key (Replicate, FAL, OpenAI, or Google)
- See docs: https://baseboards.dev/docs/setup

Visit http://localhost:3300
````
