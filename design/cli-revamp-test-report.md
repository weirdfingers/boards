# CLI Revamp Cross-Platform Testing Report

**Test Date:** [YYYY-MM-DD]
**Tester:** [Your Name]
**CLI Version:** [Version from package.json]
**Report Status:** 🚧 IN PROGRESS

---

## Executive Summary

**Overall Status:** 🔄 Testing in progress

**Platforms Tested:**
- [ ] macOS Intel (x86_64)
- [ ] macOS Apple Silicon (arm64)
- [ ] Linux Ubuntu 22.04 (amd64)
- [ ] Linux Debian 12 (amd64)
- [ ] Windows 11 WSL2 Ubuntu (amd64)

**Key Findings:**
- [Summary of critical issues found]
- [Summary of performance observations]
- [Summary of platform-specific quirks]

---

## Platform Matrix

| Scenario | macOS Intel | macOS ARM | Ubuntu 22.04 | Debian 12 | Win WSL2 | Notes |
|----------|-------------|-----------|--------------|-----------|----------|-------|
| 1. Installation | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 2. Basic Scaffold | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 3. Template Selection | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 4. App-Dev Mode | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 5. Templates Command | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 6. Logs Command | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 7. Status Command | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 8. Down Command | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 9. Clean Command | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 10. Doctor Command | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 11. Cache Test | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 12. Custom Ports | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |
| 13. Error Handling | ⏸️ | ⏸️ | ⏸️ | ⏸️ | ⏸️ | |

**Legend:**
- ⏸️ Not Started
- 🔄 In Progress
- ✅ Pass
- ❌ Fail
- ⚠️ Pass with Issues

---

## Test Environment Details

### macOS Intel (x86_64)

**System Information:**
- OS Version: [e.g., macOS 14.2 Sonoma]
- Docker Desktop Version: [e.g., 4.25.0]
- Node Version: [e.g., v20.10.0]
- Architecture: x86_64

**Prerequisites:**
- [ ] Docker Desktop installed and running
- [ ] Node.js/npm installed
- [ ] Terminal application: [e.g., Terminal.app, iTerm2]

**Test Results:** [See detailed results below]

---

### macOS Apple Silicon (arm64)

**System Information:**
- OS Version: [e.g., macOS 14.2 Sonoma]
- Docker Desktop Version: [e.g., 4.25.0]
- Node Version: [e.g., v20.10.0]
- Architecture: arm64
- Chip: [e.g., M1, M2, M3]

**Prerequisites:**
- [ ] Docker Desktop installed and running
- [ ] Node.js/npm installed
- [ ] Terminal application: [e.g., Terminal.app, iTerm2]
- [ ] Rosetta 2: Not Required ✅

**Test Results:** [See detailed results below]

---

### Linux Ubuntu 22.04 (amd64)

**System Information:**
- Distribution: Ubuntu 22.04 LTS
- Kernel Version: [e.g., 5.15.0-91-generic]
- Docker Version: [e.g., 24.0.7]
- Node Version: [e.g., v20.10.0]
- Architecture: amd64

**Prerequisites:**
- [ ] Docker Engine installed and running
- [ ] User in docker group (no sudo required)
- [ ] Node.js/npm installed
- [ ] Terminal: [e.g., gnome-terminal]
- [ ] SELinux/AppArmor: [enabled/disabled]

**Test Results:** [See detailed results below]

---

### Linux Debian 12 (amd64)

**System Information:**
- Distribution: Debian 12 (Bookworm)
- Kernel Version: [e.g., 6.1.0-17-amd64]
- Docker Version: [e.g., 24.0.7]
- Node Version: [e.g., v20.10.0]
- Architecture: amd64

**Prerequisites:**
- [ ] Docker Engine installed and running
- [ ] User in docker group (no sudo required)
- [ ] Node.js/npm installed
- [ ] Terminal: [e.g., xterm, konsole]
- [ ] SELinux/AppArmor: [enabled/disabled]

**Test Results:** [See detailed results below]

---

### Windows 11 WSL2 Ubuntu (amd64)

