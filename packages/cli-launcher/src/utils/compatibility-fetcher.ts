/**
 * Compatibility Manifest Fetcher
 *
 * Utilities for fetching and caching compatibility manifests from GitHub Releases.
 * Handles downloading, validation, caching, and error handling for manifests.
 */

import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import type { CompatibilityManifest } from '../types/compatibility-manifest.js';
import compatibilitySchema from '../schemas/compatibility-manifest.schema.json' with { type: 'json' };

const GITHUB_REPO = 'weirdfingers/boards';
const CACHE_DIR = path.join(os.homedir(), '.baseboards', 'compatibility');

// Configure Ajv with format validators (includes uri format)
const ajv = new Ajv({ strict: false });
addFormats(ajv);
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
    if (error instanceof Error && error.name === 'AbortError') {
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
