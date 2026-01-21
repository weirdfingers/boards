# CLI Revamp Testing Guide

This guide provides step-by-step instructions for performing the manual cross-platform testing documented in ticket CLI-6.5.

---

## Prerequisites

Before starting testing, ensure you have:

1. **Docker** installed and running
   - macOS: Docker Desktop
   - Linux: Docker Engine
   - Windows: Docker Desktop with WSL2 backend

2. **Node.js and npm** installed (v18 or higher recommended)

3. **Terminal access**
   - macOS: Terminal.app or iTerm2
   - Linux: Any terminal emulator
   - Windows: Windows Terminal with WSL

4. **Clean test environment**
   - Remove any previous test projects
   - Clear Docker containers/volumes from previous tests

---

## Testing Process

### Step 1: Initial Setup

1. **Verify Prerequisites:**
   ```bash
   # Check Docker
   docker --version
   docker ps

   # Check Node/npm
   node --version
   npm --version
   ```

2. **Clean Previous Tests:**
   ```bash
   # Remove any test projects
   rm -rf test-*

   # Clean Docker (optional, if needed)
   docker system prune -f
   ```

3. **Note System Information:**
   - OS version
   - Docker version
   - Node version
   - Architecture (x86_64, arm64, etc.)

### Step 2: Run Test Scenarios

Follow each test scenario in order. For each test:

1. Run the command exactly as shown
2. Observe the output
3. Record the result in the test report
4. Note any errors or unexpected behavior
5. Clean up before the next test (if needed)

---

## Test Scenarios Reference

### Scenario 1: Installation Test

**Purpose:** Verify the CLI can be installed and version displayed.

**Command:**
```bash
npx @weirdfingers/baseboards@latest --version
```

**Expected Output:**
```
[version number, e.g., 1.0.0]
```

**What to Check:**
- [ ] Version number displayed
- [ ] No errors or warnings
- [ ] Command exits cleanly

**Common Issues:**
- npm registry timeout: Check network
- Permission errors: Check npm permissions

---

### Scenario 2: Basic Scaffold Test

**Purpose:** Test default project scaffolding with full stack.

**Command:**
```bash
npx @weirdfingers/baseboards up test-default
```

**Expected Output:**
```
✓ Creating project directory
✓ Downloading template
✓ Starting services
  ✓ db
  ✓ redis
  ✓ api
  ✓ worker
  ✓ web
✓ All services healthy

Your Baseboards project is ready!
Web: http://localhost:3300
API: http://localhost:8800
```

**What to Check:**
- [ ] Project directory `test-default/` created
- [ ] 5 services started
- [ ] All health checks pass
- [ ] Web accessible at http://localhost:3300 (open in browser)
- [ ] API accessible at http://localhost:8800/graphql (open in browser)

**How to Verify:**
```bash
# Check services
docker ps | grep test-default

# Check web
curl http://localhost:3300

# Check API
curl http://localhost:8800/health
```

**Cleanup:**
```bash
npx @weirdfingers/baseboards down test-default --volumes
rm -rf test-default
```

---

### Scenario 3: Template Selection Test

**Purpose:** Test interactive and explicit template selection.

**Commands:**

**Part A: Interactive Selection**
```bash
npx @weirdfingers/baseboards up test-interactive
# When prompted, select "basic" template
```

**Part B: Explicit Template**
```bash
npx @weirdfingers/baseboards up test-basic --template basic
```

**What to Check:**
- [ ] Interactive prompt appears (Part A)
- [ ] Template list displayed
- [ ] Arrow keys work for selection
- [ ] Selected template downloaded
- [ ] Explicit template flag works (Part B)
- [ ] Services start correctly

**Cleanup:**
```bash
npx @weirdfingers/baseboards down test-interactive --volumes
npx @weirdfingers/baseboards down test-basic --volumes
rm -rf test-interactive test-basic
```

---

### Scenario 4: App-Dev Mode Test

**Purpose:** Test development mode with manual frontend.

