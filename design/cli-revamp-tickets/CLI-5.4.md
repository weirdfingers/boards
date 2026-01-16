# Handle Template Download Errors Gracefully

## Description

Implement comprehensive error handling for template download failures, providing clear, actionable error messages that help users diagnose and fix problems. This improves the reliability and user experience of the template system.

Error scenarios to handle:
- Network offline / connectivity issues
- Invalid version (template not found)
- Checksum mismatch (corrupted download)
- Disk space issues
- Permission errors
- GitHub API rate limiting
- Incomplete downloads (interrupted)

## Dependencies

- CLI-5.3 (Progress indicator, for integration)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/utils/template-downloader.ts`

## Testing

### Network Offline Test
```bash
# Disconnect network
# Clear cache
rm -rf ~/.baseboards/templates/*

# Try to download
baseboards up test --template basic

# Expected:
# Error: Failed to download template
# Cause: Network connection failed
# Suggestion: Check your internet connection and try again
#
# If you continue to have issues:
# - Verify you can access https://github.com
# - Check if you're behind a proxy
# - Try again later
```

### Invalid Version Test
```bash
# Try with non-existent version
# (Modify CLI version or use --backend-version if available)

# Expected:
# Error: Template manifest not found for version 99.99.99
# Suggestion: Check that version 99.99.99 has been released
# Available versions: 0.7.0, 0.8.0
```

### Checksum Mismatch Test
```bash
# Simulate corrupted download (manual test)
# Download template, corrupt cache file, try again

# Expected:
# Error: Template verification failed
# Cause: Downloaded file checksum does not match expected value
# Suggestion: The download may have been corrupted. Trying again...
# [Automatically re-downloads]
```

### Disk Full Test
```bash
# Simulate disk full (difficult to test)
# Expected:
# Error: Failed to save template
# Cause: Not enough disk space
# Suggestion: Free up disk space and try again
# Required: ~15 MB for baseboards template
```

### Permission Error Test
```bash
# Make cache directory read-only
chmod 444 ~/.baseboards/templates/

baseboards up test --template basic

# Expected:
# Error: Cannot write to cache directory
# Cause: Permission denied: ~/.baseboards/templates/
# Suggestion: Check file permissions or try running with appropriate permissions
```

### Rate Limiting Test
```bash
# Difficult to test, but should handle:
# Expected:
# Error: GitHub API rate limit exceeded
# Suggestion: Please try again later (rate limit resets in X minutes)
```

## Acceptance Criteria

### Error Classes

- [ ] Define custom error classes for clarity:
  ```typescript
  class TemplateDownloadError extends Error {
    constructor(
      message: string,
      public cause?: string,
      public suggestion?: string
    ) {
      super(message);
      this.name = "TemplateDownloadError";
    }
  }

  class TemplateNotFoundError extends TemplateDownloadError {}
  class NetworkError extends TemplateDownloadError {}
  class ChecksumError extends TemplateDownloadError {}
  class DiskSpaceError extends TemplateDownloadError {}
  ```

### Network Error Handling

- [ ] Catch network errors:
  ```typescript
  try {
    const response = await axios.get(url);
  } catch (error) {
    if (error.code === "ENOTFOUND" || error.code === "ECONNREFUSED") {
      throw new NetworkError(
        "Failed to download template",
        "Network connection failed",
        "Check your internet connection and try again"
      );
    }
    throw error;
  }
  ```

- [ ] Detect common network issues:
  - [ ] DNS resolution failure (ENOTFOUND)
  - [ ] Connection refused (ECONNREFUSED)
  - [ ] Timeout (ETIMEDOUT)
  - [ ] SSL errors (CERT_)

### Version Error Handling

- [ ] Handle missing versions:
  ```typescript
  try {
    const manifest = await fetchTemplateManifest(version);
  } catch (error) {
    if (error.response?.status === 404) {
      throw new TemplateNotFoundError(
        `Template manifest not found for version ${version}`,
        `Version ${version} may not be released yet`,
        `Check available versions at: https://github.com/weirdfingers/boards/releases`
      );
    }
    throw error;
  }
  ```

### Checksum Error Handling

- [ ] Handle checksum mismatches with retry:
  ```typescript
  const maxRetries = 2;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      await verifyChecksum(tempPath, expected);
      break; // Success
    } catch (error) {
      if (attempt < maxRetries) {
        console.log(`Checksum verification failed. Retrying download (attempt ${attempt + 1}/${maxRetries})...`);
        // Clean up and retry
        fs.unlinkSync(tempPath);
        continue;
      } else {
        throw new ChecksumError(
          "Template verification failed",
          "Downloaded file is corrupted",
          "Please try again. If the problem persists, report it at: https://github.com/weirdfingers/boards/issues"
        );
      }
    }
  }
  ```

### Disk Space Error Handling

- [ ] Detect disk space issues:
  ```typescript
  try {
    fs.writeFileSync(tempPath, data);
  } catch (error) {
    if (error.code === "ENOSPC") {
      throw new DiskSpaceError(
        "Failed to save template",
        "Not enough disk space",
        `Free up disk space and try again. Required: ~${formatBytes(template.size)}`
      );
    }
    throw error;
  }
  ```

### Permission Error Handling

- [ ] Detect permission issues:
  ```typescript
  try {
    fs.mkdirSync(cacheDir, { recursive: true });
  } catch (error) {
    if (error.code === "EACCES") {
      throw new Error(
        `Cannot write to cache directory\nCause: Permission denied: ${cacheDir}\nSuggestion: Check file permissions or try running with appropriate permissions`
      );
    }
    throw error;
  }
  ```

### Error Display

- [ ] Format errors consistently:
  ```typescript
  function displayError(error: TemplateDownloadError): void {
    console.error(`\n❌ ${error.message}`);

    if (error.cause) {
      console.error(`Cause: ${error.cause}`);
    }

    if (error.suggestion) {
      console.error(`\nSuggestion: ${error.suggestion}`);
    }

    console.error(); // Empty line
  }
  ```

### Cleanup on Error

- [ ] Clean up partial downloads:
  ```typescript
  try {
    await downloadTemplate(name, version, targetDir);
  } catch (error) {
    // Clean up partial files
    if (fs.existsSync(tempPath)) {
      fs.unlinkSync(tempPath);
    }

    // Clean up partial extraction
    if (fs.existsSync(targetDir)) {
      fs.rmSync(targetDir, { recursive: true, force: true });
    }

    displayError(error);
    process.exit(1);
  }
  ```

### Rate Limiting

- [ ] Handle GitHub rate limits:
  ```typescript
  if (error.response?.status === 429) {
    const resetTime = error.response.headers["x-ratelimit-reset"];
    const resetDate = new Date(resetTime * 1000);
    const minutesUntilReset = Math.ceil((resetDate - new Date()) / 60000);

    throw new Error(
      `GitHub API rate limit exceeded\nPlease try again in ${minutesUntilReset} minutes`
    );
  }
  ```

### Retry Logic

- [ ] Implement smart retry for transient failures:
  ```typescript
  const transientErrors = ["ETIMEDOUT", "ECONNRESET", "ECONNREFUSED"];
  const maxRetries = 3;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await downloadFile(url);
    } catch (error) {
      if (transientErrors.includes(error.code) && attempt < maxRetries) {
        console.log(`Download failed (${error.code}). Retrying...`);
        await sleep(1000 * attempt); // Exponential backoff
        continue;
      }
      throw error;
    }
  }
  ```

### User-Friendly Messages

- [ ] All errors include:
  - [ ] Clear description of what failed
  - [ ] Explanation of why (if known)
  - [ ] Actionable suggestion to fix
  - [ ] Link to docs/issues if appropriate

### Quality

- [ ] No generic "Error" messages
- [ ] No stack traces shown to users (unless --verbose flag)
- [ ] Error messages are actionable
- [ ] Consistent formatting across all errors
- [ ] Errors logged for debugging (in verbose mode)

### Testing

- [ ] Network offline handled
- [ ] Invalid version handled
- [ ] Checksum mismatch handled with retry
- [ ] Disk space issues detected
- [ ] Permission errors detected
- [ ] Partial downloads cleaned up
- [ ] All error messages clear and helpful
- [ ] No crashes or uncaught exceptions
