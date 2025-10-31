# OIDC Trusted Publishers Setup

This document describes how to configure PyPI and NPM to use OIDC (OpenID Connect) Trusted Publishers for secure, token-free publishing from GitHub Actions.

## Benefits of OIDC Trusted Publishers

- **Enhanced Security**: No long-lived API tokens to manage or risk exposing
- **Automatic Credentials**: Short-lived tokens generated automatically during CI/CD
- **Reduced Maintenance**: No manual token rotation required
- **Provenance**: Automatic generation of package provenance attestations

## PyPI Configuration

### 1. Configure Trusted Publisher on PyPI

1. Go to https://pypi.org/manage/project/weirdfingers-boards/settings/publishing/
2. Under "Trusted Publisher", click "Add a new publisher"
3. Select "GitHub Actions"
4. Configure the following:
   - **Owner**: `weirdfingers`
   - **Repository name**: `boards`
   - **Workflow name**: `version-bump.yml`
   - **Environment name**: `release` (STRONGLY RECOMMENDED for additional security)

### 2. Verify Workflow Configuration

The workflow already includes the required OIDC permissions and environment:

```yaml
publish-python:
  environment: release  # Must match PyPI configuration
  permissions:
    id-token: write
    contents: read
```

### 3. How It Works

- When the workflow runs, GitHub generates a short-lived OIDC token
- `uv publish` automatically detects the OIDC environment and uses it for authentication
- PyPI validates the token against the trusted publisher configuration
- If valid, PyPI issues a temporary API token (valid for 15 minutes)
- The package is published using this temporary token

### 4. Remove Old Token

After verifying OIDC publishing works:

1. Delete the `PYPI_API_TOKEN` secret from GitHub repository settings
2. Consider revoking the old API token on PyPI for security

## NPM Configuration

### 1. Configure Trusted Publisher on npmjs.com

1. Go to https://www.npmjs.com/package/@weirdfingers/boards
2. Click on "Settings" tab
3. Scroll to "Trusted Publisher" section
4. Click "Select your publisher" and choose "GitHub Actions"
5. Configure the following:
   - **Organization or user**: `weirdfingers`
   - **Repository**: `boards`
   - **Workflow filename**: `version-bump.yml` (filename only, no path)
   - **Environment name**: `release` (STRONGLY RECOMMENDED for additional security)

### 2. Verify Workflow Configuration

The workflow already includes:

- Required OIDC permissions (`id-token: write`)
- Environment declaration (`environment: release`)
- Updated npm to version 11.5.1+ (required for OIDC support)
- Removed `NODE_AUTH_TOKEN` environment variable

```yaml
publish-npm:
  environment: release  # Must match npm configuration
  permissions:
    id-token: write
    contents: read
```

### 3. How It Works

- When the workflow runs, GitHub generates a short-lived OIDC token
- npm CLI (v11.5.1+) automatically detects the OIDC environment
- npm validates the token against the trusted publisher configuration
- If valid, npm issues a temporary publish token
- The package is published using this temporary token

### 4. (Optional) Restrict Token Access

For maximum security, after setting up trusted publishers:

1. Go to package settings on npmjs.com
2. Navigate to "Publishing access"
3. Select "Require two-factor authentication and disallow tokens"
4. This prevents publishing via traditional tokens while allowing OIDC

### 5. Remove Old Token

After verifying OIDC publishing works:

1. Delete the `NPM_TOKEN` secret from GitHub repository settings
2. Revoke any automation tokens on npmjs.com that are no longer needed

## Package Configuration Requirements

### NPM: Repository Field Required

For npm to generate provenance attestations, your `package.json` **must** include a `repository` field that matches your GitHub repository:

```json
{
  "repository": {
    "type": "git",
    "url": "https://github.com/weirdfingers/boards.git"
  }
}
```

Without this field, npm will reject the publish with an error like:
```
Error verifying sigstore provenance bundle: Failed to validate repository information
```

### PyPI: Repository URL (Optional but Recommended)

While not required for OIDC, it's good practice to include repository information in your `pyproject.toml`:

```toml
[project.urls]
Repository = "https://github.com/weirdfingers/boards"
```

## Automatic Provenance Generation

Both PyPI and NPM automatically generate provenance attestations when publishing via OIDC from public repositories. This provides cryptographic proof of:

- Where the package was built (which repository)
- How it was built (which workflow)
- When it was built

Users can verify the authenticity of your packages using these attestations.

## Troubleshooting

### PyPI Publishing Fails

- Verify the trusted publisher configuration matches exactly (organization, repo, workflow file)
- Ensure you're using a GitHub-hosted runner (self-hosted runners not supported)
- Check that `uv` is version 0.1.0 or later

### NPM Publishing Fails

- Verify npm CLI is version 11.5.1 or later (the workflow updates npm automatically)
- Ensure the workflow filename matches exactly (including `.yml` extension)
- Verify the trusted publisher configuration on npmjs.com
- Check that you're using GitHub-hosted runners

### OIDC Token Not Generated

- Verify `id-token: write` permission is set in the job
- Ensure you're running on ubuntu-latest or another GitHub-hosted runner
- Check GitHub Actions logs for any permission errors

## References

- [PyPI Trusted Publishers Documentation](https://docs.pypi.org/trusted-publishers/)
- [NPM Trusted Publishers Documentation](https://docs.npmjs.com/trusted-publishers)
- [GitHub Actions OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