**Command:**
```bash
npx @weirdfingers/baseboards up test-appdev --template basic --app-dev
# When prompted, select your preferred package manager (pnpm recommended)
```

**Expected Output:**
```
✓ Creating project directory
✓ Downloading template
✓ Installing frontend dependencies
✓ Starting backend services (4/4)
  ✓ db
  ✓ redis
  ✓ api
  ✓ worker

✨ App-dev mode: Backend services ready!

To start the frontend:
  cd test-appdev/web
  pnpm dev

API: http://localhost:8800
```

**What to Check:**
- [ ] Package manager prompt appears
- [ ] 4 services start (no web service)
- [ ] Dependencies installed in `test-appdev/web/node_modules`
- [ ] Instructions displayed
- [ ] Manual frontend start works

**Test Manual Frontend:**
```bash
cd test-appdev/web
pnpm dev
# Should start on port 3300
# Ctrl+C to stop
cd ../..
```

**Cleanup:**
```bash
npx @weirdfingers/baseboards down test-appdev --volumes
rm -rf test-appdev
```

---

### Scenario 5: Templates Command Test

**Purpose:** Test listing available templates.

**Command:**
```bash
npx @weirdfingers/baseboards templates
```

**Expected Output:**
```
Available Baseboards Templates:

basic
  A minimal template with core functionality

full (default)
  Full-featured template with all capabilities

[... other templates ...]
```

**What to Check:**
- [ ] Templates listed
- [ ] Descriptions shown
- [ ] No errors

---

### Scenario 6: Logs Command Test

**Purpose:** Test log viewing functionality.

**Setup:**
```bash
# First, start a project
npx @weirdfingers/baseboards up test-default
```

**Commands:**

**Part A: View All Logs**
```bash
npx @weirdfingers/baseboards logs test-default
```

**Part B: Follow Logs**
```bash
npx @weirdfingers/baseboards logs test-default -f
# Press Ctrl+C after a few seconds to stop
```

**Part C: Service-Specific Logs**
```bash
npx @weirdfingers/baseboards logs test-default api worker
```

**What to Check:**
- [ ] Logs displayed for all services (Part A)
- [ ] Follow mode streams real-time logs (Part B)
- [ ] Ctrl+C exits cleanly
- [ ] Service filtering works (Part C)

**Cleanup:**
```bash
npx @weirdfingers/baseboards down test-default --volumes
rm -rf test-default
```

---

### Scenario 7: Status Command Test

**Purpose:** Test status checking.

**Setup:**
```bash
npx @weirdfingers/baseboards up test-default
```

**Command:**
```bash
npx @weirdfingers/baseboards status test-default
```

**Expected Output:**
```
Project: test-default

Services:
✓ db       healthy
✓ redis    healthy
✓ api      healthy
✓ worker   healthy
✓ web      healthy
```

**What to Check:**
- [ ] All services listed
- [ ] Status shown (healthy/unhealthy)
- [ ] Accurate state information

**Test Unhealthy State (Optional):**
```bash
# Stop one service
docker stop test-default-api-1

# Check status
npx @weirdfingers/baseboards status test-default
# Should show api as unhealthy
```

**Cleanup:**
```bash
npx @weirdfingers/baseboards down test-default --volumes
rm -rf test-default
```

---

### Scenario 8: Down Command Test

**Purpose:** Test stopping services.

**Setup:**
```bash
npx @weirdfingers/baseboards up test-default
```

**Commands:**

**Part A: Stop Services (Preserve Volumes)**
```bash
npx @weirdfingers/baseboards down test-default

# Verify services stopped
docker ps | grep test-default
# Should return nothing

# Verify volumes preserved
docker volume ls | grep test-default
# Should show volumes
```

**Part B: Stop with Volumes**
```bash
# Start again
npx @weirdfingers/baseboards up test-default

# Stop with volumes
npx @weirdfingers/baseboards down test-default --volumes

# Verify volumes removed
docker volume ls | grep test-default
# Should return nothing
```

