# Implement Template Download Logic

## Description

Create a utility module for downloading templates from GitHub Releases, validating their checksums, and extracting them to a target directory. This is the core functionality that enables the CLI to fetch templates on-demand instead of bundling them.

The template downloader should:
- Fetch the template manifest from GitHub Releases API
- Download specified template tarball
- Validate checksum before extraction
- Handle network errors gracefully
- Provide progress feedback
- Support version-specific downloads
- Integrate with cache (to be implemented in CLI-2.6)

This module will be used by the `up` command and `templates` command.

## Dependencies

- CLI-2.4 (Templates must be published to test against)

## Files to Create/Modify

- Create `/packages/cli-launcher/src/utils/template-downloader.ts`

## Testing

### Fetch Manifest Test
```typescript
import { fetchTemplateManifest } from "./template-downloader";

// Test fetching specific version
const manifest = await fetchTemplateManifest("0.8.0");
console.log(manifest.templates); // Should list baseboards and basic

// Test latest version
const latestManifest = await fetchTemplateManifest("latest");
console.log(latestManifest.version);
```

### Download Template Test
```typescript
import { downloadTemplate } from "./template-downloader";

// Test downloading specific template
await downloadTemplate(
  "basic",           // template name
  "0.8.0",          // version
  "/tmp/test-project" // target directory
);

// Verify files extracted
const fs = require("fs");
console.log(fs.existsSync("/tmp/test-project/web/package.json")); // true
```

### Checksum Validation Test
```typescript
// Test with corrupted file
const corruptedFile = "/tmp/corrupted.tar.gz";
fs.writeFileSync(corruptedFile, "invalid data");

try {
  await verifyChecksum(corruptedFile, "sha256:abc123");
  console.log("Should have thrown error!");
} catch (error) {
  console.log("Correctly caught checksum mismatch:", error.message);
}
```

### Error Handling Test
```typescript
// Test network error
try {
  await downloadTemplate("nonexistent", "0.8.0", "/tmp/test");
} catch (error) {
  console.log("Correctly caught error:", error.message);
  // Should provide helpful error message
}

// Test invalid version
try {
  await fetchTemplateManifest("99.99.99");
} catch (error) {
  console.log("Correctly caught version error:", error.message);
}
```

### Integration Test
```bash
# Run test script that exercises downloader
cd packages/cli-launcher
pnpm test src/utils/template-downloader.test.ts
```

## Acceptance Criteria

### Core Functions

- [ ] `fetchTemplateManifest(version: string): Promise<TemplateManifest>` implemented
  - [ ] Fetches from `https://github.com/weirdfingers/boards/releases/download/v{version}/template-manifest.json`
  - [ ] Handles 404 (version not found) with clear error
  - [ ] Handles network errors with retry logic
  - [ ] Parses JSON and validates schema

- [ ] `downloadTemplate(name: string, version: string, targetDir: string): Promise<void>` implemented
  - [ ] Fetches manifest first to get template metadata
  - [ ] Downloads tarball from GitHub Release
  - [ ] Saves to temporary location
  - [ ] Verifies checksum matches manifest
  - [ ] Extracts to target directory
  - [ ] Cleans up temporary files on success/failure

- [ ] `verifyChecksum(filePath: string, expectedChecksum: string): Promise<boolean>` implemented
  - [ ] Calculates SHA-256 hash of file
  - [ ] Compares with expected (format: "sha256:abcd123...")
  - [ ] Returns true if match, throws error if mismatch

### Error Handling

- [ ] Network failures handled gracefully
- [ ] Invalid versions return helpful error message
- [ ] Template not found in manifest throws clear error
- [ ] Checksum mismatches throw error with details
- [ ] Corrupted tarballs handled (extraction fails gracefully)
- [ ] Permission errors handled (can't write to target directory)

### Types

- [ ] TypeScript interfaces defined:
  ```typescript
  interface TemplateManifest {
    version: string;
    templates: TemplateInfo[];
  }

  interface TemplateInfo {
    name: string;
    description: string;
    file: string;
    size: number;
    checksum: string;
    frameworks: string[];
    features: string[];
  }
  ```

### Quality

- [ ] Uses axios or similar for HTTP requests
- [ ] Uses tar library for extraction
- [ ] Includes JSDoc comments
- [ ] Follows CLI package code style
- [ ] Unit tests cover main success paths
- [ ] Unit tests cover error paths
- [ ] Mocks GitHub API in tests (no real network calls)
