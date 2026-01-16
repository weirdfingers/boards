# Configure Registry Credentials

## Description

Set up the necessary secrets and permissions in the GitHub repository to enable the publish-docker workflow job to push Docker images to both GitHub Container Registry (GHCR) and Docker Hub.

For GHCR:
- No additional secrets needed (uses built-in `GITHUB_TOKEN`)
- Verify repository/organization permissions allow package publishing
- Ensure workflow has `packages: write` permission

For Docker Hub:
- Create Docker Hub access token
- Add secrets to GitHub repository: `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`

This is a prerequisite for CLI-1.2 to successfully push images during the release workflow.

## Dependencies

None (can be done in parallel with CLI-1.1 and CLI-1.2)

## Files to Create/Modify

None (configuration only in GitHub UI)

## Testing

### GHCR Access Test
```bash
# Verify GITHUB_TOKEN has package permissions
# This is automatic in GitHub Actions but can be verified by:
# 1. Checking workflow permissions in repo settings
# 2. Attempting a test push in a workflow run
```

### Docker Hub Access Test
```bash
# Test Docker Hub credentials locally
echo $DOCKERHUB_TOKEN | docker login -u $DOCKERHUB_USERNAME --password-stdin

# Verify login succeeds
docker logout
```

### Workflow Integration Test
After secrets are configured:
- Trigger the version-bump workflow (manual dispatch or actual release)
- Verify the publish-docker job can authenticate to both registries
- Check workflow logs for successful login steps
- Confirm no authentication errors during push

## Acceptance Criteria

- [ ] Docker Hub account exists or personal access token created
- [ ] `DOCKERHUB_USERNAME` secret added to GitHub repository
- [ ] `DOCKERHUB_TOKEN` secret added to GitHub repository (not password, use access token)
- [ ] Secrets are repository secrets (not environment secrets) for workflow access
- [ ] Repository settings allow GitHub Actions to create packages
- [ ] Workflow permissions include `packages: write` in version-bump.yml
- [ ] Test workflow run successfully authenticates to both GHCR and Docker Hub
- [ ] No authentication errors in workflow logs
- [ ] Personal access token has appropriate scopes:
  - Docker Hub: Read & Write permissions
  - GITHUB_TOKEN: Automatic, no action needed
