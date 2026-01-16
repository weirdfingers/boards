# Cross-Platform Testing

## Description

Perform comprehensive manual testing of the CLI revamp on all supported platforms to ensure cross-platform compatibility and catch platform-specific issues. This includes testing on macOS (Intel and Apple Silicon), Linux (Ubuntu/Debian), and Windows (WSL2).

Since this is manual testing, it's important to have a structured testing plan and document results.

## Dependencies

All previous phases (CLI should be feature-complete)

## Files to Create/Modify

None (testing only, but create test report document if needed)

## Testing

### Platform Matrix

Test on the following platforms:
- macOS Intel (x86_64)
- macOS Apple Silicon (arm64)
- Linux Ubuntu 22.04 (amd64)
- Linux Debian 12 (amd64)
- Windows 11 WSL2 Ubuntu (amd64)

### Test Scenarios

For EACH platform, execute these test scenarios:

#### 1. Installation Test
```bash
# Fresh installation
npx @weirdfingers/baseboards@latest --version

# Verify version displayed
# Verify no errors
```

#### 2. Basic Scaffold Test
```bash
# Default template
npx @weirdfingers/baseboards up test-default

# Verify:
# - Project scaffolded
# - 5 services start
# - All health checks pass
# - Web accessible at http://localhost:3300
# - API accessible at http://localhost:8800
```

#### 3. Template Selection Test
```bash
# Interactive selection
npx @weirdfingers/baseboards up test-interactive
# (Select basic template)

# Explicit template
npx @weirdfingers/baseboards up test-basic --template basic

# Verify:
# - Prompt works correctly
# - Template downloads
# - Correct template used
```

#### 4. App-Dev Mode Test
```bash
# App-dev mode with package manager selection
npx @weirdfingers/baseboards up test-appdev --template basic --app-dev

# Verify:
# - Package manager prompt works
# - 4 services start (no web)
# - Dependencies install correctly
# - Instructions displayed
# - Can manually start frontend (cd test-appdev/web && pnpm dev)
```

#### 5. Templates Command Test
```bash
# List templates
npx @weirdfingers/baseboards templates

# Verify:
# - Templates listed
# - Descriptions shown
# - No errors
```

#### 6. Logs Command Test
```bash
# View logs
npx @weirdfingers/baseboards logs test-default

# Follow logs
npx @weirdfingers/baseboards logs test-default -f
# (Ctrl+C to stop)

# Service-specific logs
npx @weirdfingers/baseboards logs test-default api worker

# Verify:
# - Logs displayed
# - Follow mode works
# - Ctrl+C exits cleanly
```

#### 7. Status Command Test
```bash
# Check status
npx @weirdfingers/baseboards status test-default

# Verify:
# - Services listed
# - Status shown (healthy/unhealthy)
```

#### 8. Down Command Test
```bash
# Stop services
npx @weirdfingers/baseboards down test-default

# Verify:
# - Services stop
# - Volumes preserved

# Stop with volumes
npx @weirdfingers/baseboards down test-default --volumes

# Verify:
# - Volumes deleted
```

#### 9. Clean Command Test
```bash
# Clean project
npx @weirdfingers/baseboards clean test-default

# Verify:
# - Containers removed
# - Volumes preserved (default)

# Hard clean
npx @weirdfingers/baseboards clean test-default --hard

# Verify:
# - Everything removed
```

#### 10. Doctor Command Test
```bash
# Run diagnostics
npx @weirdfingers/baseboards doctor test-default

# Verify:
# - Prerequisites checked
# - Status reported
# - Helpful output
```

#### 11. Cache Test
```bash
# First scaffold (downloads template)
npx @weirdfingers/baseboards up test-cache-1 --template basic

# Second scaffold (uses cache)
npx @weirdfingers/baseboards up test-cache-2 --template basic

# Verify:
# - First is slower (downloads)
# - Second is faster (cache hit)
# - Cache directory exists: ~/.baseboards/templates/

# Clear cache
npx @weirdfingers/baseboards templates --refresh

# Verify:
# - Cache cleared
# - Re-downloads on next scaffold
```

#### 12. Custom Ports Test
```bash
# Custom ports
npx @weirdfingers/baseboards up test-ports --ports "web=4000 api=9000"

# Verify:
# - Web on port 4000
# - API on port 9000
```

#### 13. Error Handling Test
```bash
# Invalid template
npx @weirdfingers/baseboards up test-error --template nonexistent

# Verify:
# - Clear error message
# - Lists available templates

# Network error (disconnect network)
npx @weirdfingers/baseboards up test-network --template basic

# Verify:
# - Clear error message
# - Suggests checking connection

# Port conflict (start nginx on 3300)
npx @weirdfingers/baseboards up test-conflict

# Verify:
# - Detects conflict
# - Offers alternative port or error
```

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
- [ ] Works in various terminals (gnome-terminal, konsole, etc.)

#### Windows WSL2
- [ ] WSL2 installed and configured
- [ ] Docker Desktop with WSL2 backend
- [ ] All test scenarios pass
- [ ] Performance acceptable
- [ ] Path translation works (C:\\ to /mnt/c)
- [ ] File permissions appropriate
- [ ] Works in Windows Terminal

### Documentation

- [ ] Create test report document:
  ```
  design/cli-revamp-test-report.md

  Contents:
  - Test date
  - Platform matrix
  - Test results (pass/fail for each scenario on each platform)
  - Issues found
  - Performance notes
  - Recommendations
  ```

### Issues Found

For any issues discovered:
- [ ] Document platform, scenario, and steps to reproduce
- [ ] Assess severity (blocker, major, minor)
- [ ] Create GitHub issues for blockers/majors
- [ ] Fix or defer based on severity

### Performance Benchmarks

Document performance metrics:
- [ ] Template download time (first run)
- [ ] Cache hit time (second run)
- [ ] Scaffold to running services time
- [ ] Docker image pull time (first run)
- [ ] Note any platform differences

### Compatibility Notes

- [ ] Document any platform-specific quirks
- [ ] Note any platform-specific warnings
- [ ] Document any known limitations
- [ ] Update docs with platform notes

### Sign-off

- [ ] All critical scenarios pass on all platforms
- [ ] Performance acceptable on all platforms
- [ ] No blockers identified
- [ ] Test report reviewed and approved