**What to Check:**
- [ ] Services stop cleanly
- [ ] Volumes preserved by default (Part A)
- [ ] `--volumes` flag removes volumes (Part B)

**Cleanup:**
```bash
rm -rf test-default
```

---

### Scenario 9: Clean Command Test

**Purpose:** Test project cleanup.

**Setup:**
```bash
npx @weirdfingers/baseboards up test-default
npx @weirdfingers/baseboards down test-default
```

**Commands:**

**Part A: Clean (Preserve Volumes)**
```bash
npx @weirdfingers/baseboards clean test-default

# Verify containers removed
docker ps -a | grep test-default
# Should return nothing

# Verify volumes preserved
docker volume ls | grep test-default
# Should show volumes
```

**Part B: Hard Clean**
```bash
# Setup again
npx @weirdfingers/baseboards up test-default
npx @weirdfingers/baseboards down test-default

# Hard clean
npx @weirdfingers/baseboards clean test-default --hard

# Verify everything removed
docker ps -a | grep test-default
docker volume ls | grep test-default
# Both should return nothing
```

**What to Check:**
- [ ] Containers removed
- [ ] Volumes preserved by default (Part A)
- [ ] `--hard` removes everything (Part B)

**Cleanup:**
```bash
rm -rf test-default
```

---

### Scenario 10: Doctor Command Test

**Purpose:** Test diagnostic functionality.

**Setup:**
```bash
npx @weirdfingers/baseboards up test-default
```

**Command:**
```bash
npx @weirdfingers/baseboards doctor test-default
```

**Expected Output:**
```
Running diagnostics for test-default...

Prerequisites:
✓ Docker installed
✓ Docker running
✓ Node.js installed

Services:
✓ db       healthy
✓ redis    healthy
✓ api      healthy
✓ worker   healthy
✓ web      healthy

Everything looks good! ✨
```

**What to Check:**
- [ ] Prerequisites checked
- [ ] Service status reported
- [ ] Helpful diagnostic output
- [ ] Actionable recommendations (if issues found)

**Test with Issue (Optional):**
```bash
# Stop Docker
# Run doctor again
npx @weirdfingers/baseboards doctor test-default
# Should detect Docker not running
```

**Cleanup:**
```bash
npx @weirdfingers/baseboards down test-default --volumes
rm -rf test-default
```

---

### Scenario 11: Cache Test

**Purpose:** Test template caching functionality.

**Commands:**

**Part A: First Run (Download)**
```bash
# Time the first run
time npx @weirdfingers/baseboards up test-cache-1 --template basic
# Note the time taken
```

**Part B: Second Run (Cache Hit)**
```bash
# Time the second run
time npx @weirdfingers/baseboards up test-cache-2 --template basic
# Should be noticeably faster
```

**Part C: Verify Cache**
```bash
# Check cache directory
ls ~/.baseboards/templates/
# Should show cached templates
```

**Part D: Clear Cache**
```bash
# Clear cache
npx @weirdfingers/baseboards templates --refresh

# Verify cache cleared
ls ~/.baseboards/templates/
# Should be empty or not exist

# Next run should download again
time npx @weirdfingers/baseboards up test-cache-3 --template basic
# Should be slower (like first run)
```

**What to Check:**
- [ ] First run downloads template (slower)
- [ ] Second run uses cache (faster)
- [ ] Cache directory exists
- [ ] `--refresh` clears cache
- [ ] Next run re-downloads

**Record Timings:**
- First run: _____ seconds
- Second run (cache): _____ seconds
- Speedup: _____x faster

**Cleanup:**
```bash
npx @weirdfingers/baseboards down test-cache-1 --volumes
npx @weirdfingers/baseboards down test-cache-2 --volumes
npx @weirdfingers/baseboards down test-cache-3 --volumes
rm -rf test-cache-*
```

---

### Scenario 12: Custom Ports Test

**Purpose:** Test custom port configuration.

**Command:**
```bash
npx @weirdfingers/baseboards up test-ports --ports "web=4000 api=9000"
```

