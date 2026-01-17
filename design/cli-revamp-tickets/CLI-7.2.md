# CLI-7.2: Implement Compatibility Manifest Fetcher

## Description

Implement utility functions to fetch and parse compatibility manifests from GitHub Releases. This module will handle downloading manifests, caching them locally, validating their schema, and providing error handling for network failures or missing manifests.

The fetcher needs to:
- Download manifests from GitHub Release assets
- Validate manifest structure against the JSON schema
- Cache manifests locally to avoid repeated downloads
- Handle missing manifests gracefully (for older releases)
- Support fetching multiple manifests for multi-version upgrades

## Dependencies

- CLI-7.1 (Compatibility Manifest Schema)

## Files to Create/Modify

### New Files
- `packages/cli-launcher/src/utils/compatibility-fetcher.ts` - Main fetcher implementation
- `packages/cli-launcher/src/utils/__tests__/compatibility-fetcher.test.ts` - Tests

## Implementation Details

### Fetcher Implementation

```typescript
// packages/cli-launcher/src/utils/compatibility-fetcher.ts

import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import fetch from 'node-fetch';
import Ajv from 'ajv';
import type { CompatibilityManifest } from '../types/compatibility-manifest.js';
import compatibilitySchema from '../schemas/compatibility-manifest.schema.json';

const GITHUB_REPO = 'weirdfingers/boards';
const CACHE_DIR = path.join(os.homedir(), '.baseboards', 'compatibility');

const ajv = new Ajv();
const validateManifest = ajv.compile(compatibilitySchema);

export interface FetchOptions {
  /** Force re-download even if cached */
  forceRefresh?: boolean;
  /** Timeout in milliseconds (default: 10000) */
  timeout?: number;
}

/**
 * Fetch compatibility manifest for a specific version from GitHub Releases
 */
export async function fetchCompatibilityManifest(
  version: string,
  options: FetchOptions = {}
): Promise<CompatibilityManifest | null> {
  const { forceRefresh = false, timeout = 10000 } = options;

  // Check cache first
  if (!forceRefresh) {
    const cached = await loadFromCache(version);
    if (cached) {
      return cached;
    }
  }

  // Fetch from GitHub
  const url = getManifestUrl(version);

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status === 404) {
        // Manifest doesn't exist for this version (likely older release)
        return null;
      }
      throw new Error(`Failed to fetch manifest: ${response.status} ${response.statusText}`);
    }

    const manifest = await response.json() as CompatibilityManifest;

    // Validate schema
    if (!validateManifest(manifest)) {
      throw new Error(`Invalid manifest schema: ${JSON.stringify(validateManifest.errors)}`);
    }

    // Cache for future use
    await saveToCache(version, manifest);

    return manifest;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`Timeout fetching compatibility manifest for v${version}`);
    }
    throw error;
  }
}

/**
 * Fetch manifests for all versions between current and target
 */
export async function fetchManifestsForRange(
  currentVersion: string,
  targetVersion: string,
  options: FetchOptions = {}
): Promise<CompatibilityManifest[]> {
  // This will be implemented in CLI-7.3 using semver to get intermediate versions
  // For now, just fetch the target version
  const manifest = await fetchCompatibilityManifest(targetVersion, options);
  return manifest ? [manifest] : [];
}

/**
 * Get the GitHub Release URL for a compatibility manifest
 */
function getManifestUrl(version: string): string {
  // Remove "v" prefix if present
  const cleanVersion = version.replace(/^v/, '');
  return `https://github.com/${GITHUB_REPO}/releases/download/v${cleanVersion}/compatibility-manifest.json`;
}

/**
 * Load manifest from local cache
 */
async function loadFromCache(version: string): Promise<CompatibilityManifest | null> {
  const cachePath = getCachePath(version);

  if (!await fs.pathExists(cachePath)) {
    return null;
  }

  try {
    const content = await fs.readFile(cachePath, 'utf-8');
    const manifest = JSON.parse(content) as CompatibilityManifest;

    // Validate cached manifest
    if (!validateManifest(manifest)) {
      // Invalid cache, remove it
      await fs.remove(cachePath);
      return null;
    }

    return manifest;
  } catch (error) {
    // Corrupted cache, remove it
    await fs.remove(cachePath).catch(() => {});
    return null;
  }
}

/**
 * Save manifest to local cache
 */
async function saveToCache(version: string, manifest: CompatibilityManifest): Promise<void> {
  const cachePath = getCachePath(version);
  await fs.ensureDir(CACHE_DIR);
  await fs.writeFile(cachePath, JSON.stringify(manifest, null, 2), 'utf-8');
}

/**
 * Get cache file path for a version
 */
function getCachePath(version: string): string {
  const cleanVersion = version.replace(/^v/, '');
  return path.join(CACHE_DIR, `compatibility-${cleanVersion}.json`);
}

/**
 * Clear compatibility manifest cache
 */
export async function clearCompatibilityCache(): Promise<void> {
  if (await fs.pathExists(CACHE_DIR)) {
    await fs.remove(CACHE_DIR);
  }
}

/**
 * Get list of cached manifest versions
 */
export async function getCachedVersions(): Promise<string[]> {
  if (!await fs.pathExists(CACHE_DIR)) {
    return [];
  }

  const files = await fs.readdir(CACHE_DIR);
  return files
    .filter(f => f.startsWith('compatibility-') && f.endsWith('.json'))
    .map(f => f.replace('compatibility-', '').replace('.json', ''));
}
```

## Testing

### Unit Tests

```typescript
// packages/cli-launcher/src/utils/__tests__/compatibility-fetcher.test.ts

