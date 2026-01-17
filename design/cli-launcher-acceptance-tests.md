# CLI Launcher Revamp — Acceptance Tests

**Purpose:** Manual verification tests to ensure the CLI revamp is working correctly before release.

**Prerequisites:**
- Clean testing environment (no existing Baseboards installations)
- Docker installed and running
- Node.js 20+ installed
- jq installed (`brew install jq`)
- Sufficient disk space (5+ GB for Docker images and templates)

**Testing machine requirements:**
- macOS (primary)
- Linux (secondary)
- Windows with WSL2 (if available)

---

## Table of Contents

1. [Template Installation Tests](#1-template-installation-tests)
2. [Development Mode Tests](#2-development-mode-tests)
3. [Template System Tests](#3-template-system-tests)
4. [Upgrade Tests](#4-upgrade-tests)
5. [Docker Image Tests](#5-docker-image-tests)
6. [Extension System Tests](#6-extension-system-tests)
7. [CLI Command Tests](#7-cli-command-tests)
8. [Error Handling Tests](#8-error-handling-tests)
9. [Performance Tests](#9-performance-tests)
10. [Documentation Verification](#10-documentation-verification)

---

## 1) Template Installation Tests

### Test 1.1: Baseboards Template - Default Mode

**Objective:** Verify that the full Baseboards template can be installed and runs correctly in default mode (pre-built Docker images).

**Steps:**

```bash
# 1. Create clean test directory
cd /tmp
rm -rf test-baseboards-default
mkdir test-baseboards-default
cd test-baseboards-default

# 2. Run CLI with baseboards template
npx @weirdfingers/baseboards@latest up . --template baseboards

# 3. Wait for completion (should take 3-5 minutes)
# Expected: All services start successfully
```

**Verification checklist:**

- [ ] Template downloaded successfully from GitHub releases
- [ ] All environment files generated (`.env` files in `api/`, `web/`, `docker/`)
- [ ] Docker services started: `db`, `cache`, `api`, `worker`, `web`
- [ ] All services show healthy status: `docker compose ps`
- [ ] Database migrations ran successfully (check logs: `docker compose logs api | grep migration`)
- [ ] API responds: `curl http://localhost:8800/health` returns `{"status":"ok"}`
- [ ] GraphQL playground accessible: Open `http://localhost:8800/graphql` in browser
- [ ] Frontend accessible: Open `http://localhost:3300` in browser
- [ ] Frontend shows Baseboards UI (not basic template)
- [ ] Can create a board via the UI
- [ ] No errors in browser console (F12)
- [ ] No errors in Docker logs: `docker compose logs --tail=100`

**Expected directory structure:**

```
test-baseboards-default/
├── web/                    # Full Baseboards frontend
├── config/
│   ├── generators.yaml
│   └── storage_config.yaml
├── extensions/
│   ├── generators/
│   └── plugins/
├── data/storage/
├── docker/.env
├── api/.env
├── web/.env
├── compose.yaml
├── compose.web.yaml
├── Dockerfile.web
└── README.md
```

**Cleanup:**

```bash
docker compose down --volumes
cd ..
rm -rf test-baseboards-default
```

**Pass criteria:** All checklist items verified, services running without errors, UI functional.

---

### Test 1.2: Basic Template - Default Mode

**Objective:** Verify that the minimal basic template can be installed and runs correctly in default mode.

**Steps:**

```bash
# 1. Create clean test directory
cd /tmp
rm -rf test-basic-default
mkdir test-basic-default
cd test-basic-default

# 2. Run CLI with basic template
npx @weirdfingers/baseboards@latest up . --template basic

# 3. Wait for completion
```

**Verification checklist:**

- [ ] Template downloaded successfully
- [ ] All environment files generated
- [ ] All Docker services started: `db`, `cache`, `api`, `worker`, `web`
- [ ] All services healthy: `docker compose ps`
- [ ] API responds: `curl http://localhost:8800/health`
- [ ] Frontend accessible: `http://localhost:3300`
- [ ] Frontend shows minimal UI (shadcn components, not full Baseboards)
- [ ] Can see "My Boards" heading
- [ ] Can create a board via "Create Board" button
- [ ] Board appears in the list after creation
- [ ] No errors in console or logs

**Expected differences from Baseboards template:**

- Simpler UI (no sidebar, no complex navigation)
- Fewer components in `web/src/components/`
- Smaller Docker image for web service (faster build)

**Cleanup:**

```bash
docker compose down --volumes
cd ..
rm -rf test-basic-default
```

**Pass criteria:** All checklist items verified, basic template is noticeably simpler than baseboards template.

---

### Test 1.3: Baseboards Template - App-Dev Mode

**Objective:** Verify that the Baseboards template works in app-dev mode (frontend runs locally, not in Docker).

**Steps:**

```bash
# 1. Create clean test directory
cd /tmp
rm -rf test-baseboards-appdev
mkdir test-baseboards-appdev
cd test-baseboards-appdev

# 2. Run CLI with app-dev flag
npx @weirdfingers/baseboards@latest up . --template baseboards --app-dev

# 3. Select package manager when prompted (choose pnpm)
# Expected: Backend services start, frontend instructions printed
```

**Verification checklist:**

- [ ] Template downloaded successfully
- [ ] Package manager selection prompt appeared
- [ ] Backend Docker services started: `db`, `cache`, `api`, `worker` (NO `web` service)
- [ ] Web service NOT in docker compose: `docker compose ps | grep web` returns nothing
- [ ] All backend services healthy
- [ ] API responds: `curl http://localhost:8800/health`
- [ ] CLI printed instructions for starting frontend locally
- [ ] Frontend dependencies installed in `web/node_modules/`

**Manual frontend startup:**

```bash
# 4. Start frontend locally
cd web
pnpm dev

# Expected: Next.js dev server starts on http://localhost:3000
```

**Frontend verification:**

- [ ] Frontend accessible at `http://localhost:3000` (not 3300)
- [ ] Baseboards UI loads correctly
- [ ] Hot reload works: Edit `web/src/app/page.tsx`, see changes instantly
- [ ] Can create and view boards
- [ ] GraphQL requests go to `http://localhost:8800/graphql`
- [ ] No CORS errors in console

**Cleanup:**

```bash
# Stop frontend (Ctrl+C)
cd ..
docker compose down --volumes
cd ..
rm -rf test-baseboards-appdev
```

**Pass criteria:** Backend runs in Docker, frontend runs locally with hot reload, full functionality works.

---

### Test 1.4: Basic Template - App-Dev Mode

**Objective:** Verify that the basic template works in app-dev mode.

**Steps:**

```bash
# 1. Create clean test directory
cd /tmp
rm -rf test-basic-appdev
mkdir test-basic-appdev
cd test-basic-appdev

# 2. Run CLI with app-dev flag
npx @weirdfingers/baseboards@latest up . --template basic --app-dev

# 3. Select package manager (choose npm)
```

**Verification checklist:**

- [ ] Template downloaded
- [ ] Package manager selection prompt (selected npm)
- [ ] Backend services started (no web)
- [ ] Instructions printed
- [ ] Frontend dependencies installed with npm

**Manual frontend startup:**

```bash
cd web
npm run dev
```

**Frontend verification:**

- [ ] Frontend starts at `http://localhost:3000`
- [ ] Basic template UI loads
- [ ] Hot reload works
- [ ] Full functionality works

**Cleanup:**

```bash
cd ..
docker compose down --volumes
cd ..
rm -rf test-basic-appdev
```

**Pass criteria:** Same as Test 1.3 but with basic template and npm.

---

## 2) Development Mode Tests

### Test 2.1: Dev-Packages Mode (Monorepo Only)

**Objective:** Verify that `--dev-packages` flag works correctly when running from the Boards monorepo.

**Prerequisites:** Must run from cloned Boards monorepo.

**Steps:**

```bash
# 1. Clone Boards monorepo (if not already)
cd /tmp
git clone https://github.com/weirdfingers/boards.git
cd boards
pnpm install

# 2. Create project with dev-packages
pnpm cli up /tmp/test-dev-packages --template basic --app-dev --dev-packages

# 3. Verify setup
cd /tmp/test-dev-packages
```

**Verification checklist:**

- [ ] CLI validated it's running from monorepo
- [ ] `frontend/` directory exists in project root
- [ ] `frontend/src/` contains @weirdfingers/boards source
- [ ] `frontend/package.json` exists and has name `@weirdfingers/boards`
- [ ] `web/package.json` references: `"@weirdfingers/boards": "file:../frontend"`
- [ ] Backend services started
- [ ] Frontend dependencies installed (including local package)

**Manual frontend startup:**

```bash
cd web
pnpm dev
```

**Hot reload verification:**

```bash
# 1. Edit package source
vim ../frontend/src/hooks/useBoards.ts
# Add a console.log or change something

# 2. Observe frontend in browser
# Expected: Changes hot-reload automatically
```

**Package development verification:**

- [ ] Changes to `frontend/src/` hot-reload in browser
- [ ] No build errors when editing package source
- [ ] TypeScript types work correctly in IDE
- [ ] Can test package changes before publishing

**Cleanup:**

```bash
cd /tmp/test-dev-packages
docker compose down --volumes
cd ..
rm -rf test-dev-packages
```

**Pass criteria:** Local package linked correctly, changes hot-reload, full development workflow works.

---

### Test 2.2: Dev-Packages Error Handling

**Objective:** Verify that `--dev-packages` fails gracefully when not in monorepo.

**Steps:**

```bash
# 1. Try to use --dev-packages from npm (not monorepo)
cd /tmp
npx @weirdfingers/baseboards@latest up test-fail --template basic --app-dev --dev-packages

# Expected: Error message explaining monorepo requirement
```

**Verification checklist:**

- [ ] CLI exits with error
- [ ] Error message explains: "requires running from within the Boards monorepo"
- [ ] Error message suggests cloning monorepo
- [ ] Error message is helpful and clear
- [ ] No partial project created

**Pass criteria:** Clear error message, no confusing state left behind.

---

### Test 2.3: Dev-Packages Without App-Dev

**Objective:** Verify that `--dev-packages` requires `--app-dev`.

**Steps:**

```bash
# From Boards monorepo
cd /tmp/boards
pnpm cli up /tmp/test-fail2 --template basic --dev-packages

# Expected: Error message
```

**Verification checklist:**

- [ ] CLI exits with error
- [ ] Error message: "--dev-packages requires --app-dev mode"
- [ ] Error explains why (Docker can't use local source)
- [ ] No project created

**Pass criteria:** Clear error, no partial state.

---

## 3) Template System Tests

### Test 3.1: Template Listing

**Objective:** Verify that `templates` command works correctly.

**Steps:**

```bash
# 1. List templates
npx @weirdfingers/baseboards@latest templates

# Expected: Shows available templates
```

**Verification checklist:**

- [ ] Command succeeds
- [ ] Shows "baseboards" template with description
- [ ] Shows "basic" template with description
- [ ] Displays framework info (Next.js)
- [ ] Displays features for each template
- [ ] Output is readable and well-formatted

**Pass criteria:** Templates listed clearly with descriptions.

---

### Test 3.2: Template Cache

**Objective:** Verify that template caching works correctly.

**Steps:**

```bash
# 1. Clear cache
rm -rf ~/.baseboards/templates/

# 2. First installation (downloads template)
cd /tmp
npx @weirdfingers/baseboards@latest up test-cache1 --template basic
cd test-cache1
docker compose down
cd ..

# 3. Second installation (uses cache)
time npx @weirdfingers/baseboards@latest up test-cache2 --template basic

# Expected: Second installation is faster (no download)
```

**Verification checklist:**

- [ ] Cache directory created: `~/.baseboards/templates/`
- [ ] Template tarball cached: `~/.baseboards/templates/template-basic-v*.tar.gz`
- [ ] Manifest cached: `~/.baseboards/templates/manifest-v*.json`
- [ ] Second installation skips download (shows "Using cached template")
- [ ] Second installation is noticeably faster
- [ ] Both installations work identically

**Cleanup:**

```bash
cd test-cache2 && docker compose down --volumes && cd ..
rm -rf test-cache1 test-cache2
```

**Pass criteria:** Caching works, speeds up subsequent installations.

---

### Test 3.3: Template Refresh

**Objective:** Verify that `--refresh` flag re-downloads templates.

**Steps:**

```bash
# 1. Install with cache
npx @weirdfingers/baseboards@latest up test-refresh --template basic

# 2. List templates with refresh
npx @weirdfingers/baseboards@latest templates --refresh

# Expected: Re-downloads manifest
```

**Verification checklist:**

- [ ] `--refresh` flag works
- [ ] Shows "Fetching latest templates..." message
- [ ] Re-downloads manifest even if cached
- [ ] Cache updated with new manifest

**Cleanup:**

```bash
cd test-refresh && docker compose down --volumes && cd ..
rm -rf test-refresh
```

**Pass criteria:** Refresh flag forces re-download.

---

## 4) Upgrade Tests

### Test 4.1: Upgrade Default Mode

**Objective:** Verify in-place upgrade for default mode installations.

**Prerequisites:** Requires two published CLI versions (e.g., 0.7.0 and 0.8.0).

**Steps:**

```bash
# 1. Install old version
cd /tmp
npx @weirdfingers/baseboards@0.7.0 up test-upgrade --template basic

# 2. Create some data (boards, generations)
# Open http://localhost:3300 and create boards

# 3. Upgrade to latest
npx @weirdfingers/baseboards@latest upgrade test-upgrade

# Expected: Services stop, images update, services restart
```

**Verification checklist:**

- [ ] CLI detected current version correctly
- [ ] Compatibility check ran
- [ ] Warning shown if breaking changes exist
- [ ] Services stopped gracefully
- [ ] New backend images pulled
- [ ] Web image rebuilt
- [ ] `docker/.env` updated with new version
- [ ] Services restarted successfully
- [ ] Database migrations ran automatically
- [ ] All services healthy after upgrade
- [ ] **Previous data preserved** (boards still exist)
- [ ] `data/storage/` contents preserved
- [ ] `config/` files preserved
- [ ] `extensions/` preserved
- [ ] Frontend works with new version

**Cleanup:**

```bash
cd test-upgrade && docker compose down --volumes && cd ..
rm -rf test-upgrade
```

**Pass criteria:** Upgrade succeeds, data preserved, no manual intervention required.

---

### Test 4.2: Upgrade App-Dev Mode

**Objective:** Verify upgrade for app-dev mode installations.

**Steps:**

```bash
# 1. Install old version with app-dev
cd /tmp
npx @weirdfingers/baseboards@0.7.0 up test-upgrade-appdev --template basic --app-dev

# 2. Upgrade
npx @weirdfingers/baseboards@latest upgrade test-upgrade-appdev

# Expected: Backend upgrades, frontend requires manual update
```

**Verification checklist:**

- [ ] CLI detected app-dev mode
- [ ] Backend services stopped and upgraded
- [ ] New backend images pulled
- [ ] Backend services restarted
- [ ] CLI printed manual frontend upgrade instructions
- [ ] Instructions show: `cd web && pnpm update @weirdfingers/boards@X.Y.Z`
- [ ] Instructions include link to release notes
- [ ] Backend healthy after upgrade
- [ ] Frontend still works with old package (backward compatible)

**Manual frontend upgrade:**

```bash
cd test-upgrade-appdev/web
pnpm update @weirdfingers/boards@latest
pnpm dev

# Verify frontend works with new version
```

**Cleanup:**

```bash
cd /tmp/test-upgrade-appdev
docker compose down --volumes
cd ..
rm -rf test-upgrade-appdev
```

**Pass criteria:** Backend upgrades automatically, frontend upgrade instructions clear.

---

### Test 4.3: Upgrade Dry Run

**Objective:** Verify `--dry-run` flag shows what would be upgraded without making changes.

**Steps:**

```bash
# 1. Install old version
cd /tmp
npx @weirdfingers/baseboards@0.7.0 up test-dryrun --template basic

# 2. Dry run upgrade
npx @weirdfingers/baseboards@latest upgrade test-dryrun --dry-run

# Expected: Shows plan but doesn't execute
```

**Verification checklist:**

- [ ] Shows current version
- [ ] Shows target version
- [ ] Lists breaking changes (if any)
- [ ] Shows which services would be updated
- [ ] Shows which images would be pulled
- [ ] No actual changes made
- [ ] Services still running old version
- [ ] `docker/.env` unchanged

**Cleanup:**

```bash
cd test-dryrun && docker compose down --volumes && cd ..
rm -rf test-dryrun
```

**Pass criteria:** Dry run informative, no actual changes made.

---

## 5) Docker Image Tests

### Test 5.1: Backend Image Verification

**Objective:** Verify that the published backend Docker image works correctly.

**Steps:**

```bash
# 1. Pull backend image
docker pull ghcr.io/weirdfingers/boards-backend:latest

# 2. Verify image exists
docker images | grep boards-backend

# 3. Check image metadata
docker inspect ghcr.io/weirdfingers/boards-backend:latest | jq '.[0].Config.Labels'
```

**Verification checklist:**

- [ ] Image pulls successfully from GHCR
- [ ] Image also available on Docker Hub: `docker pull weirdfingers/boards-backend:latest`
- [ ] Image has correct labels (version, description)
- [ ] Image architecture matches system (amd64 or arm64)
- [ ] Image size is reasonable (< 500MB)
- [ ] Image has health check configured
- [ ] Image runs as non-root user

**Run image directly:**

```bash
# Start PostgreSQL for testing
docker run -d --name test-db \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=test \
  postgres:16

# Start backend image
docker run -d --name test-api \
  --link test-db:db \
  -e BOARDS_DATABASE_URL=postgresql://test:test@db:5432/test \
  -p 8800:8800 \
  ghcr.io/weirdfingers/boards-backend:latest

# Wait for startup
sleep 10

# Test health endpoint
curl http://localhost:8800/health

# Expected: {"status":"ok"}
```

**Cleanup:**

```bash
docker stop test-api test-db
docker rm test-api test-db
```

**Pass criteria:** Image pulls, runs, and responds correctly.

---

### Test 5.2: Multi-Architecture Support

**Objective:** Verify that images work on both amd64 and arm64 (if available).

**Steps:**

```bash
# Check supported architectures
docker manifest inspect ghcr.io/weirdfingers/boards-backend:latest | jq '.manifests[].platform'

# Expected output:
# {
#   "architecture": "amd64",
#   "os": "linux"
# }
# {
#   "architecture": "arm64",
#   "os": "linux"
# }
```

**Verification checklist:**

- [ ] Both amd64 and arm64 manifests exist
- [ ] Image pulls correct architecture for host system
- [ ] Image runs correctly on native architecture

**If M1/M2 Mac available:**

```bash
# Verify arm64 image
docker pull --platform linux/arm64 ghcr.io/weirdfingers/boards-backend:latest
docker run --platform linux/arm64 --rm ghcr.io/weirdfingers/boards-backend:latest --version
```

**Pass criteria:** Both architectures available and functional.

---

## 6) Extension System Tests

### Test 6.1: Custom Generator Loading

**Objective:** Verify that custom generators can be loaded from `extensions/generators/`.

**Steps:**

```bash
# 1. Create project
cd /tmp
npx @weirdfingers/baseboards@latest up test-extensions --template basic

cd test-extensions

# 2. Create custom generator
mkdir -p extensions/generators/custom
cat > extensions/generators/custom/test_generator.py << 'EOF'
from boards.generators.base import BaseGenerator

class TestCustomGenerator(BaseGenerator):
    """Test custom generator."""

    def get_generator_info(self):
        return {
            "name": "test-custom",
            "description": "Test custom generator",
            "input_schema": {},
            "output_schema": {}
        }

    def generate(self, input_data):
        return {"message": "Custom generator works!"}
EOF

# 3. Update generators.yaml
cat >> config/generators.yaml << 'EOF'
  - class: "custom.test_generator.TestCustomGenerator"
    enabled: true
EOF

# 4. Restart services
docker compose restart api worker

# 5. Check if generator loaded
docker compose logs api | grep "test-custom"
```

**Verification checklist:**

- [ ] Custom generator file created
- [ ] `PYTHONPATH` includes `/app/extensions` in compose file
- [ ] Generator loaded without errors
- [ ] Generator appears in API logs
- [ ] Generator available in GraphQL schema
- [ ] Can query custom generator via GraphQL

**Cleanup:**

```bash
docker compose down --volumes
cd ..
rm -rf test-extensions
```

**Pass criteria:** Custom generator loads and functions correctly.

---

### Test 6.2: Extensions Directory Persistence

**Objective:** Verify that extensions persist across container restarts.

**Steps:**

```bash
# 1. Create project
cd /tmp
npx @weirdfingers/baseboards@latest up test-persist --template basic

cd test-persist

# 2. Add custom generator (as in Test 6.1)

# 3. Restart containers
docker compose down
docker compose up -d

# 4. Verify generator still works
docker compose logs api | grep "test-custom"
```

**Verification checklist:**

- [ ] Extensions directory preserved after `down`
- [ ] Custom generator still loads after restart
- [ ] No re-configuration needed

**Cleanup:**

```bash
docker compose down --volumes
cd ..
rm -rf test-persist
```

**Pass criteria:** Extensions survive restarts.

---

## 7) CLI Command Tests

### Test 7.1: Down Command

**Objective:** Verify that `down` command stops services correctly.

**Steps:**

```bash
# 1. Create and start project
cd /tmp
npx @weirdfingers/baseboards@latest up test-down --template basic

cd test-down

# 2. Verify running
docker compose ps

# 3. Stop services
npx @weirdfingers/baseboards@latest down .

# 4. Verify stopped
docker compose ps
```

**Verification checklist:**

- [ ] Command completes successfully
- [ ] All services stopped
- [ ] Containers removed
- [ ] Volumes preserved (data not lost)
- [ ] Networks removed

**Test with volumes flag:**

```bash
# Restart
npx @weirdfingers/baseboards@latest up . --no-scaffold

# Stop with volumes
npx @weirdfingers/baseboards@latest down . --volumes

# Verify volumes removed
docker volume ls | grep test-down
```

**Verification:**

- [ ] `--volumes` flag removes volumes
- [ ] Data actually deleted

**Cleanup:**

```bash
cd ..
rm -rf test-down
```

**Pass criteria:** Services stop cleanly, volumes behavior correct.

---

### Test 7.2: Logs Command

**Objective:** Verify that `logs` command works correctly.

**Steps:**

```bash
# 1. Create project
cd /tmp
npx @weirdfingers/baseboards@latest up test-logs --template basic

cd test-logs

# 2. View all logs
npx @weirdfingers/baseboards@latest logs .

# 3. View specific service
npx @weirdfingers/baseboards@latest logs . api

# 4. Follow logs
npx @weirdfingers/baseboards@latest logs . -f &
sleep 5
kill %1

# 5. Tail logs
npx @weirdfingers/baseboards@latest logs . --tail 20
```

**Verification checklist:**

- [ ] All logs command shows output from all services
- [ ] Single service logs work
- [ ] `-f` flag follows logs (streams)
- [ ] `--tail` limits output
- [ ] Logs are readable and formatted
- [ ] Timestamps included

**Cleanup:**

```bash
docker compose down --volumes
cd ..
rm -rf test-logs
```

**Pass criteria:** All log options work correctly.

---

### Test 7.3: Status Command

**Objective:** Verify that `status` command shows service health.

**Steps:**

```bash
# 1. Create project
cd /tmp
npx @weirdfingers/baseboards@latest up test-status --template basic

cd test-status

# 2. Check status
npx @weirdfingers/baseboards@latest status .
```

**Verification checklist:**

- [ ] Shows all services
- [ ] Shows health status (healthy/unhealthy)
- [ ] Shows ports
- [ ] Shows uptime
- [ ] Output is well-formatted
- [ ] All services show as healthy

**Test with stopped services:**

```bash
docker compose stop api

# Check status
npx @weirdfingers/baseboards@latest status .
```

**Verification:**

- [ ] Shows `api` as stopped
- [ ] Shows other services still healthy
- [ ] Indicates which services are down

**Cleanup:**

```bash
docker compose down --volumes
cd ..
rm -rf test-status
```

**Pass criteria:** Status accurately reflects service states.

---

### Test 7.4: Clean Command

**Objective:** Verify that `clean` command removes containers and optionally volumes.

**Steps:**

```bash
# 1. Create project
cd /tmp
npx @weirdfingers/baseboards@latest up test-clean --template basic

cd test-clean

# 2. Stop services
docker compose down

# 3. Clean (no --hard)
npx @weirdfingers/baseboards@latest clean .

# Verify
docker volume ls | grep test-clean
```

**Verification checklist:**

- [ ] Containers removed
- [ ] Images cleaned up
- [ ] Volumes preserved

**Test with --hard:**

```bash
# Restart
npx @weirdfingers/baseboards@latest up . --no-scaffold

# Clean with --hard
npx @weirdfingers/baseboards@latest clean . --hard

# Verify volumes removed
docker volume ls | grep test-clean
```

**Verification:**

- [ ] `--hard` removes volumes
- [ ] All data deleted

**Cleanup:**

```bash
cd ..
rm -rf test-clean
```

**Pass criteria:** Clean command removes appropriate resources.

---

### Test 7.5: Doctor Command

**Objective:** Verify that `doctor` command diagnoses issues.

**Steps:**

```bash
# 1. Create project
cd /tmp
npx @weirdfingers/baseboards@latest up test-doctor --template basic

cd test-doctor

# 2. Run doctor
npx @weirdfingers/baseboards@latest doctor .
```

**Verification checklist:**

- [ ] Checks Docker is running
- [ ] Checks Docker version
- [ ] Checks available disk space
- [ ] Checks port availability
- [ ] Checks service health
- [ ] Shows clear diagnostics
- [ ] Provides actionable recommendations if issues found

**Test with broken state:**

```bash
# Stop a service
docker compose stop db

# Run doctor
npx @weirdfingers/baseboards@latest doctor .
```

**Verification:**

- [ ] Detects database is down
- [ ] Suggests remediation steps

**Cleanup:**

```bash
docker compose down --volumes
cd ..
rm -rf test-doctor
```

**Pass criteria:** Doctor provides useful diagnostics.

---

## 8) Error Handling Tests

### Test 8.1: Port Conflict Handling

**Objective:** Verify graceful handling when ports are already in use.

**Steps:**

```bash
# 1. Start a service on port 8800
python3 -m http.server 8800 &
PID=$!

# 2. Try to create project
cd /tmp
npx @weirdfingers/baseboards@latest up test-port-conflict --template basic

# Expected: Error about port conflict
```

**Verification checklist:**

- [ ] CLI detects port conflict
- [ ] Error message is clear
- [ ] Suggests using `--ports` flag
- [ ] No partial project created

**Cleanup:**

```bash
kill $PID
rm -rf test-port-conflict
```

**Pass criteria:** Clear error, helpful guidance.

---

### Test 8.2: Insufficient Disk Space

**Objective:** Verify handling when disk space is low.

**Steps:**

```bash
# Check disk space
df -h

# If < 5GB available, test will show warning
cd /tmp
npx @weirdfingers/baseboards@latest up test-disk --template baseboards
```

**Verification checklist:**

- [ ] CLI warns if disk space low
- [ ] Allows user to continue or abort
- [ ] Doesn't fail silently

**Cleanup:**

```bash
cd test-disk && docker compose down --volumes && cd ..
rm -rf test-disk
```

**Pass criteria:** Disk space checked, warnings shown.

---

### Test 8.3: Missing Docker

**Objective:** Verify handling when Docker is not running.

**Steps:**

```bash
# 1. Stop Docker
# (On Mac: Quit Docker Desktop)

# 2. Try to run CLI
npx @weirdfingers/baseboards@latest up test-no-docker --template basic

# Expected: Clear error about Docker not running
```

**Verification checklist:**

- [ ] CLI detects Docker is not running
- [ ] Error message is clear and helpful
- [ ] Suggests starting Docker
- [ ] No confusing errors

**Cleanup:**

```bash
# Start Docker again
```

**Pass criteria:** Clear error, actionable guidance.

---

### Test 8.4: Invalid Template Name

**Objective:** Verify handling of invalid template names.

**Steps:**

```bash
cd /tmp
npx @weirdfingers/baseboards@latest up test-invalid --template nonexistent

# Expected: Error listing available templates
```

**Verification checklist:**

- [ ] CLI detects invalid template name
- [ ] Error lists available templates
- [ ] Suggests correct template names
- [ ] No project created

**Pass criteria:** Clear error, helpful suggestions.

---

## 9) Performance Tests

### Test 9.1: Cold Start Time

**Objective:** Measure time from command to ready state (no cache).

**Steps:**

```bash
# Clear cache
rm -rf ~/.baseboards/templates/

# Measure time
cd /tmp
time npx @weirdfingers/baseboards@latest up test-perf-cold --template basic --attach
```

**Acceptance criteria:**

- [ ] **Total time < 5 minutes** (on reasonable hardware)
- [ ] Template download < 30 seconds
- [ ] Image pulls < 2 minutes
- [ ] Service startup < 2 minutes
- [ ] Migrations < 30 seconds

**Cleanup:**

```bash
cd test-perf-cold && docker compose down --volumes && cd ..
rm -rf test-perf-cold
```

**Pass criteria:** Completes within acceptable time.

---

### Test 9.2: Warm Start Time (Cached)

**Objective:** Measure time with cached templates and pulled images.

**Steps:**

```bash
# Ensure cache exists from previous test
cd /tmp
time npx @weirdfingers/baseboards@latest up test-perf-warm --template basic --attach
```

**Acceptance criteria:**

- [ ] **Total time < 3 minutes**
- [ ] Template extracted from cache < 5 seconds
- [ ] No image pulls (already cached)
- [ ] Service startup < 2 minutes

**Cleanup:**

```bash
cd test-perf-warm && docker compose down --volumes && cd ..
rm -rf test-perf-warm
```

**Pass criteria:** Significantly faster than cold start.

---

### Test 9.3: Upgrade Time

**Objective:** Measure time for in-place upgrade.

**Steps:**

```bash
# Install old version
cd /tmp
npx @weirdfingers/baseboards@0.7.0 up test-perf-upgrade --template basic

# Measure upgrade
cd test-perf-upgrade
time npx @weirdfingers/baseboards@latest upgrade .
```

**Acceptance criteria:**

- [ ] **Upgrade time < 3 minutes**
- [ ] Downtime < 1 minute (services stopped to restarted)
- [ ] No data loss

**Cleanup:**

```bash
docker compose down --volumes
cd ..
rm -rf test-perf-upgrade
```

**Pass criteria:** Fast upgrade, minimal downtime.

---

## 10) Documentation Verification

### Test 10.1: README Accuracy

**Objective:** Verify that generated README matches actual setup.

**Steps:**

```bash
cd /tmp
npx @weirdfingers/baseboards@latest up test-readme --template basic

cd test-readme
cat README.md
```

**Verification checklist:**

- [ ] README exists
- [ ] README mentions correct ports
- [ ] README has correct startup commands
- [ ] README explains directory structure
- [ ] README includes links to docs
- [ ] README is well-formatted

**Pass criteria:** README is accurate and helpful.

---

### Test 10.2: Help Output

**Objective:** Verify CLI help text is accurate.

**Steps:**

```bash
# Main help
npx @weirdfingers/baseboards@latest --help

# Command help
npx @weirdfingers/baseboards@latest up --help
npx @weirdfingers/baseboards@latest upgrade --help
npx @weirdfingers/baseboards@latest templates --help
```

**Verification checklist:**

- [ ] All commands listed
- [ ] Flags documented
- [ ] Examples provided
- [ ] Help text matches actual behavior
- [ ] No outdated flag references (no `--dev`, `--prod`)

**Pass criteria:** Help is comprehensive and accurate.

---

## Test Execution Checklist

Use this checklist to track test execution:

### Template Installation Tests
- [ ] Test 1.1: Baseboards Template - Default Mode
- [ ] Test 1.2: Basic Template - Default Mode
- [ ] Test 1.3: Baseboards Template - App-Dev Mode
- [ ] Test 1.4: Basic Template - App-Dev Mode

### Development Mode Tests
- [ ] Test 2.1: Dev-Packages Mode
- [ ] Test 2.2: Dev-Packages Error Handling
- [ ] Test 2.3: Dev-Packages Without App-Dev

### Template System Tests
- [ ] Test 3.1: Template Listing
- [ ] Test 3.2: Template Cache
- [ ] Test 3.3: Template Refresh

### Upgrade Tests
- [ ] Test 4.1: Upgrade Default Mode
- [ ] Test 4.2: Upgrade App-Dev Mode
- [ ] Test 4.3: Upgrade Dry Run

### Docker Image Tests
- [ ] Test 5.1: Backend Image Verification
- [ ] Test 5.2: Multi-Architecture Support

### Extension System Tests
- [ ] Test 6.1: Custom Generator Loading
- [ ] Test 6.2: Extensions Directory Persistence

### CLI Command Tests
- [ ] Test 7.1: Down Command
- [ ] Test 7.2: Logs Command
- [ ] Test 7.3: Status Command
- [ ] Test 7.4: Clean Command
- [ ] Test 7.5: Doctor Command

### Error Handling Tests
- [ ] Test 8.1: Port Conflict Handling
- [ ] Test 8.2: Insufficient Disk Space
- [ ] Test 8.3: Missing Docker
- [ ] Test 8.4: Invalid Template Name

### Performance Tests
- [ ] Test 9.1: Cold Start Time
- [ ] Test 9.2: Warm Start Time
- [ ] Test 9.3: Upgrade Time

### Documentation Tests
- [ ] Test 10.1: README Accuracy
- [ ] Test 10.2: Help Output

---

## Pass/Fail Summary

**Test execution date:** _______________

**Tester:** _______________

**Environment:** macOS / Linux / Windows WSL2

**Total tests:** 33

**Passed:** ___ / 33

**Failed:** ___ / 33

**Blockers:** (list critical failures that prevent release)

---

## Notes and Observations

(Use this section for additional notes, edge cases discovered, or suggestions for improvement)

---

## Sign-off

- [ ] All critical tests passed
- [ ] No blocking issues
- [ ] Documentation updated
- [ ] Ready for release

**Signed:** _______________ **Date:** _______________
