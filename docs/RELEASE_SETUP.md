# Release Workflow Setup

This document explains how to set up and use the automated release workflow for the Boards project.

## Overview

The release workflow automatically:
- Updates version numbers in both `@weirdfingers/boards` (npm) and `boards-backend` (PyPI)
- Builds and tests both packages
- Publishes to npm and PyPI simultaneously
- Creates GitHub releases with automatic changelogs
- Supports both automatic version detection and manual overrides

## Required Setup

### 1. GitHub Secrets

Add these secrets in your GitHub repository settings (`Settings > Secrets and variables > Actions`):

#### NPM_TOKEN
1. Go to [www.npmjs.com](https://www.npmjs.com) and sign in to the `weirdfingers` organization account
2. Navigate to `Account > Access Tokens > Generate New Token`
3. Select "Automation" token type with "Read and write" permissions  
4. Copy the token and add it as `NPM_TOKEN` in GitHub secrets

#### PYPI_TOKEN
1. Go to [pypi.org](https://pypi.org) and sign in to the `weirdfingers` organization account
2. Navigate to `Account Settings > API tokens > Add API token`
3. Set scope to "Entire account" or create a project-specific token for `boards-backend`
4. Copy the token and add it as `PYPI_TOKEN` in GitHub secrets

### 2. Package Registry Setup

#### npm Package
- Package name: `@weirdfingers/boards`
- Organization: `weirdfingers` 
- Make sure the organization has publish permissions

#### PyPI Package  
- Package name: `boards-backend`
- Organization: `weirdfingers`
- Make sure the organization has upload permissions

## Usage

### Method 1: Git Tags (Recommended)

Create and push a version tag to trigger a release:

```bash
# Create and push a tag
git tag v1.2.3
git push origin v1.2.3
```

The workflow will:
- Use the exact version from the tag (e.g., `v1.2.3` → version `1.2.3`)
- Update both package versions
- Build, test, and publish both packages
- Create a GitHub release

### Method 2: Manual Workflow Dispatch

Trigger releases manually through GitHub Actions UI:

1. Go to `Actions > Release > Run workflow`
2. Select the branch (usually `main`)
3. Choose options:
   - **Version**: Leave empty for auto-detection, or specify exact version (e.g., `1.2.3`)
   - **Bump Type**: `auto`, `major`, `minor`, or `patch`

#### Auto-Detection Rules
When version and bump type are not specified, the workflow analyzes recent commits:

- **Major bump**: Commits containing `BREAKING`, `breaking`, `feat!`, or `fix!`
- **Minor bump**: Commits containing `feat:` (new features)  
- **Patch bump**: All other commits (bug fixes, chores, etc.)

## Version Management

### Synchronized Versioning
Both packages always receive the same version number. This ensures:
- Consistent releases across frontend and backend
- Simplified dependency management  
- Clear compatibility guarantees

### Current Versions
- Frontend (`@weirdfingers/boards`): 0.1.0
- Backend (`boards-backend`): 0.1.0

## Workflow Stages

1. **Version Determination**: Analyzes tags, inputs, or commits to determine target version
2. **Build & Test**: Runs full test suite and linting for both packages
3. **Version Update**: Updates `package.json` and `pyproject.toml` files
4. **Publish npm**: Builds and publishes React hooks to npm registry
5. **Publish PyPI**: Builds and publishes Python backend to PyPI
6. **Create Release**: Generates GitHub release with automatic changelog

## Troubleshooting

### Common Issues

**"Package already exists" errors:**
- Check that the version number hasn't been published before
- npm and PyPI don't allow republishing the same version

**"Authentication failed" errors:**
- Verify that `NPM_TOKEN` and `PYPI_TOKEN` secrets are correctly set
- Ensure tokens have appropriate permissions for the `weirdfingers` organization

**"Version update failed" errors:**
- Check that the Git user has write permissions to the repository
- Verify branch protection rules allow automated commits

**Build/test failures:**
- The workflow will stop if tests fail - fix failing tests before retrying
- Check that all dependencies are properly declared in package files

### Viewing Workflow Logs

1. Go to `Actions` tab in your GitHub repository  
2. Click on the failed "Release" workflow run
3. Click on the failed job to see detailed logs
4. Look for error messages in the expanded step logs

## Future Enhancements

This workflow is designed to easily support:

### Independent Versioning
To switch to independent package versions:
- Modify the `update-versions` job to handle different version numbers
- Update the `determine-version` job to detect changes per package
- Adjust publishing jobs to handle different version strategies

### Individual Package Releases
To enable releasing packages separately:
- Add workflow inputs to select which packages to release
- Add conditional logic in publishing jobs
- Create separate workflows for each package if preferred

### Advanced Version Detection
- Integrate with conventional commits for more sophisticated version bumping
- Add support for pre-release versions (alpha, beta, rc)
- Implement change detection to only release packages that have changed

## Package Links

After releases, packages will be available at:
- npm: https://www.npmjs.com/package/@weirdfingers/boards
- PyPI: https://pypi.org/project/boards-backend/