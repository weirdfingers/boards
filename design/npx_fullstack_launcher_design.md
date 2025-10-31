# npx Full‑Stack Launcher — Technical Design

**Goal:** Package a Next.js frontend + FastAPI backend (with Postgres + Redis) into a turnkey experience that runs with a single command:

```bash
npx @acme/fullstack-launcher@latest up my-app
```

This command should scaffold a project directory, generate an `.env`, pull/build Docker images, run the stack with `docker compose`, and expose the web app on `http://localhost:3000` with hot reload for local development. The solution must work on macOS, Windows (incl. WSL2), and Linux.

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
- **One-liner start:** `npx @acme/fullstack-launcher up <dir>` brings up a full stack locally via Docker.
- **Zero global installs:** Only prerequisites are Docker Desktop / Engine + Node >= 18.
- **Scaffold + Run:** Creates a minimal monorepo structure (Next.js app, FastAPI API) ready for development.
- **Cross‑platform:** macOS, Windows (native/WSL2), Linux.
- **Predictable images:** Use versioned images; deterministic builds.
- **Graceful teardown:** `npx @acme/fullstack-launcher down` stops and removes containers/volumes.

### Non‑Goals
- Cloud deploys (can be added later).
- Multi‑host orchestration (Kubernetes, Nomad) — out of scope.
- GPU workflows — optional future.

---

## 2) User Experience (UX) Flows

### New project
```bash
npx @acme/fullstack-launcher up my-app
# prompts for: port collisions, Postgres password, .env creation
# opens http://localhost:3000 when ready
```

### Start existing project
```bash
npx @acme/fullstack-launcher up
# detects existing scaffold in cwd and starts stack
```

### Stop stack
```bash
npx @acme/fullstack-launcher down
```

### View logs
```bash
npx @acme/fullstack-launcher logs web api db
```

### Clean everything (volumes, images for this project)
```bash
npx @acme/fullstack-launcher clean --hard
```

### Update to latest template/images
```bash
npx @acme/fullstack-launcher update
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
     v           v           v           v           v
  Next.js      FastAPI     Postgres     Redis     (Nginx*)
  (web)         (api)        (db)        (cache)   optional
```

- **Images:**
  - `acme/web:TAG` (Next.js, Node 20-alpine)
  - `acme/api:TAG` (FastAPI, Python 3.12-slim)
  - `postgres:16` (official)
  - `redis:7` (official)
- **Compose:** One base `compose.yaml` plus `compose.dev.yaml` for live‑reload and host mounts.

---

## 4) Components & Responsibilities

- **CLI (`@acme/fullstack-launcher`)**
  - Bootstraps project from embedded templates.
  - Generates secrets (DB password, JWT secret) when absent.
  - Validates prerequisites (Docker, Node version, disk space, WSL check on Windows).
  - Ensures ports free (3000, 8000, 5432, 6379 by default) or selects alternatives.
  - Writes `.env` and `docker/.env` for compose.
  - Runs `docker compose` with appropriate profiles.
  - Waits for health checks; prints next steps.

- **Templates** (bundled in the npm package):
  - `packages/web` — Next.js App Router + Tailwind + shadcn.
  - `packages/api` — FastAPI + uvicorn + SQLAlchemy + Alembic.
  - `compose.yaml` & `compose.dev.yaml`.
  - `Makefile` helpers (optional).

- **Docker Images**
  - Built in CI and pushed to GHCR or Docker Hub.
  - Tagged by semantic version matching the CLI version (e.g., `1.2.0`).

---

## 5) CLI Specification (Node.js/TypeScript)

**Package name:** `@acme/fullstack-launcher`

**Entry:** `bin/acme-fullstack` (exposed as `acme` and invoked via `npx`).

**Commands**
- `up [dir] [--dev|--prod] [--detached] [--ports web=3000 api=8000 db=5432 redis=6379]` 
- `down` — stop & remove containers
- `logs [service...] [--since 1h] [--follow]`
- `status` — container states + health
- `clean [--hard]` — remove volumes/images scoped by project label
- `update` — refresh templates & pull latest tagged images
- `doctor` — diagnostic report for support

**Implementation Outline**

```ts
// src/index.ts
import { run } from './router';
run(process.argv);
```

```ts
// src/commands/up.ts
export async function up(args: UpArgs) {
  await assertPrereqs(); // docker, node, platform
  const ctx = await resolveProject(args.dir);
  await scaffoldIfMissing(ctx);
  await ensureEnvFiles(ctx); // writes .env, docker/.env
  await reservePorts(ctx);   // picks non-conflicting ports
  await writeComposeOverrides(ctx); // compose.dev.yaml if --dev
  await dockerComposeUp(ctx, { detached: args.detached });
  await waitForHealth(ctx, { timeoutMs: 120_000 });
  printEndpoints(ctx); // http://localhost:PORTs
}
```

**Key Libraries**
- `commander` (CLI parsing)
- `execa` (shelling out to `docker compose`)
- `fs-extra`, `yaml` (file ops)
- `ora`, `chalk` (UX)
- `which` (locating executables)

**Distribution**
- `type: module`, Node 18+
- Publish to npm with `files` whitelist to include only `/dist` and `/templates`.

---

