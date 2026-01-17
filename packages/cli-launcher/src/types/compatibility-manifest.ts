/**
 * Compatibility Manifest
 *
 * Defines the structure for compatibility manifests published with each release.
 * These manifests provide metadata about version compatibility, breaking changes,
 * and migration requirements to enable intelligent upgrade decisions.
 */

/**
 * Complete compatibility manifest for a specific version.
 * Published with each release to describe breaking changes and migration requirements.
 */
export interface CompatibilityManifest {
  /** The version this manifest describes (e.g., "0.8.0") */
  version: string;

  /** Storage format version number (increment when storage structure changes) */
  storageFormatVersion: string;

  /** List of breaking changes that affect upgrades */
  breakingChanges?: BreakingChange[];

  /** URL to detailed migration notes in release */
  migrationNotes?: string;

  /** Manual actions required during/after upgrade */
  requiredActions?: string[];
}

/**
 * Describes a breaking change between versions.
 * Used to warn users and provide migration guidance during upgrades.
 */
export interface BreakingChange {
  /** Semver range of versions affected by this breaking change (e.g., ">=0.7.0 <0.8.0") */
  affectedVersions: string;

  /** Human-readable description of what changed */
  description: string;

  /** How to mitigate or resolve this breaking change */
  mitigation: string;

  /** Optional category for grouping (e.g., "graphql", "environment", "storage") */
  category?: 'graphql' | 'environment' | 'storage' | 'config' | 'docker' | 'other';
}

/**
 * Result of checking compatibility between two versions.
 * Used by the upgrade command to present warnings and required actions to users.
 */
export interface CompatibilityCheck {
  /** Version being upgraded from */
  fromVersion: string;

  /** Version being upgraded to */
  toVersion: string;

  /** Whether this upgrade includes breaking changes */
  breaking: boolean;

  /** List of warning messages for the user */
  warnings: string[];

  /** Optional URL to detailed migration documentation */
  migrationNotes?: string;

  /** List of manual actions the user must perform */
  requiredActions: string[];
}
