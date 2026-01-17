# CLI-7.3: Implement Version Compatibility Checker

## Description

Implement the core logic for checking version compatibility during upgrades. This module uses the compatibility manifest to determine if an upgrade has breaking changes, generate warnings, and aggregate compatibility information across multiple version jumps.

The compatibility checker needs to:
- Compare current version against manifest's breaking changes using semver
- Generate user-friendly warnings and migration instructions
- Handle multi-version upgrades (e.g., 0.6.0 → 0.9.0)
- Check storage format compatibility
- Aggregate all breaking changes and required actions

## Dependencies

- CLI-7.1 (Compatibility Manifest Schema)
- CLI-7.2 (Compatibility Manifest Fetcher)

## Files to Create/Modify

### New Files
- `packages/cli-launcher/src/utils/compatibility-checker.ts` - Main checker implementation
- `packages/cli-launcher/src/utils/__tests__/compatibility-checker.test.ts` - Tests

## Implementation Details

### Compatibility Checker Implementation

```typescript
// packages/cli-launcher/src/utils/compatibility-checker.ts

import semver from 'semver';
import type {
  CompatibilityManifest,
  CompatibilityCheck,
  BreakingChange,
} from '../types/compatibility-manifest.js';
import { fetchCompatibilityManifest } from './compatibility-fetcher.js';

/**
 * Check compatibility between current and target versions
 */
export async function checkCompatibility(
  currentVersion: string,
  targetVersion: string
): Promise<CompatibilityCheck> {
  // Fetch manifest for target version
  const manifest = await fetchCompatibilityManifest(targetVersion);

  if (!manifest) {
    // No manifest available (likely older version)
    return {
      fromVersion: currentVersion,
      toVersion: targetVersion,
      breaking: false,
      warnings: [
        '⚠️  No compatibility manifest found for this version',
        '   This may be an older release. Proceed with caution.',
      ],
      requiredActions: [],
    };
  }

  // Check for breaking changes that affect current version
  const affectedBreakingChanges = (manifest.breakingChanges || []).filter(
    (bc) => isVersionAffected(currentVersion, bc.affectedVersions)
  );

  const breaking = affectedBreakingChanges.length > 0;

  // Build warnings
  const warnings: string[] = [];

  if (breaking) {
    warnings.push('⚠️  This upgrade contains breaking changes!');
    if (manifest.migrationNotes) {
      warnings.push(`   See: ${manifest.migrationNotes}`);
    }
    warnings.push('');

    // List each breaking change
    affectedBreakingChanges.forEach((bc) => {
      warnings.push(`   • ${bc.description}`);
      warnings.push(`     → ${bc.mitigation}`);
    });
  }

  return {
    fromVersion: currentVersion,
    toVersion: targetVersion,
    breaking,
    warnings,
    migrationNotes: manifest.migrationNotes,
    requiredActions: manifest.requiredActions || [],
  };
}

/**
 * Check compatibility across multiple versions (e.g., 0.6.0 -> 0.9.0)
 */
export async function checkMultiVersionCompatibility(
  currentVersion: string,
  targetVersion: string
): Promise<CompatibilityCheck> {
  // Get all versions between current and target
  const intermediateVersions = getVersionsBetween(currentVersion, targetVersion);

  // Fetch all manifests
  const manifests = await Promise.all(
    intermediateVersions.map((v) => fetchCompatibilityManifest(v))
  );

  // Filter out null manifests (missing for older versions)
  const validManifests = manifests.filter((m) => m !== null) as CompatibilityManifest[];

  if (validManifests.length === 0) {
    return {
      fromVersion: currentVersion,
      toVersion: targetVersion,
      breaking: false,
      warnings: ['⚠️  No compatibility manifests found for intermediate versions'],
      requiredActions: [],
    };
  }

  // Aggregate all breaking changes that affect current version
  const allBreakingChanges: BreakingChange[] = [];
  validManifests.forEach((manifest) => {
    const affected = (manifest.breakingChanges || []).filter((bc) =>
      isVersionAffected(currentVersion, bc.affectedVersions)
    );
    allBreakingChanges.push(...affected);
  });

  // Deduplicate by description
  const uniqueBreakingChanges = deduplicateBreakingChanges(allBreakingChanges);

  // Aggregate required actions
  const allRequiredActions = validManifests.flatMap((m) => m.requiredActions || []);
  const uniqueRequiredActions = [...new Set(allRequiredActions)];

  const breaking = uniqueBreakingChanges.length > 0;

  // Build warnings
  const warnings: string[] = [];

  if (breaking) {
    warnings.push(`⚠️  This upgrade spans ${intermediateVersions.length} versions and contains breaking changes!`);
    warnings.push('');

    // Group by category if available
    const categorized = groupByCategory(uniqueBreakingChanges);

    Object.entries(categorized).forEach(([category, changes]) => {
      if (category !== 'other') {
        warnings.push(`   ${getCategoryLabel(category)}:`);
      }
      changes.forEach((bc) => {
        warnings.push(`   • ${bc.description}`);
        warnings.push(`     → ${bc.mitigation}`);
      });
      warnings.push('');
    });

    // Recommendation
    if (uniqueBreakingChanges.length > 5) {
      warnings.push('   💡 Recommendation: Consider step-by-step upgrade through intermediate versions');
    }
  }

  return {
    fromVersion: currentVersion,
    toVersion: targetVersion,
    breaking,
    warnings,
    migrationNotes: validManifests[validManifests.length - 1]?.migrationNotes,
    requiredActions: uniqueRequiredActions,
  };
}

/**
 * Check if a version is affected by a breaking change using semver range
 */
function isVersionAffected(version: string, affectedRange: string): boolean {
  try {
    return semver.satisfies(version, affectedRange);
  } catch (error) {
    console.warn(`Invalid semver range: ${affectedRange}`, error);
    return false;
  }
}

/**
 * Get all versions between current and target (inclusive of target)
 * This is a simplified implementation - real version would query npm/GitHub
 */
function getVersionsBetween(currentVersion: string, targetVersion: string): string[] {
  // For now, just return the target version
  // Full implementation would query npm registry or GitHub releases
  // Example: ['0.7.0', '0.7.1', '0.8.0', '0.9.0']
  return [targetVersion];
}

/**
 * Deduplicate breaking changes by description
 */
function deduplicateBreakingChanges(changes: BreakingChange[]): BreakingChange[] {
  const seen = new Set<string>();
  return changes.filter((bc) => {
    if (seen.has(bc.description)) {
      return false;
    }
    seen.add(bc.description);
    return true;
  });
}

/**
 * Group breaking changes by category
 */
function groupByCategory(changes: BreakingChange[]): Record<string, BreakingChange[]> {
  const grouped: Record<string, BreakingChange[]> = {};

  changes.forEach((bc) => {
    const category = bc.category || 'other';
    if (!grouped[category]) {
      grouped[category] = [];
    }
    grouped[category].push(bc);
  });

  return grouped;
}

/**
 * Get display label for category
 */
function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    graphql: '📊 GraphQL Schema Changes',
    environment: '🔧 Environment Variables',
    storage: '💾 Storage Format',
    config: '⚙️  Configuration',
    docker: '🐳 Docker Changes',
    other: '📝 Other Changes',
  };
  return labels[category] || '📝 Other Changes';
}

/**
 * Format compatibility check results for display
 */
export function formatCompatibilityWarnings(check: CompatibilityCheck): string[] {
  const output: string[] = [];

  if (check.warnings.length > 0) {
    output.push(...check.warnings);
  }

  if (check.requiredActions.length > 0) {
    output.push('');
    output.push('⚠️  Required manual actions:');
    check.requiredActions.forEach((action) => {
      output.push(`   • ${action}`);
    });
  }

  return output;
}
```

