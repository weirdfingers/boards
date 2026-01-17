# CLI-7.9: Create Compatibility Manifest Generation Script

## Description

Create a script that automatically generates compatibility manifests during the release process. This script analyzes changes between versions, detects breaking changes, and produces a well-formed `compatibility-manifest.json` file that will be uploaded to GitHub Releases.

The script should:
- Accept version and output path as arguments
- Detect breaking changes from CHANGELOG.md or commit messages
- Compare GraphQL schemas between versions (if available)
- Detect environment variable changes
- Determine storage format version
- Generate manifest in correct JSON format
- Validate manifest against schema

## Dependencies

- CLI-7.1 (Compatibility Manifest Schema)

## Files to Create/Modify

### New Files
- `scripts/generate-compatibility-manifest.js` - Main generation script
- `scripts/__tests__/generate-compatibility-manifest.test.js` - Tests

## Implementation Details

### Script Implementation

```javascript
#!/usr/bin/env node
// scripts/generate-compatibility-manifest.js

import fs from 'fs-extra';
import path from 'path';
import { Command } from 'commander';
import Ajv from 'ajv';

const program = new Command();

program
  .name('generate-compatibility-manifest')
  .description('Generate compatibility manifest for a release')
  .requiredOption('--version <version>', 'Version to generate manifest for (e.g., 0.8.0)')
  .option('--output <path>', 'Output file path', 'dist/compatibility-manifest.json')
  .option('--changelog <path>', 'Path to CHANGELOG.md', 'CHANGELOG.md')
  .parse();

const options = program.opts();

async function main() {
  console.log(`Generating compatibility manifest for v${options.version}...`);

  // 1. Parse CHANGELOG.md for breaking changes
  const breakingChanges = await parseChangelogBreakingChanges(
    options.changelog,
    options.version
  );

  // 2. Detect storage format version
  const storageFormatVersion = await detectStorageFormatVersion();

  // 3. Generate manifest
  const manifest = {
    version: options.version,
    storageFormatVersion,
    breakingChanges: breakingChanges.length > 0 ? breakingChanges : undefined,
    migrationNotes: `https://github.com/weirdfingers/boards/releases/tag/v${options.version}#migration-notes`,
    requiredActions: await detectRequiredActions(breakingChanges),
  };

  // 4. Validate against schema
  const schema = await fs.readJson(
    path.join(process.cwd(), 'packages/cli-launcher/src/schemas/compatibility-manifest.schema.json')
  );
  const ajv = new Ajv();
  const validate = ajv.compile(schema);

  if (!validate(manifest)) {
    console.error('❌ Generated manifest failed schema validation:');
    console.error(validate.errors);
    process.exit(1);
  }

  // 5. Write manifest
  await fs.ensureDir(path.dirname(options.output));
  await fs.writeJson(options.output, manifest, { spaces: 2 });

  console.log(`✅ Compatibility manifest generated: ${options.output}`);
  console.log(`   Breaking changes: ${breakingChanges.length}`);
  console.log(`   Storage format: ${storageFormatVersion}`);
}

/**
 * Parse CHANGELOG.md for breaking changes in a specific version
 */
