# Add Template Publishing to Workflow

## Description

Add a new `publish-templates` job to the `.github/workflows/version-bump.yml` workflow that builds and publishes template tarballs and manifest to GitHub Release assets. This job runs after the release is created and makes templates available for download via the CLI.

The job should:
- Check out code at the release tag
- Install dependencies (pnpm, Node.js)
- Run the template preparation script
- Upload template tarballs to the GitHub Release
- Upload template manifest to the GitHub Release

This enables the new template download system where templates are fetched from GitHub Releases instead of being bundled in the npm package.

## Dependencies

- CLI-2.3 (Template preparation script must exist)

## Files to Create/Modify

- Modify `.github/workflows/version-bump.yml`

## Testing

### Workflow Syntax Test
```bash
# Validate workflow YAML syntax
gh workflow view version-bump.yml
```

### Local Script Test
Before adding to workflow, test script locally:
```bash
# Install dependencies
pnpm install

# Run template prep script
./scripts/prepare-release-templates.sh "0.8.0"

# Verify outputs exist
ls -la dist/template-*.tar.gz dist/template-manifest.json
```

### Dry Run Test
After workflow changes:
- Create a test branch
- Manually trigger workflow with workflow_dispatch
- Monitor the publish-templates job
- Verify it runs after bump-and-release completes
- Check that tarballs and manifest are generated

### Release Verification Test
After a real release:
```bash
# Check GitHub Release assets
gh release view v0.8.0 --json assets --jq '.assets[].name'

# Should show:
# - template-baseboards-v0.8.0.tar.gz
# - template-basic-v0.8.0.tar.gz
# - template-manifest.json

# Download and verify
gh release download v0.8.0 --pattern "template-*"

# Verify checksums in manifest match downloaded files
sha256sum template-baseboards-v0.8.0.tar.gz
cat template-manifest.json | jq '.templates[] | select(.name=="baseboards") | .checksum'
```

## Acceptance Criteria

- [ ] New `publish-templates` job added to version-bump.yml
- [ ] Job depends on `bump-and-release` (needs version output)
- [ ] Job has `contents: write` permission for uploading release assets
- [ ] Checkout step uses correct ref:
  ```yaml
  with:
    ref: "v${{ needs.bump-and-release.outputs.version }}"
  ```
- [ ] pnpm installation step included
- [ ] Node.js setup step included (v20.x)
- [ ] pnpm install step runs to get dependencies
- [ ] Build templates step runs:
  ```yaml
  run: |
    VERSION=${{ needs.bump-and-release.outputs.version }}
    ./scripts/prepare-release-templates.sh "$VERSION"
  ```
- [ ] Upload templates to release step uses `softprops/action-gh-release@v1`
- [ ] Upload includes all three files:
  ```yaml
  files: |
    dist/template-baseboards-v${{ needs.bump-and-release.outputs.version }}.tar.gz
    dist/template-basic-v${{ needs.bump-and-release.outputs.version }}.tar.gz
    dist/template-manifest.json
  ```
- [ ] Upload step references correct tag:
  ```yaml
  tag_name: "v${{ needs.bump-and-release.outputs.version }}"
  ```
- [ ] Workflow succeeds in test run
- [ ] Assets appear on GitHub Release after workflow completes
- [ ] Assets are publicly downloadable
- [ ] Job logs show successful template preparation
- [ ] No errors in workflow execution
