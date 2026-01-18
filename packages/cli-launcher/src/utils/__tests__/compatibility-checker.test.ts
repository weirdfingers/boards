import { describe, test, expect, beforeEach, vi } from 'vitest';
import {
  checkCompatibility,
  checkMultiVersionCompatibility,
  formatCompatibilityWarnings,
} from '../compatibility-checker.js';
import * as fetcher from '../compatibility-fetcher.js';

vi.mock('../compatibility-fetcher.js');

const mockFetchCompatibilityManifest = vi.mocked(fetcher.fetchCompatibilityManifest);

describe('Compatibility Checker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('detects breaking changes that affect current version', async () => {
    mockFetchCompatibilityManifest.mockResolvedValue({
      version: '0.8.0',
      storageFormatVersion: '2',
      breakingChanges: [
        {
          affectedVersions: '>=0.7.0 <0.8.0',
          description: 'Board.tags removed',
          mitigation: 'Use Board.metadata.tags',
        },
      ],
    });

    const result = await checkCompatibility('0.7.0', '0.8.0');

    expect(result.breaking).toBe(true);
    expect(result.warnings).toContain('⚠️  This upgrade contains breaking changes!');
    expect(result.warnings.some((w) => w.includes('Board.tags removed'))).toBe(true);
  });

  test('ignores breaking changes that do not affect current version', async () => {
    mockFetchCompatibilityManifest.mockResolvedValue({
      version: '0.8.0',
      storageFormatVersion: '2',
      breakingChanges: [
        {
          affectedVersions: '>=0.5.0 <0.6.0', // Does not affect 0.7.0
          description: 'Old breaking change',
          mitigation: 'Not relevant',
        },
      ],
    });

    const result = await checkCompatibility('0.7.0', '0.8.0');

    expect(result.breaking).toBe(false);
    expect(result.warnings).toHaveLength(0);
  });

  test('handles missing manifest gracefully', async () => {
    mockFetchCompatibilityManifest.mockResolvedValue(null);

    const result = await checkCompatibility('0.6.0', '0.7.0');

    expect(result.breaking).toBe(false);
    expect(result.warnings).toContain('⚠️  No compatibility manifest found for this version');
  });

  test('includes migration notes URL when available', async () => {
    mockFetchCompatibilityManifest.mockResolvedValue({
      version: '0.8.0',
      storageFormatVersion: '2',
      breakingChanges: [
        {
          affectedVersions: '>=0.7.0 <0.8.0',
          description: 'Breaking change',
          mitigation: 'Fix it',
        },
      ],
      migrationNotes: 'https://github.com/weirdfingers/boards/releases/tag/v0.8.0',
    });

    const result = await checkCompatibility('0.7.0', '0.8.0');

    expect(result.migrationNotes).toBe(
      'https://github.com/weirdfingers/boards/releases/tag/v0.8.0'
    );
    expect(
      result.warnings.some((w) => w.includes('https://github.com/weirdfingers/boards/releases'))
    ).toBe(true);
  });

  test('includes required actions', async () => {
    mockFetchCompatibilityManifest.mockResolvedValue({
      version: '0.8.0',
      storageFormatVersion: '2',
      requiredActions: ['Update .env files', 'Restart Docker'],
    });

    const result = await checkCompatibility('0.7.0', '0.8.0');

    expect(result.requiredActions).toEqual(['Update .env files', 'Restart Docker']);
  });

  test('formats warnings with required actions', () => {
    const check = {
      fromVersion: '0.7.0',
      toVersion: '0.8.0',
      breaking: true,
      warnings: ['⚠️  Breaking changes detected'],
      requiredActions: ['Action 1', 'Action 2'],
    };

    const formatted = formatCompatibilityWarnings(check);

    expect(formatted).toContain('⚠️  Breaking changes detected');
    expect(formatted).toContain('⚠️  Required manual actions:');
    expect(formatted).toContain('   • Action 1');
    expect(formatted).toContain('   • Action 2');
  });

  test('multi-version check aggregates breaking changes', async () => {
    // Mock will be called with target version only (simplified implementation)
    mockFetchCompatibilityManifest.mockResolvedValue({
      version: '0.9.0',
      storageFormatVersion: '3',
      breakingChanges: [
        {
          affectedVersions: '>=0.6.0 <0.9.0',
          description: 'Multiple version breaking change',
          mitigation: 'Upgrade carefully',
        },
      ],
    });

    const result = await checkMultiVersionCompatibility('0.6.0', '0.9.0');

    expect(result.breaking).toBe(true);
    expect(result.warnings.some((w) => w.includes('Multiple version breaking change'))).toBe(true);
  });
});