**System Information:**
- Windows Version: Windows 11 [Build number]
- WSL Version: WSL 2
- Distribution: Ubuntu [version]
- Docker Desktop Version: [e.g., 4.25.0] with WSL2 backend
- Node Version: [e.g., v20.10.0]
- Architecture: amd64

**Prerequisites:**
- [ ] WSL2 installed and configured
- [ ] Docker Desktop with WSL2 backend enabled
- [ ] Node.js/npm installed in WSL
- [ ] Windows Terminal or alternative

**Test Results:** [See detailed results below]

---

## Detailed Test Results

### Test Scenario 1: Installation

**Command:**
```bash
npx @weirdfingers/baseboards@latest --version
```

**Expected Result:**
- Version number displayed (e.g., `1.0.0`)
- No errors or warnings
- Clean exit

#### macOS Intel
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

---

### Test Scenario 2: Basic Scaffold

**Command:**
```bash
npx @weirdfingers/baseboards up test-default
```

**Expected Result:**
- Project directory created
- 5 services started (web, api, worker, db, redis)
- All health checks pass
- Web accessible at http://localhost:3300
- API accessible at http://localhost:8800

#### macOS Intel
- **Status:** ⏸️
- **Project Created:**
- **Services Started:**
- **Health Checks:**
- **Web Accessible:**
- **API Accessible:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Project Created:**
- **Services Started:**
- **Health Checks:**
- **Web Accessible:**
- **API Accessible:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Project Created:**
- **Services Started:**
- **Health Checks:**
- **Web Accessible:**
- **API Accessible:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Project Created:**
- **Services Started:**
- **Health Checks:**
- **Web Accessible:**
- **API Accessible:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Project Created:**
- **Services Started:**
- **Health Checks:**
- **Web Accessible:**
- **API Accessible:**
- **Issues:**
- **Notes:**

---

### Test Scenario 3: Template Selection

**Commands:**
```bash
# Interactive selection
npx @weirdfingers/baseboards up test-interactive
# (Select basic template when prompted)

# Explicit template
npx @weirdfingers/baseboards up test-basic --template basic
```

**Expected Result:**
- Interactive prompt works correctly
- Template downloads successfully
- Correct template used
- Services start properly

#### macOS Intel
- **Status:** ⏸️
- **Interactive Prompt:**
- **Template Download:**
- **Correct Template:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Interactive Prompt:**
- **Template Download:**
- **Correct Template:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Interactive Prompt:**
- **Template Download:**
- **Correct Template:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Interactive Prompt:**
- **Template Download:**
- **Correct Template:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Interactive Prompt:**
- **Template Download:**
- **Correct Template:**
- **Issues:**
- **Notes:**

---

### Test Scenario 4: App-Dev Mode

**Command:**
```bash
npx @weirdfingers/baseboards up test-appdev --template basic --app-dev
```

**Expected Result:**
- Package manager selection prompt appears
- 4 services start (api, worker, db, redis - no web)
- Dependencies install correctly
- Instructions displayed for manual frontend startup
- Can start frontend manually: `cd test-appdev/web && pnpm dev`

#### macOS Intel
- **Status:** ⏸️
- **Package Manager Prompt:**
- **4 Services Started:**
- **Dependencies Installed:**
- **Instructions Shown:**
- **Manual Frontend Start:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Package Manager Prompt:**
- **4 Services Started:**
- **Dependencies Installed:**
- **Instructions Shown:**
- **Manual Frontend Start:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Package Manager Prompt:**
- **4 Services Started:**
- **Dependencies Installed:**
- **Instructions Shown:**
- **Manual Frontend Start:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Package Manager Prompt:**
- **4 Services Started:**
- **Dependencies Installed:**
- **Instructions Shown:**
- **Manual Frontend Start:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Package Manager Prompt:**
- **4 Services Started:**
- **Dependencies Installed:**
- **Instructions Shown:**
- **Manual Frontend Start:**
- **Issues:**
- **Notes:**

---

### Test Scenario 5: Templates Command

**Command:**
```bash
npx @weirdfingers/baseboards templates
```

