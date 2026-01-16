# Create Migration Guide

## Description

Create a comprehensive migration guide for users upgrading from v0.7.0 to v0.8.0. This guide should explain all breaking changes, provide step-by-step migration instructions, and help users understand the benefits of upgrading.

The migration guide is critical for user adoption and should minimize friction during the upgrade.

## Dependencies

All previous phases (complete understanding of changes)

## Files to Create/Modify

- Create `/docs/MIGRATION_v0.8.md`
- Update `/apps/docs/docs/migration-v0.8.md` (for website)

## Testing

### Completeness Test
```bash
# Verify all breaking changes documented
# Cross-reference with changelog
# Ensure step-by-step instructions complete
```

### Migration Validation Test
```bash
# Follow the migration guide with a v0.7.0 project
# Verify each step works
# Verify final result is functional v0.8.0 project
```

## Acceptance Criteria

### Document Structure

- [ ] Clear title: "Migration Guide: v0.7.0 → v0.8.0"
- [ ] Date of release
- [ ] Table of contents
- [ ] Sections:
  - Summary of changes
  - Breaking changes
  - New features
  - Migration steps
  - Troubleshooting
  - FAQ

### Summary of Changes

- [ ] High-level overview:
  - Backend now runs from pre-built Docker images
  - Templates downloaded from GitHub Releases
  - Single development mode (no prod/dev)
  - New --app-dev flag for local frontend development
  - New templates command

- [ ] Benefits of upgrading:
  - Faster setup (no local backend build)
  - Consistent environments (everyone uses same image)
  - Multiple template options
  - Better development experience with --app-dev
  - Smaller npm package size
  - Faster template loading with cache

### Breaking Changes

- [ ] **--prod flag removed**:
  - What: Production mode no longer available in CLI
  - Why: CLI is for development only; use Docker for production
  - Impact: Scripts using --prod will fail
  - Migration: Remove --prod flag from scripts, deploy using Docker Compose directly

