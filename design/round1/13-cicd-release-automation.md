# CI/CD and Release Automation

## Overview
Automated release pipeline that publishes to PyPI and npm when a GitHub release is created, with automatic version bumping and changelog generation.

## Release Strategy

### Version Management
- **Monorepo with Independent Versions**: Each package maintains its own version
- **Version Files**:
  - Python: `pyproject.toml` (version field)
  - TypeScript: `package.json` (version field)
- **Git Tags**: Format `package-name@version` (e.g., `backend-sdk@1.2.0`, `frontend-hooks@2.1.0`)

### Release Triggers
1. Manual: Create GitHub release with tag
2. Automated: Push to `main` with conventional commit triggers release

## GitHub Actions Workflows

### Main CI Workflow (`.github/workflows/ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12"]
        node-version: ["20.x"]
    
    steps:
      - uses: actions/checkout@v4
      
      # Setup Python
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      
      - name: Set up Python
        run: uv python install ${{ matrix.python-version }}
      
      # Setup Node
      - uses: pnpm/action-setup@v2
        with:
          version: 9
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'pnpm'
      
      # Install dependencies
      - name: Install Python dependencies
        run: |
          cd packages/backend-sdk
          uv pip install -e ".[dev]"
      
      - name: Install Node dependencies
        run: pnpm install
      
      # Lint Python
      - name: Lint Python
        run: |
          cd packages/backend-sdk
          uv run ruff check .
          uv run mypy .
      
      # Lint TypeScript
      - name: Lint TypeScript
        run: pnpm turbo lint
      
      # Test Python
      - name: Test Python
        run: |
          cd packages/backend-sdk
          uv run pytest tests/ --cov
      
      # Test TypeScript
      - name: Test TypeScript
        run: pnpm turbo test
      
      # Type check
      - name: Type check TypeScript
        run: pnpm turbo typecheck
```

### Release Workflow (`.github/workflows/release.yml`)

```yaml
name: Release

on:
  release:
    types: [published]

jobs:
  detect-packages:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.detect.outputs.packages }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Detect packages from tag
        id: detect
        run: |
          TAG="${{ github.event.release.tag_name }}"
          if [[ $TAG == backend-sdk@* ]]; then
            echo "packages=[\"backend-sdk\"]" >> $GITHUB_OUTPUT
          elif [[ $TAG == frontend-hooks@* ]]; then
            echo "packages=[\"frontend-hooks\"]" >> $GITHUB_OUTPUT
          elif [[ $TAG == weirdfingers-cli@* ]]; then
            echo "packages=[\"weirdfingers-cli\"]" >> $GITHUB_OUTPUT
          else
            echo "packages=[]" >> $GITHUB_OUTPUT
          fi

  release-python:
    needs: detect-packages
    if: contains(needs.detect-packages.outputs.packages, 'backend-sdk')
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      
      - name: Extract version from tag
        id: version
        run: |
          TAG="${{ github.event.release.tag_name }}"
          VERSION="${TAG#backend-sdk@}"
          echo "version=$VERSION" >> $GITHUB_OUTPUT
      
      - name: Update version in pyproject.toml
        run: |
          cd packages/backend-sdk
          sed -i "s/^version = .*/version = \"${{ steps.version.outputs.version }}\"/" pyproject.toml
      
      - name: Build package
        run: |
          cd packages/backend-sdk
          uv build
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          cd packages/backend-sdk
          uv publish

  release-npm:
    needs: detect-packages
    if: contains(needs.detect-packages.outputs.packages, 'frontend-hooks')
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: pnpm/action-setup@v2
        with:
          version: 9
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20.x'
          registry-url: 'https://registry.npmjs.org'
      
      - name: Extract version from tag
        id: version
        run: |
          TAG="${{ github.event.release.tag_name }}"
          VERSION="${TAG#frontend-hooks@}"
          echo "version=$VERSION" >> $GITHUB_OUTPUT
      
      - name: Update version
        run: |
          cd packages/frontend-hooks
          npm version ${{ steps.version.outputs.version }} --no-git-tag-version
      
      - name: Install dependencies
        run: pnpm install
      
      - name: Build package
        run: |
          cd packages/frontend-hooks
          pnpm build
      
      - name: Publish to npm
        run: |
          cd packages/frontend-hooks
          npm publish --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

  release-cli:
    needs: detect-packages
    if: contains(needs.detect-packages.outputs.packages, 'weirdfingers-cli')
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: pnpm/action-setup@v2
        with:
          version: 9
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20.x'
          registry-url: 'https://registry.npmjs.org'
      
      - name: Extract version from tag
        id: version
        run: |
          TAG="${{ github.event.release.tag_name }}"
          VERSION="${TAG#weirdfingers-cli@}"
          echo "version=$VERSION" >> $GITHUB_OUTPUT
      
      - name: Update version
        run: |
          cd packages/weirdfingers-cli
          npm version ${{ steps.version.outputs.version }} --no-git-tag-version
      
      - name: Build and publish
        run: |
          cd packages/weirdfingers-cli
          pnpm build
          npm publish --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### Version Bump Workflow (`.github/workflows/version-bump.yml`)