**Expected Result:**
- List of available templates displayed
- Template descriptions shown
- No errors

#### macOS Intel
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

---

### Test Scenario 6: Logs Command

**Commands:**
```bash
# View logs
npx @weirdfingers/baseboards logs test-default

# Follow logs
npx @weirdfingers/baseboards logs test-default -f
# (Press Ctrl+C to stop)

# Service-specific logs
npx @weirdfingers/baseboards logs test-default api worker
```

**Expected Result:**
- Logs displayed correctly
- Follow mode streams logs in real-time
- Ctrl+C exits cleanly
- Service filtering works

#### macOS Intel
- **Status:** ⏸️
- **Logs Displayed:**
- **Follow Mode:**
- **Clean Exit:**
- **Service Filter:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Logs Displayed:**
- **Follow Mode:**
- **Clean Exit:**
- **Service Filter:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Logs Displayed:**
- **Follow Mode:**
- **Clean Exit:**
- **Service Filter:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Logs Displayed:**
- **Follow Mode:**
- **Clean Exit:**
- **Service Filter:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Logs Displayed:**
- **Follow Mode:**
- **Clean Exit:**
- **Service Filter:**
- **Issues:**
- **Notes:**

---

### Test Scenario 7: Status Command

**Command:**
```bash
npx @weirdfingers/baseboards status test-default
```

**Expected Result:**
- All services listed
- Status shown (healthy/unhealthy)
- Accurate state information

#### macOS Intel
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

---

### Test Scenario 8: Down Command

**Commands:**
```bash
# Stop services (preserve volumes)
npx @weirdfingers/baseboards down test-default

# Stop with volumes
npx @weirdfingers/baseboards down test-default --volumes
```

**Expected Result:**
- Services stop cleanly
- Volumes preserved by default
- `--volumes` flag removes volumes

#### macOS Intel
- **Status:** ⏸️
- **Services Stopped:**
- **Volumes Preserved:**
- **Volumes Deleted (with flag):**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Services Stopped:**
- **Volumes Preserved:**
- **Volumes Deleted (with flag):**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Services Stopped:**
- **Volumes Preserved:**
- **Volumes Deleted (with flag):**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Services Stopped:**
- **Volumes Preserved:**
- **Volumes Deleted (with flag):**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Services Stopped:**
- **Volumes Preserved:**
- **Volumes Deleted (with flag):**
- **Issues:**
- **Notes:**

---

### Test Scenario 9: Clean Command

**Commands:**
```bash
# Clean project (preserve volumes)
npx @weirdfingers/baseboards clean test-default

# Hard clean (remove everything)
npx @weirdfingers/baseboards clean test-default --hard
```

**Expected Result:**
- Containers removed
- Volumes preserved by default
- `--hard` removes everything including volumes

#### macOS Intel
- **Status:** ⏸️
- **Containers Removed:**
- **Volumes Preserved:**
- **Hard Clean Works:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Containers Removed:**
- **Volumes Preserved:**
- **Hard Clean Works:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Containers Removed:**
- **Volumes Preserved:**
- **Hard Clean Works:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Containers Removed:**
- **Volumes Preserved:**
- **Hard Clean Works:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Containers Removed:**
- **Volumes Preserved:**
- **Hard Clean Works:**
- **Issues:**
- **Notes:**

---

### Test Scenario 10: Doctor Command

**Command:**
```bash
npx @weirdfingers/baseboards doctor test-default
```

**Expected Result:**
- Prerequisites checked (Docker, Node, etc.)
- Service status reported
- Helpful diagnostic output
- Actionable recommendations if issues found

#### macOS Intel
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Result:**
- **Issues:**
- **Notes:**

---

### Test Scenario 11: Cache Test

**Commands:**
```bash
# First scaffold (downloads template)
npx @weirdfingers/baseboards up test-cache-1 --template basic

# Second scaffold (uses cache)
npx @weirdfingers/baseboards up test-cache-2 --template basic

# Clear cache
npx @weirdfingers/baseboards templates --refresh
```

