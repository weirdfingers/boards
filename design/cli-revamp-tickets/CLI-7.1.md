# CLI-7.1: Create Compatibility Manifest Schema

## Description

Define the JSON schema for compatibility manifests that will be published with each release. This manifest provides structured metadata about version compatibility, breaking changes, and migration requirements, enabling the CLI to make intelligent upgrade decisions.

The manifest will be fetched from GitHub Releases and used by the upgrade command to:
- Detect breaking changes between versions
- Display warnings and migration notes to users
- Check storage format compatibility
- List required manual actions

## Dependencies

None - this is the foundation for Phase 7

## Files to Create/Modify

### New Files
- `packages/cli-launcher/src/types/compatibility-manifest.ts` - TypeScript interfaces and types
- `packages/cli-launcher/src/schemas/compatibility-manifest.schema.json` - JSON schema for validation

## Implementation Details

### TypeScript Interface

```typescript
// packages/cli-launcher/src/types/compatibility-manifest.ts

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

export interface BreakingChange {
  /** Semver range of versions affected by this breaking change (e.g., ">=0.7.0 <0.8.0") */
  affectedVersions: string;

  /** Human-readable description of what changed */
  description: string;

  /** How to mitigate or resolve this breaking change */
  mitigation: string;

  /** Optional category for grouping (e.g., "graphql", "environment", "storage") */
  category?: string;
}

export interface CompatibilityCheck {
  fromVersion: string;
  toVersion: string;
  breaking: boolean;
  warnings: string[];
  migrationNotes?: string;
  requiredActions: string[];
}
```

### JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Compatibility Manifest",
  "description": "Metadata about version compatibility and breaking changes",
  "type": "object",
  "required": ["version", "storageFormatVersion"],
  "properties": {
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semver version this manifest describes"
    },
    "storageFormatVersion": {
      "type": "string",
      "description": "Storage format version identifier"
    },
    "breakingChanges": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["affectedVersions", "description", "mitigation"],
        "properties": {
          "affectedVersions": {
            "type": "string",
            "description": "Semver range of affected versions"
          },
          "description": {
            "type": "string",
            "description": "What changed"
          },
          "mitigation": {
            "type": "string",
            "description": "How to handle this change"
          },
          "category": {
            "type": "string",
            "enum": ["graphql", "environment", "storage", "config", "docker", "other"]
          }
        }
      }
    },
    "migrationNotes": {
      "type": "string",
      "format": "uri",
      "description": "URL to detailed migration documentation"
    },
    "requiredActions": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Manual steps user must take"
    }
  }
}
```

## Testing

### Schema Validation Tests

```typescript
// packages/cli-launcher/src/schemas/__tests__/compatibility-manifest.test.ts

import Ajv from 'ajv';
import compatibilitySchema from '../compatibility-manifest.schema.json';

const ajv = new Ajv();
const validate = ajv.compile(compatibilitySchema);

describe('Compatibility Manifest Schema', () => {
  test('validates valid manifest with minimal fields', () => {
    const manifest = {
      version: '0.8.0',
      storageFormatVersion: '2',
    };
    expect(validate(manifest)).toBe(true);
  });

  test('validates valid manifest with all fields', () => {
    const manifest = {
      version: '0.8.0',
      storageFormatVersion: '2',
      breakingChanges: [
        {
          affectedVersions: '>=0.7.0 <0.8.0',
          description: 'Board.tags removed',
          mitigation: 'Use Board.metadata.tags',
          category: 'graphql',
        },
      ],
      migrationNotes: 'https://github.com/weirdfingers/boards/releases/tag/v0.8.0',
      requiredActions: ['Update .env files'],
    };
    expect(validate(manifest)).toBe(true);
  });

  test('rejects invalid version format', () => {
    const manifest = {
      version: 'v0.8.0', // Invalid: includes "v" prefix
      storageFormatVersion: '2',
    };
    expect(validate(manifest)).toBe(false);
  });

  test('rejects manifest missing required fields', () => {
    const manifest = {
      version: '0.8.0',
      // Missing storageFormatVersion
    };
    expect(validate(manifest)).toBe(false);
  });

  test('rejects breaking change missing required fields', () => {
    const manifest = {
      version: '0.8.0',
      storageFormatVersion: '2',
      breakingChanges: [
        {
          affectedVersions: '>=0.7.0 <0.8.0',
          // Missing description and mitigation
        },
      ],
    };
    expect(validate(manifest)).toBe(false);
  });

  test('rejects invalid category', () => {
    const manifest = {
      version: '0.8.0',
      storageFormatVersion: '2',
      breakingChanges: [
        {
          affectedVersions: '>=0.7.0 <0.8.0',
          description: 'Test change',
          mitigation: 'Test mitigation',
          category: 'invalid-category',
        },
      ],
    };
    expect(validate(manifest)).toBe(false);
  });
});
```

### Example Manifests

Create example manifests for testing:

```json
// packages/cli-launcher/test-fixtures/compatibility-manifest-minimal.json
{
  "version": "0.7.0",
  "storageFormatVersion": "1"
}
```

```json
// packages/cli-launcher/test-fixtures/compatibility-manifest-breaking.json
{
  "version": "0.8.0",
  "storageFormatVersion": "2",
  "breakingChanges": [
    {
      "affectedVersions": ">=0.7.0 <0.8.0",
      "description": "GraphQL schema: Board.tags field removed",
      "mitigation": "Use Board.metadata.tags instead",
      "category": "graphql"
    },
    {
      "affectedVersions": ">=0.6.0 <0.8.0",
      "description": "BOARDS_AUTH_PROVIDER renamed to BOARDS_AUTH_TYPE",
      "mitigation": "Update api/.env with new variable name",
      "category": "environment"
    }
  ],
  "migrationNotes": "https://github.com/weirdfingers/boards/releases/tag/v0.8.0#migration",
  "requiredActions": [
    "Manual .env update required if using custom auth provider",
    "Rebuild any custom Docker images that reference old env vars"
  ]
}
```

## Acceptance Criteria

- [ ] TypeScript interface created in `src/types/compatibility-manifest.ts`
- [ ] JSON schema created in `src/schemas/compatibility-manifest.schema.json`
- [ ] Schema validates required fields: `version`, `storageFormatVersion`
- [ ] Schema validates optional fields: `breakingChanges`, `migrationNotes`, `requiredActions`
- [ ] Breaking change requires: `affectedVersions`, `description`, `mitigation`
- [ ] Version field validated as semver format (no "v" prefix)
- [ ] Category enum includes: graphql, environment, storage, config, docker, other
- [ ] Unit tests pass for valid and invalid manifests
- [ ] Example fixtures created for testing
- [ ] JSDoc comments added to all interfaces

## Notes

- The manifest schema is versioned implicitly through the `version` field
- If schema needs to evolve, add optional fields (backward compatible)
- The `storageFormatVersion` is a simple string to allow flexibility (e.g., "1", "2", "2.1")
- `affectedVersions` uses semver range syntax (via `semver` package)
- Migration notes URL should link to GitHub Release with anchor to migration section