```yaml
name: Version Bump

on:
  workflow_dispatch:
    inputs:
      package:
        description: 'Package to bump'
        required: true
        type: choice
        options:
          - backend-sdk
          - frontend-hooks
          - weirdfingers-cli
      bump_type:
        description: 'Bump type'
        required: true
        type: choice
        options:
          - patch
          - minor
          - major

jobs:
  bump-version:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Configure Git
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
      
      - name: Bump Python package version
        if: inputs.package == 'backend-sdk'
        run: |
          cd packages/backend-sdk
          # Parse current version and bump
          CURRENT=$(grep "^version = " pyproject.toml | cut -d'"' -f2)
          # Use semver tool or custom script to bump
          NEW_VERSION=$(python -c "
          import sys
          parts = '$CURRENT'.split('.')
          if '${{ inputs.bump_type }}' == 'major':
              parts[0] = str(int(parts[0]) + 1)
              parts[1] = '0'
              parts[2] = '0'
          elif '${{ inputs.bump_type }}' == 'minor':
              parts[1] = str(int(parts[1]) + 1)
              parts[2] = '0'
          else:
              parts[2] = str(int(parts[2]) + 1)
          print('.'.join(parts))
          ")
          sed -i "s/^version = .*/version = \"$NEW_VERSION\"/" pyproject.toml
          echo "NEW_VERSION=$NEW_VERSION" >> $GITHUB_ENV
      
      - name: Bump npm package version
        if: inputs.package != 'backend-sdk'
        run: |
          cd packages/${{ inputs.package }}
          npm version ${{ inputs.bump_type }} --no-git-tag-version
          NEW_VERSION=$(node -p "require('./package.json').version")
          echo "NEW_VERSION=$NEW_VERSION" >> $GITHUB_ENV
      
      - name: Commit and tag
        run: |
          git add .
          git commit -m "chore: bump ${{ inputs.package }} to ${{ env.NEW_VERSION }}"
          git tag "${{ inputs.package }}@${{ env.NEW_VERSION }}"
          git push origin main --tags
      
      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: "${{ inputs.package }}@${{ env.NEW_VERSION }}"
          release_name: "${{ inputs.package }} v${{ env.NEW_VERSION }}"
          draft: false
          prerelease: false
```

## Local Development Scripts

### Release Script (`scripts/release.sh`)

```bash
#!/bin/bash

# Interactive release script for local use

PACKAGES=("backend-sdk" "frontend-hooks" "weirdfingers-cli")

echo "Which package do you want to release?"
select PACKAGE in "${PACKAGES[@]}"; do
    if [[ -n $PACKAGE ]]; then
        break
    fi
done

echo "What type of version bump?"
select BUMP in "patch" "minor" "major"; do
    if [[ -n $BUMP ]]; then
        break
    fi
done

# Trigger GitHub workflow
gh workflow run version-bump.yml \
  -f package=$PACKAGE \
  -f bump_type=$BUMP

echo "Release workflow triggered for $PACKAGE ($BUMP bump)"
```

## Environment Secrets Required

### GitHub Repository Secrets
- `PYPI_API_TOKEN`: PyPI API token for publishing Python packages
- `NPM_TOKEN`: npm authentication token for publishing Node packages
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions

### Local Development
Create `.env` file:
```bash
# For local PyPI uploads (testing)
TWINE_USERNAME=__token__
TWINE_PASSWORD=pypi-xxx

# For local npm publishing (testing)
NPM_TOKEN=npm_xxx
```

## Continuous Deployment

### Staging Environment
- Triggered on push to `develop` branch
- Deploys to staging environment for testing
- Uses preview/canary package versions

### Production Environment
- Triggered on successful release
- Deploys tagged versions to production
- Includes rollback capability

## Package Publishing Configuration

### Python (`packages/backend-sdk/pyproject.toml`)
```toml
[project]
name = "boards-backend-sdk"
dynamic = ["version"]  # Version managed by CI

[project.urls]
Homepage = "https://github.com/weirdfingers/boards"
Repository = "https://github.com/weirdfingers/boards"

[tool.setuptools.dynamic]
version = {attr = "boards.__version__"}
```

### npm (`packages/frontend-hooks/package.json`)
```json
{
  "name": "@weirdfingers/boards",
  "version": "0.0.0",
  "publishConfig": {
    "access": "public",
    "registry": "https://registry.npmjs.org/"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/weirdfingers/boards.git"
  }
}
```

## Release Checklist

1. **Pre-release**:
   - [ ] All tests passing
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated
   - [ ] Version compatibility matrix updated

2. **Release**:
   - [ ] Run version bump workflow
   - [ ] Verify package published correctly
   - [ ] Test installation from registry

3. **Post-release**:
   - [ ] Update example apps to use new version
   - [ ] Announce release (Discord, Twitter, etc.)
   - [ ] Close related issues/PRs