**Expected Output:**
```
✓ Creating project directory
✓ Starting services with custom ports
✓ All services healthy

Your Baseboards project is ready!
Web: http://localhost:4000
API: http://localhost:9000
```

**What to Check:**
- [ ] Services start successfully
- [ ] Web accessible on port 4000 (not 3300)
- [ ] API accessible on port 9000 (not 8800)

**Verify:**
```bash
# Check web
curl http://localhost:4000
# Should work

# Check API
curl http://localhost:9000/health
# Should work

# Check default ports don't work
curl http://localhost:3300
curl http://localhost:8800
# Both should fail
```

**Cleanup:**
```bash
npx @weirdfingers/baseboards down test-ports --volumes
rm -rf test-ports
```

---

### Scenario 13: Error Handling Test

**Purpose:** Test error messages and handling.

**Part A: Invalid Template**
```bash
npx @weirdfingers/baseboards up test-error --template nonexistent
```

**Expected Output:**
```
✗ Error: Template 'nonexistent' not found

Available templates:
  - basic
  - full (default)
  [...]
```

**What to Check:**
- [ ] Clear error message
- [ ] Lists available templates
- [ ] Helpful suggestion

---

**Part B: Network Error**

```bash
# Disconnect network or disable Docker registry access
# Then run:
npx @weirdfingers/baseboards up test-network --template basic
```

**Expected Output:**
```
✗ Error: Failed to download template

This might be due to network issues.
Please check your internet connection and try again.
```

**What to Check:**
- [ ] Clear error message
- [ ] Suggests checking connection
- [ ] Graceful failure

**Note:** Reconnect network after this test!

---

**Part C: Port Conflict**

```bash
# Start a service on port 3300 first
python3 -m http.server 3300 &
PID=$!

# Try to start Baseboards
npx @weirdfingers/baseboards up test-conflict

# Kill the conflicting service
kill $PID
```

**Expected Output:**
```
✗ Error: Port 3300 is already in use

Another service is using port 3300.
Stop the other service or use a custom port:
  npx @weirdfingers/baseboards up test-conflict --ports "web=4000"
```

**What to Check:**
- [ ] Detects port conflict
- [ ] Clear error message
- [ ] Offers solution (custom port)

**Cleanup:**
```bash
rm -rf test-error test-network test-conflict
```

---

### Scenario 14: Upgrade Command Test

**Purpose:** Test upgrading projects to newer versions.

**Setup:**
```bash
# Create a project to upgrade
npx @weirdfingers/baseboards up test-upgrade
```

**Commands:**

**Part A: Check Current Version**
```bash
# View current version in docker/.env
cat test-upgrade/docker/.env | grep VERSION
```

**Part B: Dry Run Upgrade**
```bash
npx @weirdfingers/baseboards upgrade test-upgrade --dry-run
```

**Expected Output:**
```
📋 Upgrade Plan:

   Current version: X.X.X
   Target version:  Y.Y.Y
   Project mode:    default

   Steps:
   1. Stop all services
   2. Pull new backend images
   3. Update web/package.json
   4. Rebuild frontend Docker image
   5. Update docker/.env
   6. Start services
   7. Wait for health checks

🔍 Dry run complete - no changes made
```

**What to Check:**
- [ ] Current version detected correctly
- [ ] Target version shown (latest from npm)
- [ ] Project mode detected (default or app-dev)
- [ ] Upgrade steps listed
- [ ] No changes made in dry run

**Part C: Upgrade to Specific Version**
```bash
npx @weirdfingers/baseboards upgrade test-upgrade --version 0.9.0 --dry-run
```

**What to Check:**
- [ ] Specified version shown as target
- [ ] Compatibility warnings displayed (if any)

**Part D: Force Upgrade (skip confirmation)**
```bash
npx @weirdfingers/baseboards upgrade test-upgrade --force --dry-run
```

**What to Check:**
- [ ] No confirmation prompt shown
- [ ] Warning about --force flag displayed (if breaking changes)

