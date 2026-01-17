# Create Release Template Preparation Script

## Description

Create a bash script that prepares templates for release by packaging them as tarballs and generating the template manifest. This script will be run during the CI/CD release process.

The script must:
1. Prepare the `baseboards` template from `apps/baseboards`
2. Prepare the `basic` template from `packages/cli-launcher/basic-template`
3. Transform workspace dependencies to published package versions
4. Copy shared template files (compose files, Dockerfiles)
5. Create versioned tarballs
6. Generate the template manifest with checksums

This script bridges the development workspace structure (using workspace:* dependencies) to the published template structure (using actual package versions).

## Dependencies

- CLI-2.1 (Basic template must exist)
- CLI-2.2 (Manifest generator script must exist)

## Files to Create/Modify

- Create `/scripts/prepare-release-templates.sh`
- Optionally create `/scripts/transform-package-json.js` (for workspace dep transformation)

## Testing

### Dry Run Test
```bash
# Set test version
export VERSION=0.8.0-test

# Run script
./scripts/prepare-release-templates.sh $VERSION

# Verify output directory structure
ls -la dist/templates/
# Should show: baseboards/ basic/

# Verify tarballs created
ls -la dist/
# Should show: template-baseboards-v0.8.0-test.tar.gz
#              template-basic-v0.8.0-test.tar.gz
#              template-manifest.json
```

### Baseboards Template Test
```bash
# Extract and verify baseboards template
mkdir -p test-extract/baseboards
tar -xzf dist/template-baseboards-v0.8.0-test.tar.gz -C test-extract/

# Verify structure
ls test-extract/baseboards/
# Should show: web/ config/ docker/ compose.yaml compose.web.yaml Dockerfile.web README.md

# Verify workspace deps are replaced
cat test-extract/baseboards/web/package.json | grep "@weirdfingers/boards"
# Should show version like "^0.8.0", NOT "workspace:*"
```

### Basic Template Test
```bash
# Extract and verify basic template
mkdir -p test-extract/basic
tar -xzf dist/template-basic-v0.8.0-test.tar.gz -C test-extract/

# Verify structure
ls test-extract/basic/
# Should show: web/ config/ docker/ compose.yaml compose.web.yaml Dockerfile.web README.md

# Verify package.json version
cat test-extract/basic/web/package.json | jq '.version'
# Should be "0.8.0-test"
```

### Manifest Test
```bash
# Verify manifest was generated
cat dist/template-manifest.json | jq .

# Verify it includes both templates
cat dist/template-manifest.json | jq '.templates | length'
# Should be 2

# Verify checksums match
sha256sum dist/template-baseboards-v0.8.0-test.tar.gz
sha256sum dist/template-basic-v0.8.0-test.tar.gz
# Compare with manifest checksums
```

### Exclusion Test
```bash
# Verify build artifacts are excluded
tar -tzf dist/template-baseboards-v0.8.0-test.tar.gz | grep -E '(.next|node_modules|dist)'
# Should return nothing (empty)
```

### Shared Files Test
```bash
# Verify shared template files are included
tar -tzf dist/template-basic-v0.8.0-test.tar.gz | grep -E '(compose\.yaml|Dockerfile\.web)'
# Should find these files
```

## Acceptance Criteria

- [ ] Script file created at `/scripts/prepare-release-templates.sh`
- [ ] Script accepts VERSION as first argument
- [ ] Script creates `dist/templates/` directory
- [ ] Baseboards template prepared:
  - [ ] Copies from `apps/baseboards/` to `dist/templates/baseboards/web/`
  - [ ] Excludes .next, node_modules, build artifacts
  - [ ] Transforms workspace:* dependencies to $VERSION
  - [ ] Copies shared files (compose.yaml, compose.web.yaml, Dockerfile.web, config/)
  - [ ] Creates extensions/ directories with README files (generators and plugins)
  - [ ] Creates data/storage/.gitkeep
  - [ ] Includes .gitignore with data/storage/* pattern
  - [ ] Ensures storage_config.yaml uses /app/data/storage for base_path
- [ ] Basic template prepared:
  - [ ] Copies from `packages/cli-launcher/basic-template/` to `dist/templates/basic/`
  - [ ] Updates version in package.json to $VERSION
  - [ ] Copies shared files
  - [ ] Includes extensions/ directories (should already be in basic-template from CLI-2.1)
  - [ ] Includes data/storage/.gitkeep
  - [ ] Verifies storage_config.yaml path is correct
- [ ] Creates tarballs:
  - [ ] `dist/template-baseboards-v$VERSION.tar.gz`
  - [ ] `dist/template-basic-v$VERSION.tar.gz`
- [ ] Calls generate-template-manifest.js to create manifest
- [ ] Manifest written to `dist/template-manifest.json`
- [ ] Script is idempotent (can run multiple times safely)
- [ ] Script includes error handling (exits on failure)
- [ ] Script includes progress messages
- [ ] All file permissions preserved in tarballs
- [ ] Script includes usage help/documentation
