# Add Template Download Integration Tests

## Description

Create automated integration tests for the template downloader module to ensure reliability and catch regressions. Tests should cover the full download workflow, caching behavior, error handling, and edge cases.

These tests provide confidence that the template system works correctly across different scenarios.

## Dependencies

- CLI-2.5 (Template downloader implementation)

## Files to Create/Modify

- Create `/packages/cli-launcher/tests/template-downloader.test.ts`

## Testing

### Run Tests
```bash
cd packages/cli-launcher
pnpm test template-downloader.test.ts

# Should: All tests pass
# Should: Coverage report shows >80% coverage
```

### Test in CI
```bash
# Tests should run in CI pipeline
# Should pass consistently
```

## Acceptance Criteria

### Test Setup

- [ ] Test file created at correct path
- [ ] Uses testing framework (Jest, Vitest, or existing)
- [ ] Mock GitHub API calls (no real network requests)
- [ ] Mock filesystem operations where appropriate
- [ ] Setup and teardown functions

### Core Functionality Tests

- [ ] **fetchTemplateManifest** tests:
  ```typescript
  describe("fetchTemplateManifest", () => {
    it("should fetch manifest from GitHub Release", async () => {
      // Mock successful API response
      // Assert manifest returned with correct structure
    });

    it("should handle 404 for invalid version", async () => {
      // Mock 404 response
      // Assert appropriate error thrown
    });

    it("should parse manifest JSON correctly", async () => {
      // Mock valid manifest
      // Assert all fields present and correct types
    });
  });
  ```

- [ ] **downloadTemplate** tests:
  ```typescript
  describe("downloadTemplate", () => {
    it("should download and extract template", async () => {
      // Mock download and extraction
      // Assert files created in target directory
    });

    it("should verify checksum", async () => {
      // Mock download
      // Assert checksum verification called
    });

    it("should throw on checksum mismatch", async () => {
      // Mock corrupted download
      // Assert error thrown
    });
  });
  ```

- [ ] **verifyChecksum** tests:
  ```typescript
  describe("verifyChecksum", () => {
    it("should return true for matching checksum", async () => {
      // Create file with known content
      // Calculate expected checksum
      // Assert verification passes
    });

    it("should throw for mismatching checksum", async () => {
      // Create file with known content
      // Provide wrong checksum
      // Assert error thrown with details
    });
  });
  ```

### Caching Tests

- [ ] **Cache behavior** tests:
  ```typescript
  describe("template cache", () => {
    it("should cache downloaded template", async () => {
      // Mock download
      // Assert file saved in cache directory
    });

    it("should use cached template on second call", async () => {
      // First call: mock download
      // Second call: assert no download (cache hit)
    });

    it("should validate cached template checksum", async () => {
      // Mock cache with file
      // Mock checksum validation
      // Assert validation called before use
    });

    it("should re-download if cache corrupted", async () => {
      // Mock cache with corrupted file
      // Assert re-download triggered
    });
  });
  ```

- [ ] **clearCache** tests:
  ```typescript
  describe("clearCache", () => {
    it("should delete all cached templates", async () => {
      // Create cached files
      // Call clearCache
      // Assert files deleted
    });

    it("should not error on empty cache", async () => {
      // Empty cache directory
      // Call clearCache
      // Assert no error
    });
  });
  ```

### Error Handling Tests

- [ ] **Network errors**:
  ```typescript
  it("should handle network timeout", async () => {
    // Mock timeout
    // Assert appropriate error
  });

  it("should handle connection refused", async () => {
    // Mock ECONNREFUSED
    // Assert appropriate error
  });

  it("should handle DNS failure", async () => {
    // Mock ENOTFOUND
    // Assert appropriate error
  });
  ```

- [ ] **GitHub API errors**:
  ```typescript
  it("should handle rate limiting", async () => {
    // Mock 429 response
    // Assert error mentions rate limit
  });

  it("should handle 404 not found", async () => {
    // Mock 404 response
    // Assert error mentions version/template not found
  });
  ```

- [ ] **Filesystem errors**:
  ```typescript
  it("should handle permission denied", async () => {
    // Mock EACCES
    // Assert appropriate error
  });

  it("should handle disk full", async () => {
    // Mock ENOSPC
    // Assert appropriate error
  });
  ```

### Edge Cases

- [ ] **Empty manifest**:
  ```typescript
  it("should handle manifest with no templates", async () => {
    // Mock empty templates array
    // Assert appropriate error or empty result
  });
  ```

- [ ] **Invalid JSON**:
  ```typescript
  it("should handle malformed manifest JSON", async () => {
    // Mock invalid JSON response
    // Assert parse error caught
  });
  ```

- [ ] **Missing fields**:
  ```typescript
  it("should handle manifest missing required fields", async () => {
    // Mock manifest missing checksum/size/etc
    // Assert validation error
  });
  ```

- [ ] **Large files**:
  ```typescript
  it("should handle large template downloads", async () => {
    // Mock large file (>100MB)
    // Assert progress tracking works
    // Assert memory usage reasonable
  });
  ```

### Mocking Strategy

- [ ] Mock axios for HTTP requests
- [ ] Mock fs operations where appropriate
- [ ] Mock crypto for checksum calculations (if needed)
- [ ] Use test fixtures for manifest/template data

### Test Utilities

- [ ] Helper functions for common setup:
  ```typescript
  function mockManifest(templates: TemplateInfo[]): void;
  function mockDownload(templateName: string, success: boolean): void;
  function createTestCache(): string; // Returns temp cache dir
  ```

### Coverage

- [ ] Overall coverage >80%
- [ ] All exported functions covered
- [ ] All error paths covered
- [ ] Main success paths covered

### Quality

- [ ] Tests are deterministic (no flaky tests)
- [ ] Tests run quickly (< 5 seconds total)
- [ ] Tests are independent (can run in any order)
- [ ] Clear test descriptions
- [ ] No real network calls
- [ ] No real filesystem dependencies (use temp dirs)

### Documentation

- [ ] Test file has header comment explaining scope
- [ ] Complex test cases documented
- [ ] Mock strategies explained