## Testing

### Unit Tests

```typescript
// packages/cli-launcher/src/utils/__tests__/compatibility-checker.test.ts

import { jest } from '@jest/globals';
import {
  checkCompatibility,
  checkMultiVersionCompatibility,
  formatCompatibilityWarnings,
} from '../compatibility-checker.js';
import * as fetcher from '../compatibility-fetcher.js';

jest.mock('../compatibility-fetcher.js');

const mockFetchCompatibilityManifest = fetcher.fetchCompatibilityManifest as jest.MockedFunction<
  typeof fetcher.fetchCompatibilityManifest
>;

describe('Compatibility Checker', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
```

## Acceptance Criteria

- [ ] `checkCompatibility()` compares current version against breaking changes
- [ ] Uses `semver.satisfies()` to check if version is in affected range
- [ ] Returns `breaking: true` when breaking changes affect current version
- [ ] Returns `breaking: false` when no breaking changes affect current version
- [ ] Includes all affected breaking changes in warnings
- [ ] Handles missing manifests gracefully (returns warning, not error)
- [ ] Includes migration notes URL when available
- [ ] Includes required actions from manifest
- [ ] `checkMultiVersionCompatibility()` aggregates changes across multiple versions
- [ ] Deduplicates breaking changes by description
- [ ] Groups breaking changes by category when displaying
- [ ] Recommends step-by-step upgrade when >5 breaking changes
- [ ] `formatCompatibilityWarnings()` formats output for CLI display
- [ ] All unit tests pass
- [ ] Handles invalid semver ranges gracefully

## Notes

- Use `semver` package for version comparison
- The `affectedVersions` field uses semver range syntax (e.g., `">=0.7.0 <0.8.0"`)
- For multi-version upgrades, fetch manifests for all intermediate versions
- Category labels use emojis for better visual distinction
- If manifest is missing, treat as non-breaking but warn user