**Expected Result:**
- First run downloads template (slower)
- Second run uses cache (faster)
- Cache directory exists: `~/.baseboards/templates/`
- `--refresh` clears cache
- Next run re-downloads

#### macOS Intel
- **Status:** ⏸️
- **First Run Time:**
- **Second Run Time:**
- **Cache Hit:**
- **Cache Location:**
- **Refresh Works:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **First Run Time:**
- **Second Run Time:**
- **Cache Hit:**
- **Cache Location:**
- **Refresh Works:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **First Run Time:**
- **Second Run Time:**
- **Cache Hit:**
- **Cache Location:**
- **Refresh Works:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **First Run Time:**
- **Second Run Time:**
- **Cache Hit:**
- **Cache Location:**
- **Refresh Works:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **First Run Time:**
- **Second Run Time:**
- **Cache Hit:**
- **Cache Location:**
- **Refresh Works:**
- **Issues:**
- **Notes:**

---

### Test Scenario 12: Custom Ports

**Command:**
```bash
npx @weirdfingers/baseboards up test-ports --ports "web=4000 api=9000"
```

**Expected Result:**
- Services start on custom ports
- Web accessible on port 4000
- API accessible on port 9000
- Other services on default ports

#### macOS Intel
- **Status:** ⏸️
- **Web on 4000:**
- **API on 9000:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Web on 4000:**
- **API on 9000:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Web on 4000:**
- **API on 9000:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Web on 4000:**
- **API on 9000:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Web on 4000:**
- **API on 9000:**
- **Issues:**
- **Notes:**

---

### Test Scenario 13: Error Handling

**Commands:**
```bash
# Invalid template
npx @weirdfingers/baseboards up test-error --template nonexistent

# Network error (test with network disconnected)
npx @weirdfingers/baseboards up test-network --template basic

# Port conflict (start service on port 3300 first)
npx @weirdfingers/baseboards up test-conflict
```

**Expected Result:**
- Invalid template: Clear error, lists available templates
- Network error: Clear error, suggests checking connection
- Port conflict: Detects conflict, offers alternative or clear error

#### macOS Intel
- **Status:** ⏸️
- **Invalid Template Error:**
- **Network Error:**
- **Port Conflict Error:**
- **Issues:**
- **Notes:**

#### macOS ARM
- **Status:** ⏸️
- **Invalid Template Error:**
- **Network Error:**
- **Port Conflict Error:**
- **Issues:**
- **Notes:**

#### Ubuntu 22.04
- **Status:** ⏸️
- **Invalid Template Error:**
- **Network Error:**
- **Port Conflict Error:**
- **Issues:**
- **Notes:**

#### Debian 12
- **Status:** ⏸️
- **Invalid Template Error:**
- **Network Error:**
- **Port Conflict Error:**
- **Issues:**
- **Notes:**

#### Windows WSL2
- **Status:** ⏸️
- **Invalid Template Error:**
- **Network Error:**
- **Port Conflict Error:**
- **Issues:**
- **Notes:**

---

## Performance Benchmarks

### Template Download Performance

| Platform | First Run (download) | Cache Hit (second run) | Speedup |
|----------|----------------------|------------------------|---------|
| macOS Intel | | | |
| macOS ARM | | | |
| Ubuntu 22.04 | | | |
| Debian 12 | | | |
| Windows WSL2 | | | |

### Scaffold to Running Performance

Time from `npx @weirdfingers/baseboards up` to all services healthy:

| Platform | Cold Start (first time) | Warm Start (images cached) |
|----------|-------------------------|----------------------------|
| macOS Intel | | |
| macOS ARM | | |
| Ubuntu 22.04 | | |
| Debian 12 | | |
| Windows WSL2 | | |

### Docker Image Pull Performance

Time to pull Docker images on first run:

| Platform | Time to Pull Images | Notes |
|----------|---------------------|-------|
| macOS Intel | | |
| macOS ARM | | |
| Ubuntu 22.04 | | |
| Debian 12 | | |
| Windows WSL2 | | |

---

## Issues Found

### Critical Issues (Blockers)

