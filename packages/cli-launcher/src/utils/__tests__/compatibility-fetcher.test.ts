import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import {
  fetchCompatibilityManifest,
  clearCompatibilityCache,
  getCachedVersions,
} from '../compatibility-fetcher.js';

const CACHE_DIR = path.join(os.homedir(), '.baseboards', 'compatibility');

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch as any;

describe('Compatibility Manifest Fetcher', () => {
  beforeEach(async () => {
    await clearCompatibilityCache();
    vi.clearAllMocks();
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
    mockFetch.mockImplementation((url, options: any) => {
      return new Promise((resolve, reject) => {
        // Simulate abort signal behavior
        if (options?.signal) {
          options.signal.addEventListener('abort', () => {
            const error = new Error('The operation was aborted');
            error.name = 'AbortError';
            reject(error);
          });
        }
      });
    });

    await expect(
      fetchCompatibilityManifest('0.8.0', { timeout: 100 })
    ).rejects.toThrow('Timeout fetching compatibility manifest');
  }, 5000);

  test('handles version strings with "v" prefix', async () => {
    const mockManifest = {
      version: '0.8.0',
      storageFormatVersion: '2',
    };

    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockManifest,
    } as any);

    // Test with "v" prefix
    await fetchCompatibilityManifest('v0.8.0');

    expect(mockFetch).toHaveBeenCalledWith(
      'https://github.com/weirdfingers/boards/releases/download/v0.8.0/compatibility-manifest.json',
      expect.any(Object)
    );
  });

  test('removes invalid cached manifest and fetches fresh', async () => {
    // Create invalid cached manifest (doesn't match schema)
    const cachePath = path.join(CACHE_DIR, 'compatibility-0.8.0.json');
    await fs.ensureDir(CACHE_DIR);
    await fs.writeFile(cachePath, JSON.stringify({ version: '0.8.0' }), 'utf-8');

    const mockManifest = {
      version: '0.8.0',
      storageFormatVersion: '2',
    };

    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockManifest,
    } as any);

    // Should remove invalid cache and fetch from network
    const result = await fetchCompatibilityManifest('0.8.0');
    expect(result).toEqual(mockManifest);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  test('clearCompatibilityCache removes all cached manifests', async () => {
    const mockManifest = {
      version: '0.8.0',
      storageFormatVersion: '2',
    };

    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockManifest,
    } as any);

    // Cache a manifest
    await fetchCompatibilityManifest('0.8.0');

    // Verify it's cached
    let cached = await getCachedVersions();
    expect(cached).toContain('0.8.0');

    // Clear cache
    await clearCompatibilityCache();

    // Verify cache is empty
    cached = await getCachedVersions();
    expect(cached).toHaveLength(0);
  });

  test('throws error for non-404 HTTP errors', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    } as any);

    await expect(
      fetchCompatibilityManifest('0.8.0')
    ).rejects.toThrow('Failed to fetch manifest: 500 Internal Server Error');
  });
});