**Part E: Already at Target Version**
```bash
# Get current version
CURRENT=$(cat test-upgrade/docker/.env | grep VERSION | cut -d= -f2)

# Try to upgrade to same version
npx @weirdfingers/baseboards upgrade test-upgrade --version $CURRENT
```

**Expected Output:**
```
✅ Already at vX.X.X
```

**What to Check:**
- [ ] Detects already at target version
- [ ] No upgrade performed
- [ ] Clean exit

**Part F: Invalid Project**
```bash
mkdir empty-dir
npx @weirdfingers/baseboards upgrade empty-dir
```

**Expected Output:**
```
❌ Error: Not a Baseboards project
   Run baseboards up to scaffold a project first.
```

**What to Check:**
- [ ] Detects non-Baseboards directory
- [ ] Helpful error message
- [ ] Suggests running `baseboards up`

**Cleanup:**
```bash
npx @weirdfingers/baseboards down test-upgrade --volumes
rm -rf test-upgrade empty-dir
```

---

## Performance Benchmarking

### Template Download Time

Measure the time for template operations:

```bash
# Cold cache (download)
rm -rf ~/.baseboards/templates
time npx @weirdfingers/baseboards up test-perf-1 --template basic
# Record time

# Warm cache (cached)
time npx @weirdfingers/baseboards up test-perf-2 --template basic
# Record time

# Calculate speedup
```

### Full Scaffold Time

Measure end-to-end scaffold time:

```bash
# Cold start (first time, pulls images)
docker system prune -af --volumes
time npx @weirdfingers/baseboards up test-perf-cold
# Record time from command start to "All services healthy"

# Warm start (images cached)
npx @weirdfingers/baseboards down test-perf-cold --volumes
time npx @weirdfingers/baseboards up test-perf-warm
# Record time
```

### Docker Image Pull Time

```bash
# Remove all images
docker rmi $(docker images -q)

# Measure pull time
time npx @weirdfingers/baseboards up test-perf-pull
# Note time spent pulling images (shown in output)
```

---

## Troubleshooting

### Common Issues

**npm install fails:**
```bash
# Clear npm cache
npm cache clean --force

# Try again
npx @weirdfingers/baseboards --version
```

**Docker not running:**
```bash
# Start Docker
# macOS: Open Docker Desktop
# Linux: sudo systemctl start docker
```

**Port conflicts:**
```bash
# Find what's using the port
lsof -i :3300

# Kill the process or use custom ports
```

**Permission errors (Linux):**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in
```

**Generator dependency errors (ModuleNotFoundError):**

If you see errors like `ModuleNotFoundError: No module named 'fal_client'` in worker logs:

```bash
# This indicates the Docker image lacks generator dependencies
# FIXED: As of 2026-01-20, the Dockerfile now includes all generator extras

# If testing with an older image, you can:
# 1. Build the updated image locally:
cd packages/backend
docker build -t boards-backend:local .

# 2. Update your project's compose.yaml to use the local image:
#    Change: ghcr.io/weirdfingers/boards-backend:latest
#    To: boards-backend:local

# 3. Restart services:
npx @weirdfingers/baseboards down your-project-name --volumes
npx @weirdfingers/baseboards up your-project-name
```

---

## Reporting Results

After completing all tests:

1. **Fill in the test report** (`design/cli-revamp-test-report.md`)
   - Update the platform matrix
   - Document all test results
   - Note any issues found
   - Record performance metrics

2. **Categorize issues** by severity:
   - **Blocker**: Prevents basic functionality
   - **Major**: Significant issue, workaround available
   - **Minor**: Small issue, doesn't impact core functionality

3. **Write recommendations**:
   - What works well
   - What needs improvement
   - Platform-specific notes

4. **Submit for review**

---

## Quick Reference: Cleanup Commands

Clean up all test projects:
```bash
# Stop all test projects
for proj in test-*; do
  npx @weirdfingers/baseboards down "$proj" --volumes 2>/dev/null
done

# Remove directories
rm -rf test-*

# Clean Docker (optional)
docker system prune -f
```

---

**End of Testing Guide**
