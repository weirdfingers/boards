/**
 * Compatibility Checker
 *
 * Core logic for checking version compatibility during upgrades.
 * Uses the compatibility manifest to determine if an upgrade has breaking changes,
 * generate warnings, and aggregate compatibility information across multiple version jumps.
 */

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
    // Swallow invalid semver range errors and treat them as "not affected".
    // Higher-level callers can implement their own logging or error handling
    // if they need to surface these issues.
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