async function parseChangelogBreakingChanges(changelogPath, version) {
  if (!await fs.pathExists(changelogPath)) {
    console.warn(`⚠️  CHANGELOG.md not found at ${changelogPath}`);
    return [];
  }

  const content = await fs.readFile(changelogPath, 'utf-8');
  const breakingChanges = [];

  // Parse markdown sections by version
  const versionRegex = new RegExp(`## \\[${version}\\]([\\s\\S]*?)(?=## \\[|$)`, 'i');
  const versionSection = content.match(versionRegex);

  if (!versionSection) {
    console.warn(`⚠️  Version ${version} not found in CHANGELOG.md`);
    return [];
  }

  const versionContent = versionSection[1];

  // Look for breaking changes markers:
  // - "### Breaking Changes" section
  // - Lines starting with "BREAKING:" or "**BREAKING**:"
  const breakingSection = versionContent.match(/### Breaking Changes([\\s\\S]*?)(?=###|$)/i);

  if (breakingSection) {
    // Parse list items in breaking changes section
    const items = breakingSection[1].match(/^\\s*-\\s+(.+)$/gm) || [];

    items.forEach((item) => {
      // Format: "- Description → Mitigation"
      // or: "- **category**: Description → Mitigation"
      const match = item.match(/^\\s*-\\s+(?:\\*\\*(.+?)\\*\\*:\\s+)?(.+?)\\s+→\\s+(.+)$/);

      if (match) {
        const [, category, description, mitigation] = match;
        breakingChanges.push({
          affectedVersions: `>=${getPreviousMinorVersion(version)} <${version}`,
          description: description.trim(),
          mitigation: mitigation.trim(),
          category: category?.toLowerCase() || 'other',
        });
      }
    });
  }

  return breakingChanges;
}

/**
 * Detect storage format version from backend constants
 */
async function detectStorageFormatVersion() {
  // Read from backend constants file
  const constantsPath = path.join(
    process.cwd(),
    'packages/backend/src/boards/constants.py'
  );

  if (!await fs.pathExists(constantsPath)) {
    console.warn('⚠️  Backend constants file not found, defaulting to version "1"');
    return '1';
  }

  const content = await fs.readFile(constantsPath, 'utf-8');

  // Look for STORAGE_FORMAT_VERSION constant
  const match = content.match(/STORAGE_FORMAT_VERSION\\s*=\\s*['"](\\d+)['"]/);

  return match ? match[1] : '1';
}

/**
 * Detect required actions from breaking changes
 */
async function detectRequiredActions(breakingChanges) {
  const actions = [];

  // Check for environment variable changes
  if (breakingChanges.some((bc) => bc.category === 'environment')) {
    actions.push('Manual .env update may be required');
  }

  // Check for config changes
  if (breakingChanges.some((bc) => bc.category === 'config')) {
    actions.push('Review and update configuration files in config/');
  }

  // Check for docker changes
  if (breakingChanges.some((bc) => bc.category === 'docker')) {
    actions.push('Rebuild any custom Docker images');
  }

  return actions.length > 0 ? actions : undefined;
}

/**
 * Get previous minor version (e.g., 0.8.0 -> 0.7.0)
 */
function getPreviousMinorVersion(version) {
  const [major, minor, patch] = version.split('.').map(Number);
  return `${major}.${minor - 1}.0`;
}

main().catch((error) => {
  console.error('❌ Error generating compatibility manifest:', error);
  process.exit(1);
});
```

### CHANGELOG.md Format

Document the expected CHANGELOG format:

```markdown
## [0.8.0] - 2024-01-15

### Breaking Changes

- **graphql**: Board.tags field removed → Use Board.metadata.tags instead
- **environment**: BOARDS_AUTH_PROVIDER renamed to BOARDS_AUTH_TYPE → Update api/.env with new variable name
- Storage format changed to version 2 → Automatic migration on first startup

### Added
- New feature X
- New feature Y

### Fixed
- Bug fix A
- Bug fix B
```

## Testing

### Unit Tests

```javascript
// scripts/__tests__/generate-compatibility-manifest.test.js
describe('Compatibility Manifest Generator', () => {
  test('parses breaking changes from CHANGELOG', async () => {
    const changelog = `
## [0.8.0]

### Breaking Changes

- **graphql**: Board.tags removed → Use Board.metadata.tags
- **environment**: BOARDS_AUTH_PROVIDER renamed → Update .env
    `;

    // Write test changelog
    await fs.writeFile('test-changelog.md', changelog);

    // Run generator
    await exec('node scripts/generate-compatibility-manifest.js --version 0.8.0 --changelog test-changelog.md --output test-manifest.json');

    // Verify output
    const manifest = await fs.readJson('test-manifest.json');
    expect(manifest.breakingChanges).toHaveLength(2);
    expect(manifest.breakingChanges[0].category).toBe('graphql');
  });

  test('detects storage format version from constants', async () => {
    // Test with different STORAGE_FORMAT_VERSION values
  });

  test('generates valid manifest schema', async () => {
    // Verify generated manifest passes schema validation
  });
});
```

### Integration with Release Workflow

```yaml
# In .github/workflows/version-bump.yml
- name: Generate compatibility manifest
  run: |
    VERSION=${{ needs.bump-and-release.outputs.version }}
    node scripts/generate-compatibility-manifest.js \
      --version "$VERSION" \
      --output dist/compatibility-manifest.json
```

## Acceptance Criteria

- [ ] Script accepts `--version` and `--output` arguments
- [ ] Parses CHANGELOG.md for breaking changes in version section
- [ ] Supports "### Breaking Changes" section format
- [ ] Parses breaking change items with category, description, and mitigation
- [ ] Detects storage format version from backend constants
- [ ] Generates `affectedVersions` as semver range (previous minor → current)
- [ ] Includes migration notes URL pointing to GitHub Release
- [ ] Detects required actions based on breaking change categories
- [ ] Validates generated manifest against JSON schema
- [ ] Exits with code 1 if validation fails
- [ ] Handles missing CHANGELOG.md gracefully (generates minimal manifest)
- [ ] Unit tests pass
- [ ] Documented CHANGELOG format in CONTRIBUTING.md or docs

## Notes

- The script is run during CI/CD, so it should be fast and reliable
- CHANGELOG format should be documented for contributors
- If CHANGELOG parsing fails, generate a minimal manifest (version + storage format only)
- Consider adding GitHub API integration to fetch commit messages if CHANGELOG is incomplete
- The `affectedVersions` range assumes previous minor version (e.g., 0.7.x → 0.8.0 affects ">=0.7.0 <0.8.0")