- [ ] **--dev flag removed** (implicit default):
  - What: Dev mode is now the only mode
  - Why: Simplification
  - Impact: Minimal (it's the default)
  - Migration: Remove --dev flag (no longer needed)

- [ ] **Backend runs from Docker image**:
  - What: Backend code no longer built locally
  - Why: Faster, more consistent
  - Impact: Custom backend code won't work
  - Migration: For custom backends, fork and build your own image

- [ ] **Templates from GitHub Releases**:
  - What: Templates downloaded, not bundled
  - Why: Smaller package, multiple templates, independent versioning
  - Impact: Requires internet on first scaffold
  - Migration: Ensure internet access or pre-download templates

- [ ] **New project structure**:
  - What: Simplified structure, no `api/` directory
  - Why: Backend in image, only frontend scaffolded
  - Impact: Old scaffolds incompatible
  - Migration: Re-scaffold project

### New Features

- [ ] **Multiple templates**:
  - `baseboards` - Full-featured application
  - `basic` - Minimal starter
  - More coming soon

- [ ] **--template flag**:
  - Choose template explicitly
  - Example: `--template basic`

- [ ] **--app-dev mode**:
  - Run frontend locally with native tooling
  - Better IDE integration
  - Faster hot reload
  - Example: `--app-dev`

- [ ] **templates command**:
  - List available templates
  - Example: `baseboards templates`

- [ ] **Template caching**:
  - Templates cached locally after first download
  - Subsequent scaffolds much faster

### Step-by-Step Migration

- [ ] **Prerequisites**:
  ```bash
  # Ensure Docker is running
  docker --version

  # Ensure Node.js 20+ (for --app-dev only)
  node --version
  ```

- [ ] **Step 1: Backup Configuration**:
  ```bash
  # Navigate to your project
  cd my-baseboards-project

  # Backup configuration files
  mkdir ~/backup-v0.7.0
  cp -r config/ ~/backup-v0.7.0/
  cp docker/.env ~/backup-v0.7.0/docker.env
  cp api/.env ~/backup-v0.7.0/api.env 2>/dev/null || true

  # Backup any custom modifications
  cp -r data/ ~/backup-v0.7.0/ 2>/dev/null || true
  ```

- [ ] **Step 2: Stop Old Services**:
  ```bash
  # Stop services
  npx @weirdfingers/baseboards@0.7.0 down

  # Optional: Remove volumes if you want fresh database
  npx @weirdfingers/baseboards@0.7.0 down --volumes
  ```

- [ ] **Step 3: Clean Old Scaffold**:
  ```bash
  # Move to parent directory
  cd ..

  # Rename old project (don't delete yet)
  mv my-baseboards-project my-baseboards-project-v0.7.0
  ```

- [ ] **Step 4: Re-scaffold with v0.8.0**:
  ```bash
  # Scaffold with new CLI
  npx @weirdfingers/baseboards@latest up my-baseboards-project

  # Select template when prompted (or use --template flag)
  # Example: baseboards
  ```

- [ ] **Step 5: Restore Configuration**:
  ```bash
  cd my-baseboards-project

  # Restore config files
  cp ~/backup-v0.7.0/config/* config/

  # Restore environment variables
  # NOTE: docker/.env and api/.env formats may have changed
  # Manually merge changes from backup

  # Restore custom storage
  cp -r ~/backup-v0.7.0/data/* data/ 2>/dev/null || true
  ```

- [ ] **Step 6: Review and Update Environment Variables**:
  ```bash
  # Compare old and new .env files
  diff ~/backup-v0.7.0/docker.env docker/.env
  diff ~/backup-v0.7.0/api.env api/.env

  # Update with your values (API keys, secrets, etc.)
  vim docker/.env
  vim api/.env
  ```

- [ ] **Step 7: Start New Version**:
  ```bash
  # Start services
  npx @weirdfingers/baseboards up .

  # Verify services are healthy
  npx @weirdfingers/baseboards status .
  ```

- [ ] **Step 8: Verify and Test**:
  ```bash
  # Open web app
  open http://localhost:3300

  # Test key functionality:
  # - Login/authentication
  # - Create a board
  # - Generate content
  # - Check existing data (if restored)
  ```

- [ ] **Step 9: Clean Up**:
  ```bash
  # Once verified, remove old scaffold
  rm -rf ../my-baseboards-project-v0.7.0

  # Remove backup if desired
  rm -rf ~/backup-v0.7.0
  ```

### Troubleshooting

- [ ] **Issue: Template download fails**:
  - Cause: No internet connection or GitHub unavailable
  - Solution: Check internet, try again later, or use cached templates

- [ ] **Issue: Port conflicts**:
  - Cause: Ports 3300 or 8800 already in use
  - Solution: Use --ports flag to specify different ports

- [ ] **Issue: Docker image pull fails**:
  - Cause: Docker not running or network issue
  - Solution: Start Docker, check network, try again

- [ ] **Issue: Configuration not working**:
  - Cause: Environment variable format changed
  - Solution: Review new .env.example files and update accordingly

- [ ] **Issue: Lost data after migration**:
  - Cause: Volumes not backed up
  - Solution: If backups available, restore; otherwise, data is lost

- [ ] **Issue: Custom backend code doesn't work**:
  - Cause: Backend runs from pre-built image
  - Solution: For custom backends, use monorepo development setup, not CLI

### FAQ

- [ ] **Q: Do I have to migrate?**
  - A: No, v0.7.0 continues to work, but v0.8.0 has significant improvements

- [ ] **Q: Can I go back to v0.7.0?**
  - A: Yes, if you backed up your old scaffold

- [ ] **Q: Will my data be lost?**
  - A: Not if you follow the backup steps and don't use --volumes when stopping

- [ ] **Q: Can I use multiple templates?**
  - A: Yes, choose during scaffold or use --template flag

- [ ] **Q: What if I have custom backend code?**
  - A: CLI is for running, not developing the toolkit. Use monorepo for development.

- [ ] **Q: How do I pin to a specific backend version?**
  - A: Set BACKEND_VERSION in docker/.env (e.g., BACKEND_VERSION=0.8.0)

- [ ] **Q: Can I still run the web app in Docker?**
  - A: Yes, that's the default. Use --app-dev only if you want local dev.

- [ ] **Q: What's the difference between baseboards and basic templates?**
  - A: Baseboards is full-featured (12MB), basic is minimal (45KB). Choose based on needs.

### Quality

- [ ] Clear, step-by-step instructions
- [ ] No ambiguity
- [ ] Tested by following exactly
- [ ] Examples for each step
- [ ] Warning about data loss
- [ ] Encouragement to backup

### Links

- [ ] Link to full changelog
- [ ] Link to v0.8.0 release notes
- [ ] Link to new documentation
- [ ] Link to issue tracker for problems
