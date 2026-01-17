/**
 * Tests for generate-compatibility-manifest.js
 * Uses Node.js built-in test runner
 */

const { describe, test, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Path resolution: __dirname is the __tests__ directory
const scriptPath = path.join(__dirname, '..', 'generate-compatibility-manifest.js');
const testOutputDir = path.join(__dirname, 'test-output');

describe('Compatibility Manifest Generator', () => {
  beforeEach(() => {
    // Create test output directory
    if (!fs.existsSync(testOutputDir)) {
      fs.mkdirSync(testOutputDir, { recursive: true });
    }
  });

  afterEach(() => {
    // Clean up test files
    if (fs.existsSync(testOutputDir)) {
      fs.rmSync(testOutputDir, { recursive: true, force: true });
    }
  });

  test('generates minimal manifest without CHANGELOG', () => {
    const outputPath = path.join(testOutputDir, 'manifest.json');

    // Run generator without CHANGELOG - should succeed even without file
    execSync(
      `node "${scriptPath}" --version 0.8.0 --output "${outputPath}" --changelog /nonexistent/CHANGELOG.md`,
      { encoding: 'utf-8', stdio: 'pipe' }
    );

    // Verify output exists
    assert.ok(fs.existsSync(outputPath), 'Output file should exist');

    // Verify manifest structure
    const manifest = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
    assert.strictEqual(manifest.version, '0.8.0');
    assert.ok(manifest.storageFormatVersion, 'Should have storageFormatVersion');
    assert.ok(manifest.migrationNotes, 'Should have migrationNotes');

    // Should not have breaking changes since no CHANGELOG
    assert.strictEqual(manifest.breakingChanges, undefined);
  });

  test('parses breaking changes from CHANGELOG', () => {
    const changelogPath = path.join(testOutputDir, 'CHANGELOG.md');
    const outputPath = path.join(testOutputDir, 'manifest.json');

    // Create test CHANGELOG
    const changelog = `
# Changelog

## [0.8.0] - 2024-01-15

### Breaking Changes

- **graphql**: Board.tags field removed → Use Board.metadata.tags instead
- **environment**: BOARDS_AUTH_PROVIDER renamed to BOARDS_AUTH_TYPE → Update api/.env with new variable name
- Storage format changed to version 2 → Automatic migration on first startup

### Added
- New feature X
- New feature Y
`;

    fs.writeFileSync(changelogPath, changelog);

    // Run generator
    execSync(
      `node "${scriptPath}" --version 0.8.0 --output "${outputPath}" --changelog "${changelogPath}"`,
      { encoding: 'utf-8', stdio: 'pipe' }
    );

    // Verify output
    const manifest = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
    assert.strictEqual(manifest.version, '0.8.0');
    assert.ok(manifest.breakingChanges, 'Should have breakingChanges');
    assert.strictEqual(manifest.breakingChanges.length, 3);

    // Verify first breaking change
    const firstChange = manifest.breakingChanges[0];
    assert.strictEqual(firstChange.category, 'graphql');
    assert.strictEqual(firstChange.description, 'Board.tags field removed');
    assert.strictEqual(firstChange.mitigation, 'Use Board.metadata.tags instead');
    assert.strictEqual(firstChange.affectedVersions, '>=0.7.0 <0.8.0');

    // Verify second breaking change
    const secondChange = manifest.breakingChanges[1];
    assert.strictEqual(secondChange.category, 'environment');
    assert.strictEqual(secondChange.description, 'BOARDS_AUTH_PROVIDER renamed to BOARDS_AUTH_TYPE');
    assert.strictEqual(secondChange.mitigation, 'Update api/.env with new variable name');
  });

  test('detects required actions from breaking changes', () => {
    const changelogPath = path.join(testOutputDir, 'CHANGELOG.md');
    const outputPath = path.join(testOutputDir, 'manifest.json');

    // Create test CHANGELOG with environment changes
    const changelog = `
## [0.8.0]

### Breaking Changes

- **environment**: BOARDS_AUTH_PROVIDER renamed → Update .env
- **config**: New config format → Review config files
- **docker**: Base image updated → Rebuild images
`;

    fs.writeFileSync(changelogPath, changelog);

    // Run generator
    execSync(
      `node "${scriptPath}" --version 0.8.0 --output "${outputPath}" --changelog "${changelogPath}"`,
      { encoding: 'utf-8', stdio: 'pipe' }
    );

    // Verify required actions
    const manifest = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
    assert.ok(manifest.requiredActions, 'Should have requiredActions');
    assert.ok(manifest.requiredActions.includes('Manual .env update may be required'));
    assert.ok(manifest.requiredActions.includes('Review and update configuration files in config/'));
    assert.ok(manifest.requiredActions.includes('Rebuild any custom Docker images'));
  });

  test('generates valid manifest that passes schema validation', () => {
    const changelogPath = path.join(testOutputDir, 'CHANGELOG.md');
    const outputPath = path.join(testOutputDir, 'manifest.json');

    // Create test CHANGELOG
    const changelog = `
## [0.8.0]

### Breaking Changes

- **graphql**: Test change → Test mitigation
`;

    fs.writeFileSync(changelogPath, changelog);

    // Run generator (should not throw if validation passes)
    execSync(
      `node "${scriptPath}" --version 0.8.0 --output "${outputPath}" --changelog "${changelogPath}"`,
      { encoding: 'utf-8', stdio: 'pipe' }
    );

    // Verify file was created (validation passed)
    assert.ok(fs.existsSync(outputPath));

    const manifest = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));

    // Verify it has required fields per schema
    assert.ok(manifest.version);
    assert.ok(manifest.storageFormatVersion);
  });

  test('fails with non-zero exit code when version is missing', () => {
    const outputPath = path.join(testOutputDir, 'manifest.json');

    // Run generator without version - should throw
    assert.throws(() => {
      execSync(`node "${scriptPath}" --output "${outputPath}"`, {
        encoding: 'utf-8',
        stdio: 'pipe',
      });
    }, 'Should throw when version is missing');
  });

  test('handles version not found in CHANGELOG gracefully', () => {
    const changelogPath = path.join(testOutputDir, 'CHANGELOG.md');
    const outputPath = path.join(testOutputDir, 'manifest.json');

    // Create CHANGELOG without version 0.9.0
    const changelog = `
## [0.8.0]

### Breaking Changes

- **graphql**: Test change → Test mitigation
`;

    fs.writeFileSync(changelogPath, changelog);

    // Run generator for version not in CHANGELOG
    execSync(
      `node "${scriptPath}" --version 0.9.0 --output "${outputPath}" --changelog "${changelogPath}"`,
      { encoding: 'utf-8', stdio: 'pipe' }
    );

    // Should still generate manifest, just without breaking changes
    const manifest = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
    assert.strictEqual(manifest.version, '0.9.0');
    assert.strictEqual(manifest.breakingChanges, undefined);
  });

  test('parses breaking changes without category', () => {
    const changelogPath = path.join(testOutputDir, 'CHANGELOG.md');
    const outputPath = path.join(testOutputDir, 'manifest.json');

    // Create CHANGELOG with breaking change without category
    const changelog = `
## [0.8.0]

### Breaking Changes

- Breaking change without category → Just migrate
`;

    fs.writeFileSync(changelogPath, changelog);

    // Run generator
    execSync(
      `node "${scriptPath}" --version 0.8.0 --output "${outputPath}" --changelog "${changelogPath}"`,
      { encoding: 'utf-8', stdio: 'pipe' }
    );

    // Verify breaking change defaults to "other" category
    const manifest = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
    assert.ok(manifest.breakingChanges);
    assert.strictEqual(manifest.breakingChanges[0].category, 'other');
  });

  test('generates migration notes URL', () => {
    const outputPath = path.join(testOutputDir, 'manifest.json');

    // Run generator
    execSync(
      `node "${scriptPath}" --version 0.8.0 --output "${outputPath}" --changelog /nonexistent/CHANGELOG.md`,
      { encoding: 'utf-8', stdio: 'pipe' }
    );

    // Verify migration notes URL
    const manifest = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
    assert.strictEqual(
      manifest.migrationNotes,
      'https://github.com/weirdfingers/boards/releases/tag/v0.8.0#migration-notes'
    );
  });

  test('calculates correct affected versions range', () => {
    const changelogPath = path.join(testOutputDir, 'CHANGELOG.md');
    const outputPath = path.join(testOutputDir, 'manifest.json');

    // Create test CHANGELOG
    const changelog = `
## [0.8.0]

### Breaking Changes

- **graphql**: Test change → Test mitigation
`;

    fs.writeFileSync(changelogPath, changelog);

    // Run generator
    execSync(
      `node "${scriptPath}" --version 0.8.0 --output "${outputPath}" --changelog "${changelogPath}"`,
      { encoding: 'utf-8', stdio: 'pipe' }
    );

    // Verify affected versions is previous minor -> current
    const manifest = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
    assert.strictEqual(manifest.breakingChanges[0].affectedVersions, '>=0.7.0 <0.8.0');
  });
});
