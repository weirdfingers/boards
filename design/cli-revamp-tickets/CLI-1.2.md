# Add Docker Build to GitHub Workflow

## Description

Add a new `publish-docker` job to the existing `.github/workflows/version-bump.yml` workflow that builds and publishes the backend Docker image to both GitHub Container Registry (GHCR) and Docker Hub on every release.

The job should:
- Build for multiple architectures (linux/amd64, linux/arm64) using Docker Buildx
- Push to both GHCR (`ghcr.io/weirdfingers/boards-backend`) and Docker Hub (`weirdfingers/boards-backend`)
- Tag with both specific version and `latest`
- Use GitHub Actions cache for faster builds
- Run after the `bump-and-release` job completes
- Have appropriate permissions for pushing to GHCR

This enables automatic image publishing as part of the release process, so users can pull pre-built images instead of building locally.

## Dependencies

- CLI-1.1 (Dockerfile must exist before workflow can build it)

## Files to Create/Modify

- Modify `.github/workflows/version-bump.yml`

## Testing

### Local Testing (if possible)
```bash
# Test multi-arch build locally with buildx
docker buildx create --use
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t test-backend:local \
  packages/backend
```

### Workflow Validation
```bash
# Validate workflow syntax
gh workflow view version-bump.yml
```

### Dry Run Test
After pushing the workflow changes to a branch:
- Trigger the workflow manually via GitHub Actions UI
- Verify the publish-docker job appears in the workflow
- Check that it waits for bump-and-release to complete
- Monitor build logs for multi-arch support

### Post-Release Verification
After a real release:
```bash
# Verify images were pushed to GHCR
docker pull ghcr.io/weirdfingers/boards-backend:0.7.0
docker pull ghcr.io/weirdfingers/boards-backend:latest

# Verify images were pushed to Docker Hub
docker pull weirdfingers/boards-backend:0.7.0
docker pull weirdfingers/boards-backend:latest

# Verify multi-arch support
docker manifest inspect ghcr.io/weirdfingers/boards-backend:0.7.0
```

## Acceptance Criteria

- [ ] New `publish-docker` job added to version-bump.yml
- [ ] Job depends on `bump-and-release` (runs after it completes)
- [ ] Job has `packages: write` permission for GHCR
- [ ] QEMU setup step included for multi-arch support
- [ ] Docker Buildx setup step included
- [ ] Login to GHCR step uses `${{ secrets.GITHUB_TOKEN }}`
- [ ] Login to Docker Hub step uses secrets (DOCKERHUB_USERNAME, DOCKERHUB_TOKEN)
- [ ] Build step specifies `platforms: linux/amd64,linux/arm64`
- [ ] Push enabled: `push: true`
- [ ] Tags include version and latest for both registries:
  - `ghcr.io/weirdfingers/boards-backend:${{ needs.bump-and-release.outputs.version }}`
  - `ghcr.io/weirdfingers/boards-backend:latest`
  - `weirdfingers/boards-backend:${{ needs.bump-and-release.outputs.version }}`
  - `weirdfingers/boards-backend:latest`
- [ ] GitHub Actions cache configured: `cache-from: type=gha` and `cache-to: type=gha,mode=max`
- [ ] Build context points to `packages/backend`
- [ ] Dockerfile path is `packages/backend/Dockerfile`
- [ ] Workflow runs successfully and pushes images