import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import { jest } from '@jest/globals';
import {
  fetchCompatibilityManifest,
  clearCompatibilityCache,
  getCachedVersions,
} from '../compatibility-fetcher.js';

// Mock node-fetch
jest.mock('node-fetch');
import fetch from 'node-fetch';
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

const CACHE_DIR = path.join(os.homedir(), '.baseboards', 'compatibility');

describe('Compatibility Manifest Fetcher', () => {
  beforeEach(async () => {
    await clearCompatibilityCache();
    jest.clearAllMocks();
  });

  afterEach(async () => {
    await clearCompatibilityCache();
  });

  test('fetches and validates manifest from GitHub', async () => {
    const mockManifest = {
      version: '0.8.0',
      storageFormatVersion: '2',
    };

    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockManifest,
    } as any);

    const result = await fetchCompatibilityManifest('0.8.0');

    expect(result).toEqual(mockManifest);
    expect(mockFetch).toHaveBeenCalledWith(
      'https://github.com/weirdfingers/boards/releases/download/v0.8.0/compatibility-manifest.json',
      expect.any(Object)
    );
  });

  test('returns null for 404 (missing manifest)', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    } as any);

    const result = await fetchCompatibilityManifest('0.6.0');

    expect(result).toBeNull();
  });

  test('throws error for network failures', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));

    await expect(
      fetchCompatibilityManifest('0.8.0')
    ).rejects.toThrow('Network error');
  });

  test('throws error for invalid manifest schema', async () => {
    const invalidManifest = {
      version: '0.8.0',
      // Missing required storageFormatVersion
    };

    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => invalidManifest,
    } as any);

    await expect(
      fetchCompatibilityManifest('0.8.0')
    ).rejects.toThrow('Invalid manifest schema');
  });

  test('caches manifest after first fetch', async () => {
    const mockManifest = {
      version: '0.8.0',
      storageFormatVersion: '2',
    };

    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockManifest,
    } as any);

    // First fetch
    await fetchCompatibilityManifest('0.8.0');
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Second fetch should use cache
    const result = await fetchCompatibilityManifest('0.8.0');
    expect(result).toEqual(mockManifest);
    expect(mockFetch).toHaveBeenCalledTimes(1); // Not called again
  });

  test('bypasses cache with forceRefresh option', async () => {
    const mockManifest = {
      version: '0.8.0',
      storageFormatVersion: '2',
    };

    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockManifest,
    } as any);

    // First fetch
    await fetchCompatibilityManifest('0.8.0');
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Force refresh
    await fetchCompatibilityManifest('0.8.0', { forceRefresh: true });
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  test('removes corrupted cache files', async () => {
    // Create corrupted cache file
    const cachePath = path.join(CACHE_DIR, 'compatibility-0.8.0.json');
    await fs.ensureDir(CACHE_DIR);
    await fs.writeFile(cachePath, 'invalid json{', 'utf-8');

    const mockManifest = {
      version: '0.8.0',
      storageFormatVersion: '2',
    };

    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockManifest,
    } as any);

    // Should fetch from network (cache is corrupted)
    const result = await fetchCompatibilityManifest('0.8.0');
    expect(result).toEqual(mockManifest);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  test('getCachedVersions returns list of cached versions', async () => {
    const mockManifest1 = { version: '0.7.0', storageFormatVersion: '1' };
    const mockManifest2 = { version: '0.8.0', storageFormatVersion: '2' };

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockManifest1,
      } as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockManifest2,
      } as any);

    await fetchCompatibilityManifest('0.7.0');
    await fetchCompatibilityManifest('0.8.0');

    const cached = await getCachedVersions();
    expect(cached).toContain('0.7.0');
    expect(cached).toContain('0.8.0');
  });

  test('handles timeout gracefully', async () => {
    mockFetch.mockImplementation(() =>
      new Promise((resolve) => {
        // Never resolves
      })
    );

    await expect(
      fetchCompatibilityManifest('0.8.0', { timeout: 100 })
    ).rejects.toThrow('Timeout fetching compatibility manifest');
  }, 10000);
});
```

## Acceptance Criteria

- [ ] `fetchCompatibilityManifest()` downloads manifest from GitHub Releases
- [ ] Returns `null` for 404 (missing manifest for older versions)
- [ ] Throws error for network failures
- [ ] Validates manifest against JSON schema
- [ ] Caches valid manifests in `~/.baseboards/compatibility/`
- [ ] Uses cached manifest on subsequent calls (unless `forceRefresh: true`)
- [ ] Removes corrupted cache files automatically
- [ ] Supports custom timeout option
- [ ] `clearCompatibilityCache()` deletes all cached manifests
- [ ] `getCachedVersions()` lists all cached version numbers
- [ ] All unit tests pass
- [ ] Handles network timeouts gracefully
- [ ] Handles version strings with or without "v" prefix

## Notes

- Cache directory: `~/.baseboards/compatibility/compatibility-{version}.json`
- Default timeout: 10 seconds
- Manifest validation uses Ajv with the JSON schema from CLI-7.1
- For older versions without manifests, return `null` (not an error)
- The fetcher should be resilient to GitHub API rate limiting (cache helps)