**None found** ✅

---

### Major Issues

**None found** ✅

---

### Minor Issues

**None found** ✅

---

## Platform-Specific Notes

### macOS Intel

**Quirks:**
- [Any platform-specific behaviors]

**Warnings:**
- [Any warnings specific to this platform]

**Limitations:**
- [Any known limitations]

---

### macOS Apple Silicon

**Quirks:**
- [Any platform-specific behaviors]
- [Docker ARM vs x86 emulation performance]

**Warnings:**
- [Any warnings specific to this platform]

**Limitations:**
- [Any known limitations]

**Rosetta 2:**
- Not required ✅

---

### Linux Ubuntu 22.04

**Quirks:**
- [Any platform-specific behaviors]

**Warnings:**
- [Any warnings specific to this platform]

**Limitations:**
- [Any known limitations]

**Docker Group:**
- User in docker group: [yes/no]

---

### Linux Debian 12

**Quirks:**
- [Any platform-specific behaviors]

**Warnings:**
- [Any warnings specific to this platform]

**Limitations:**
- [Any known limitations]

**Docker Group:**
- User in docker group: [yes/no]

---

### Windows WSL2

**Quirks:**
- [Any platform-specific behaviors]
- [Path translation issues]
- [File permission handling]

**Warnings:**
- [Any warnings specific to this platform]

**Limitations:**
- [Any known limitations]

**WSL Integration:**
- Docker Desktop WSL2 backend: [enabled/disabled]

---

## Recommendations

### For Users

1. **Recommended Platforms:** [List platforms that work best]
2. **Setup Tips:** [Any setup recommendations]
3. **Known Workarounds:** [For any minor issues]

### For Development Team

1. **Priority Fixes:** [Issues that should be addressed first]
2. **Documentation Updates:** [What should be documented]
3. **Future Improvements:** [Nice-to-have improvements]

---

## Acceptance Criteria

### Platform-Specific Requirements

#### macOS (Intel and ARM)
- [ ] Docker Desktop installed and running
- [ ] All test scenarios pass
- [ ] Performance acceptable
- [ ] File permissions correct
- [ ] Path handling works (spaces, special chars)
- [ ] Native terminal works
- [ ] Rosetta 2 not required (ARM)

#### Linux (Ubuntu/Debian)
- [ ] Docker Engine installed and running
- [ ] User in docker group (no sudo)
- [ ] All test scenarios pass
- [ ] Performance acceptable
- [ ] File permissions correct
- [ ] SELinux/AppArmor compatible (if enabled)
- [ ] Works in various terminals

#### Windows WSL2
- [ ] WSL2 installed and configured
- [ ] Docker Desktop with WSL2 backend
- [ ] All test scenarios pass
- [ ] Performance acceptable
- [ ] Path translation works
- [ ] File permissions appropriate
- [ ] Works in Windows Terminal

### Overall Testing
- [ ] All critical scenarios pass on all platforms
- [ ] Performance acceptable on all platforms
- [ ] No blockers identified
- [ ] Test report complete and reviewed

---

## Sign-Off

**Tested By:** [Your Name]
**Date:** [YYYY-MM-DD]
**Approved By:** [Reviewer Name]
**Date:** [YYYY-MM-DD]

**Overall Result:** ⏸️ Pending Testing

---

## Appendix: Testing Checklist

Use this checklist while performing manual testing:

### Pre-Testing Setup
- [ ] Clean system state (remove any previous test projects)
- [ ] Docker running and healthy
- [ ] Node.js/npm available
- [ ] Network connection stable
- [ ] Screenshot/recording tool ready (optional)

### During Testing
- [ ] Run each test scenario sequentially
- [ ] Document results immediately
- [ ] Take screenshots of errors
- [ ] Note exact error messages
- [ ] Record timing for performance tests
- [ ] Test both success and failure paths

### Post-Testing
- [ ] Review all results for completeness
- [ ] Categorize issues by severity
- [ ] Calculate performance metrics
- [ ] Write recommendations
- [ ] Submit for review

---

**End of Test Report**