## 6) Project Layout (Scaffold)

```
my-app/
├─ packages/
│  ├─ web/               # Next.js app (App Router)
│  └─ api/               # FastAPI app
├─ docker/
│  ├─ env.example        # example compose env
│  └─ .env               # generated (gitignored)
├─ compose.yaml
├─ compose.dev.yaml
├─ .env                  # app env (gitignored)
├─ Makefile              # optional helpers
└─ README.md
```

### packages/web (Next.js)
- Dev server in dev mode with bind mount `./packages/web:/app` + `node_modules` volume.
- Production build baked in `acme/web:TAG`.

### packages/api (FastAPI)
- `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` in dev.
- `gunicorn -k uvicorn.workers.UvicornWorker app.main:app` in prod.

---

## 7) Docker & Compose Strategy

### compose.yaml (base)
- Services: `web`, `api`, `db` (Postgres 16), `cache` (Redis 7), optional `nginx`.
- Networks: `internal` (private), `public` (for web if nginx included).
- Healthchecks:
  - `web`: `curl -f http://localhost:3000/api/health`
  - `api`: `curl -f http://localhost:8000/health`
  - `db`: `pg_isready -U $POSTGRES_USER`
  - `cache`: `redis-cli ping`
- Labels: `com.acme.project=<dir>` to scope cleanup.

### compose.dev.yaml (overrides)
- Binds local sources into containers for hot reload.
- Mounts `node_modules` and `.next` as named volumes to avoid host pollution.
- Uses `pip install -e .` or `uvicorn --reload` patterns for API.

### Images
- Prebuilt for quick start. For contributors, `docker buildx bake` can rebuild.

---

## 8) Environment & Secrets Management

- `.env` (app-level):
  - `NEXT_PUBLIC_API_URL=http://localhost:8000`
  - `JWT_SECRET=...` (generated)
- `docker/.env` (compose-level):
  - `POSTGRES_USER=acme`
  - `POSTGRES_PASSWORD=<generated>`
  - `POSTGRES_DB=acme`
  - `DB_URL=postgresql://acme:<pw>@db:5432/acme`
  - `REDIS_URL=redis://cache:6379/0`
- Generated by CLI on first run; never committed.

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
- Ports are configurable; defaults: `3000` (web), `8000` (api).

---

## 11) Update & Versioning Strategy

- **SemVer** aligned across CLI + images + templates: `MAJOR.MINOR.PATCH`.
- `update` command:
  1) Backs up user changes in `packages/*` (skip if modified files detected unless `--force`).
  2) Pulls new images matching CLI version.
  3) Optionally reapplies template diffs (3‑way merge via `git‑apply` if repo exists).

---

## 12) Telemetry (Opt‑In) & Diagnostics

- First run prompts: “Share anonymous usage to improve the tool? (y/N)”
- Data: command name, duration, OS, success/failure. No PII.
- `doctor` emits: Docker version, Compose version, platform, port usage, disk space, truncated logs.

---

## 13) Testing Strategy

- **Unit Tests (Jest):** CLI arg parsing, env generation, port allocator.
- **Integration (local docker):** Spin up with ephemeral project name, assert health.
- **E2E (GitHub Actions):** Matrix for macOS/Linux/Windows (with WSL), run `npx ... up`, poll health, run smoke tests (`/health`, DB insert).

---

## 14) Release Process (CI/CD)

- **Repo:** `acme/fullstack-launcher`
- **Pipelines:**
  1) Build & test CLI (tsc + jest).
  2) Build images `acme/web`, `acme/api`; push to GHCR with tag = package.json version.
  3) Publish npm on `git tag vX.Y.Z`.
  4) Create GitHub Release with changelog + compose templates.

---

## 15) Security Considerations

- Default credentials are randomly generated.
- Compose network is isolated; DB not published outside Docker network by default.
- CORS configured to allow `http://localhost:3000` in dev.
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

- Running `npx @acme/fullstack-launcher up my-app` on macOS/Windows/Linux:
  - scaffolds files, generates `.env`s
  - starts containers and reaches `healthy` within 2 minutes on a typical laptop
  - web is reachable at `http://localhost:<web_port>`; API at `/api/hello`; DB accepts connections.
- `down`, `logs`, `status`, `clean` behave as specified.

---

## 19) Future Extensions

- **brew tap** for `brew install acme-fullstack` wrapper around npm.
- **pip**-installable Python CLI that delegates to the Node CLI.
- **Cloud deploy** subcommand to push to Fly.io/Render/Vercel + Railway.
- **Profiles** for optional services (MinIO, n8n, Kafka).

---

## Appendix A — Example `compose.yaml` (excerpt)

```yaml
name: ${PROJECT_NAME:-acme}
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
    image: acme/api:${VERSION}
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
      - "${API_PORT:-8000}:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 5s
      timeout: 3s
      retries: 50

  web:
    image: acme/web:${VERSION}
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${API_PORT:-8000}
    depends_on:
      api:
        condition: service_healthy
    ports:
      - "${WEB_PORT:-3000}:3000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
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

```md
# My App

## Prereqs
- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Node.js 18+

## Run
```bash
npx @acme/fullstack-launcher up
```

Visit http://localhost:3000
```
