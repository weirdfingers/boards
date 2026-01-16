# Implement Template Cache Management

## Description

Implement local caching for downloaded templates to avoid re-downloading on subsequent scaffolds. Templates should be cached in the user's home directory (`~/.baseboards/templates/`) with version-specific organization.

The cache system should:
- Cache templates after first download
- Check cache before downloading
- Support multiple versions simultaneously
- Verify cached files with checksums
- Provide cache cleanup utilities
- Be transparent to the download logic

This significantly improves the user experience by making repeated scaffolds nearly instant.

## Dependencies

- CLI-2.5 (Template downloader must exist)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/utils/template-downloader.ts` (add cache logic)

## Testing

### Cache Directory Test
```typescript
import { getCacheDir } from "./template-downloader";

const cacheDir = getCacheDir();
console.log(cacheDir); // Should be ~/.baseboards/templates/

// Verify directory is created
const fs = require("fs");
console.log(fs.existsSync(cacheDir)); // true
```

### Cache Hit Test
```typescript
import { downloadTemplate } from "./template-downloader";

// First download (cache miss)
console.time("first-download");
await downloadTemplate("basic", "0.8.0", "/tmp/test1");
console.timeEnd("first-download"); // ~5 seconds (downloads from GitHub)

// Second download (cache hit)
console.time("second-download");
await downloadTemplate("basic", "0.8.0", "/tmp/test2");
console.timeEnd("second-download"); // ~500ms (extracts from cache)
```

### Multi-Version Cache Test
```typescript
// Download v0.8.0
await downloadTemplate("basic", "0.8.0", "/tmp/test-v0.8.0");

// Download v0.7.0
await downloadTemplate("basic", "0.7.0", "/tmp/test-v0.7.0");

// Verify both cached
const cache = getCacheDir();
console.log(fs.existsSync(`${cache}/template-basic-v0.8.0.tar.gz`)); // true
console.log(fs.existsSync(`${cache}/template-basic-v0.7.0.tar.gz`)); // true
```

### Cache Invalidation Test
```typescript
import { clearCache } from "./template-downloader";

// Download and cache
await downloadTemplate("basic", "0.8.0", "/tmp/test");

// Clear cache
await clearCache();

// Verify cache is empty
const cache = getCacheDir();
const files = fs.readdirSync(cache);
console.log(files.length); // 0 (cache cleared)
```

### Checksum Verification Test
```typescript
// Simulate corrupted cache
const cache = getCacheDir();
const cachedFile = `${cache}/template-basic-v0.8.0.tar.gz`;

// Download once (should cache)
await downloadTemplate("basic", "0.8.0", "/tmp/test1");

// Corrupt the cached file
fs.writeFileSync(cachedFile, "corrupted data");

// Download again (should detect corruption and re-download)
await downloadTemplate("basic", "0.8.0", "/tmp/test2");

// Verify new file is valid
const manifest = await fetchTemplateManifest("0.8.0");
const template = manifest.templates.find(t => t.name === "basic");
const valid = await verifyChecksum(cachedFile, template.checksum);
console.log(valid); // true (re-downloaded and verified)
```

### Cache Structure Test
```bash
# Verify cache directory structure
ls -la ~/.baseboards/templates/
# Should show:
# template-baseboards-v0.8.0.tar.gz
# template-basic-v0.8.0.tar.gz
# manifest-v0.8.0.json (cached manifest)
```

## Acceptance Criteria

### Core Functionality

- [ ] Cache directory created at `~/.baseboards/templates/`
- [ ] Cache directory path uses `os.homedir()` for cross-platform support
- [ ] Cache directory created automatically if missing

### Cache Logic

- [ ] `downloadTemplate()` checks cache before downloading:
  - [ ] Look for cached file: `~/.baseboards/templates/template-{name}-v{version}.tar.gz`
  - [ ] If found, verify checksum
  - [ ] If checksum valid, extract from cache
  - [ ] If checksum invalid, delete and re-download
  - [ ] If not found, download and cache

- [ ] Downloaded files saved to cache after successful download
- [ ] Cached manifest: `~/.baseboards/templates/manifest-v{version}.json`
- [ ] Manifest cached alongside templates for faster lookups

### Cache Management

- [ ] `clearCache(): Promise<void>` function implemented
  - [ ] Deletes all files in cache directory
  - [ ] Preserves directory itself
  - [ ] Handles errors gracefully

- [ ] `clearTemplateCache(name: string, version: string): Promise<void>` function implemented
  - [ ] Deletes specific template from cache
  - [ ] Useful for forcing re-download

- [ ] `getCacheSize(): Promise<number>` function implemented (optional)
  - [ ] Returns total cache size in bytes
  - [ ] Useful for doctor command

### Error Handling

- [ ] Handles permission errors (can't write to home directory)
- [ ] Handles disk full errors
- [ ] Handles concurrent access (multiple CLI instances)
- [ ] Atomic writes (tmp file + rename) to prevent partial writes

### Quality

- [ ] Cache logic doesn't break existing tests
- [ ] Performance improvement measurable (second scaffold much faster)
- [ ] Cache size reasonable (only tarballs, no extracted files)
- [ ] Cache doesn't grow unbounded (or document cleanup strategy)
- [ ] Cross-platform (works on macOS, Linux, Windows)

### Documentation

- [ ] JSDoc comments for cache functions
- [ ] README note about cache location
- [ ] Cache clearing documented in help text
