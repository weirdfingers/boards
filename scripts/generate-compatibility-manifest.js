#!/usr/bin/env node

/**
 * Generate Compatibility Manifest
 *
 * Creates a JSON manifest file describing version compatibility, breaking changes,
 * and migration requirements. Used during release process to help CLI detect
 * and handle breaking changes.
 *
 * Usage:
 *   node scripts/generate-compatibility-manifest.js \
 *     --version 0.8.0 \
 *     --output dist/compatibility-manifest.json \
 *     --changelog CHANGELOG.md
 */

const fs = require('fs');
const path = require('path');
const Ajv = require('ajv');

/**
 * Parse command-line arguments
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    version: null,
    output: 'dist/compatibility-manifest.json',
    changelog: 'CHANGELOG.md',
    help: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else if (arg === '--version') {
      if (i + 1 >= args.length || args[i + 1].startsWith('-')) {
        throw new Error('Missing value for --version');
      }
      options.version = args[i + 1];
      i++;
    } else if (arg === '--output') {
      if (i + 1 >= args.length || args[i + 1].startsWith('-')) {
        throw new Error('Missing value for --output');
      }
      options.output = args[i + 1];
      i++;
    } else if (arg === '--changelog') {
      if (i + 1 >= args.length || args[i + 1].startsWith('-')) {
        throw new Error('Missing value for --changelog');
      }
      options.changelog = args[i + 1];
      i++;
    }
  }

  return options;
}

/**
 * Print usage help
 */
function printHelp() {
  console.log(`
Usage: node scripts/generate-compatibility-manifest.js [options]

Generate a compatibility manifest describing breaking changes and migration requirements.

Options:
  --version <version>      Version to generate manifest for (e.g., "0.8.0") (required)
  --output <path>          Output file path (default: dist/compatibility-manifest.json)
  --changelog <path>       Path to CHANGELOG.md (default: CHANGELOG.md)
  --help, -h               Show this help message

Examples:
  # Generate manifest for version 0.8.0
  node scripts/generate-compatibility-manifest.js \\
    --version 0.8.0 \\
    --output dist/compatibility-manifest.json

  # Specify custom changelog location
  node scripts/generate-compatibility-manifest.js \\
    --version 0.8.0 \\
    --changelog docs/CHANGELOG.md \\
    --output dist/compatibility-manifest.json

CHANGELOG Format:
  The script expects breaking changes to be documented in CHANGELOG.md:

  ## [0.8.0] - 2024-01-15

  ### Breaking Changes

  - **graphql**: Board.tags field removed → Use Board.metadata.tags instead
  - **environment**: BOARDS_AUTH_PROVIDER renamed to BOARDS_AUTH_TYPE → Update api/.env
  - Storage format changed to version 2 → Automatic migration on first startup
`);
}

/**
 * Parse CHANGELOG.md for breaking changes in a specific version
 */
