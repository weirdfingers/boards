import { describe, test, expect } from 'vitest';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const schemaPath = join(__dirname, '..', 'compatibility-manifest.schema.json');
const compatibilitySchema = JSON.parse(readFileSync(schemaPath, 'utf-8'));

// Configure Ajv with format validators (includes uri format)
const ajv = new Ajv({ strict: false });
addFormats(ajv);
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