function parseChangelogBreakingChanges(changelogPath, version) {
  if (!fs.existsSync(changelogPath)) {
    console.error(`⚠️  CHANGELOG.md not found at ${changelogPath}`);
    return [];
  }

  const content = fs.readFileSync(changelogPath, 'utf-8');
  const breakingChanges = [];

  // Parse markdown sections by version
  const escapedVersion = escapeRegex(version);
  const versionRegex = new RegExp(`## \\[${escapedVersion}\\]([\\s\\S]*?)(?=## \\[|$)`, 'i');
  const versionSection = content.match(versionRegex);

  if (!versionSection) {
    console.error(`⚠️  Version ${version} not found in CHANGELOG.md`);
    console.error(`   Tried regex: ${versionRegex}`);
    return [];
  }

  const versionContent = versionSection[1];

  // Look for breaking changes section
  const breakingSection = versionContent.match(/### Breaking Changes([\s\S]*?)(?=###|$)/i);

  if (breakingSection) {
    // Parse list items in breaking changes section
    const items = breakingSection[1].match(/^\s*-\s+.+$/gm) || [];

    items.forEach((item) => {
      // Format: "- Description → Mitigation"
      // or: "- **category**: Description → Mitigation"
      const match = item.match(/^\s*-\s+(?:\*\*(.+?)\*\*:\s+)?(.+?)\s+→\s+(.+)$/);

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
function detectStorageFormatVersion() {
  // Read from backend constants file
  const constantsPath = path.join(
    process.cwd(),
    'packages/backend/src/boards/constants.py'
  );

  if (!fs.existsSync(constantsPath)) {
    console.error('⚠️  Backend constants file not found, defaulting to version "1"');
    return '1';
  }

  const content = fs.readFileSync(constantsPath, 'utf-8');

  // Look for STORAGE_FORMAT_VERSION constant
  const match = content.match(/STORAGE_FORMAT_VERSION\s*=\s*['"](\d+)['"]/);

  return match ? match[1] : '1';
}

/**
 * Detect required actions from breaking changes
 */
function detectRequiredActions(breakingChanges) {
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

  if (isNaN(major) || isNaN(minor) || isNaN(patch)) {
    throw new Error(`Invalid version format: ${version}`);
  }

  return `${major}.${Math.max(0, minor - 1)}.0`;
}

/**
 * Escape special regex characters
 */
function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Validate manifest against JSON schema
 */
function validateManifest(manifest) {
  const schemaPath = path.join(
    process.cwd(),
    'packages/cli-launcher/src/schemas/compatibility-manifest.schema.json'
  );

  if (!fs.existsSync(schemaPath)) {
    throw new Error(`Schema file not found: ${schemaPath}`);
  }

  const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf-8'));
  // Configure Ajv to ignore unknown formats (uri is not built-in to Ajv v8)
  const ajv = new Ajv({ strict: false });
  const validate = ajv.compile(schema);

  if (!validate(manifest)) {
    console.error('❌ Generated manifest failed schema validation:');
    validate.errors.forEach((error) => {
      console.error(`  - ${error.instancePath} ${error.message}`);
    });
    return false;
  }

  return true;
}

/**
 * Main function
 */
function main() {
  try {
    const options = parseArgs();

    if (options.help) {
      printHelp();
      process.exit(0);
    }

    // Validate required arguments
    if (!options.version) {
      console.error('Error: --version flag is required');
      printHelp();
      process.exit(1);
    }

    console.log(`Generating compatibility manifest for v${options.version}...`);

    // 1. Parse CHANGELOG.md for breaking changes
    const breakingChanges = parseChangelogBreakingChanges(
      options.changelog,
      options.version
    );

    // 2. Detect storage format version
    const storageFormatVersion = detectStorageFormatVersion();

    // 3. Generate manifest
    const manifest = {
      version: options.version,
      storageFormatVersion,
    };

    // Only include breakingChanges if there are any
    if (breakingChanges.length > 0) {
      manifest.breakingChanges = breakingChanges;
    }

    // Include migration notes URL
    manifest.migrationNotes = `https://github.com/weirdfingers/boards/releases/tag/v${options.version}#migration-notes`;

    // Detect required actions
    const requiredActions = detectRequiredActions(breakingChanges);
    if (requiredActions) {
      manifest.requiredActions = requiredActions;
    }

    // 4. Validate against schema
    if (!validateManifest(manifest)) {
      process.exit(1);
    }

    // 5. Write manifest
    const outputDir = path.dirname(options.output);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    fs.writeFileSync(options.output, JSON.stringify(manifest, null, 2));

    console.log(`✅ Compatibility manifest generated: ${options.output}`);
    console.log(`   Version: ${manifest.version}`);
    console.log(`   Breaking changes: ${breakingChanges.length}`);
    console.log(`   Storage format: ${storageFormatVersion}`);

    process.exit(0);
  } catch (error) {
    console.error(`❌ Error generating compatibility manifest: ${error.message}`);
    process.exit(1);
  }
}

// Run main function
main();
