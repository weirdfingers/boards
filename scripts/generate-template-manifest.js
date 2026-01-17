#!/usr/bin/env node

/**
 * Generate Template Manifest
 *
 * Creates a JSON manifest file for Boards templates with checksums,
 * file sizes, and metadata for CLI consumption.
 *
 * Usage:
 *   node scripts/generate-template-manifest.js \
 *     --version 0.8.0 \
 *     --templates "dist/template-baseboards-v0.8.0.tar.gz,dist/template-basic-v0.8.0.tar.gz" \
 *     --output dist/template-manifest.json
 */

const fs = require('fs');
const crypto = require('crypto');
const path = require('path');

/**
 * Simple glob function for matching file patterns
 */
function simpleGlob(pattern) {
  const dirPath = path.dirname(pattern);
  const filePattern = path.basename(pattern);

  // Convert glob pattern to regex
  const regexPattern = filePattern
    .replace(/\./g, '\\.')
    .replace(/\*/g, '.*')
    .replace(/\?/g, '.');
  const regex = new RegExp(`^${regexPattern}$`);

  // Read directory and filter matching files
  try {
    if (!fs.existsSync(dirPath)) {
      return [];
    }

    const files = fs.readdirSync(dirPath);
    const matches = files
      .filter((file) => regex.test(file))
      .map((file) => path.join(dirPath, file));

    return matches;
  } catch (error) {
    return [];
  }
}

// Template metadata configuration
const TEMPLATE_METADATA = {
  baseboards: {
    description: 'Full-featured Boards application (recommended)',
    frameworks: ['next.js'],
    features: ['auth', 'generators', 'boards', 'themes'],
  },
  basic: {
    description: 'Minimal Next.js starter with @weirdfingers/boards',
    frameworks: ['next.js'],
    features: ['minimal'],
  },
};

/**
 * Calculate SHA-256 checksum for a file
 */
function calculateChecksum(filePath) {
  const fileBuffer = fs.readFileSync(filePath);
  const hashSum = crypto.createHash('sha256');
  hashSum.update(fileBuffer);
  return `sha256:${hashSum.digest('hex')}`;
}

/**
 * Get file size in bytes
 */
function getFileSize(filePath) {
  const stats = fs.statSync(filePath);
  return stats.size;
}

/**
 * Extract template name from filename
 * Example: "template-baseboards-v0.8.0.tar.gz" -> "baseboards"
 */
function extractTemplateName(filename) {
  const basename = path.basename(filename);
  const match = basename.match(/^template-(.+?)-v[\d.]+\.tar\.gz$/);
  if (!match) {
    throw new Error(`Invalid template filename format: ${filename}`);
  }
  return match[1];
}

/**
 * Process a single template file and extract metadata
 */
function processTemplate(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Template file not found: ${filePath}`);
  }

  const templateName = extractTemplateName(filePath);
  const metadata = TEMPLATE_METADATA[templateName];

  if (!metadata) {
    throw new Error(
      `Unknown template: ${templateName}. Please add metadata to TEMPLATE_METADATA.`
    );
  }

  const filename = path.basename(filePath);
  const checksum = calculateChecksum(filePath);
  const size = getFileSize(filePath);

  return {
    name: templateName,
    description: metadata.description,
    file: filename,
    size: size,
    checksum: checksum,
    frameworks: metadata.frameworks,
    features: metadata.features,
  };
}

/**
 * Validate manifest schema
 */
function validateManifest(manifest) {
  const errors = [];

  if (!manifest.version) {
    errors.push('Missing required field: version');
  }

  if (!manifest.templates || !Array.isArray(manifest.templates)) {
    errors.push('Missing or invalid field: templates (must be an array)');
  } else {
    manifest.templates.forEach((template, index) => {
      const requiredFields = [
        'name',
        'description',
        'file',
        'size',
        'checksum',
        'frameworks',
        'features',
      ];

      requiredFields.forEach((field) => {
        if (template[field] === undefined || template[field] === null) {
          errors.push(`Template ${index}: missing required field '${field}'`);
        }
      });

      // Validate checksum format
      if (template.checksum && !template.checksum.startsWith('sha256:')) {
        errors.push(
          `Template ${index}: checksum must start with 'sha256:' prefix`
        );
      }

      // Validate arrays
      if (template.frameworks && !Array.isArray(template.frameworks)) {
        errors.push(`Template ${index}: 'frameworks' must be an array`);
      }
      if (template.features && !Array.isArray(template.features)) {
        errors.push(`Template ${index}: 'features' must be an array`);
      }

      // Validate size is a number
      if (template.size && typeof template.size !== 'number') {
        errors.push(`Template ${index}: 'size' must be a number`);
      }
    });
  }

  return errors;
}

/**
 * Parse command-line arguments
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    version: null,
    templates: [],
    output: null,
    help: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else if (arg === '--version') {
      options.version = args[++i];
    } else if (arg === '--templates') {
      const templatesArg = args[++i];
      // Support comma-separated list or glob pattern
      if (templatesArg.includes(',')) {
        options.templates = templatesArg.split(',').map((t) => t.trim());
      } else {
        // Expand glob pattern
        const matches = simpleGlob(templatesArg);
        if (matches.length === 0) {
          throw new Error(`No files matched pattern: ${templatesArg}`);
        }
        options.templates = matches;
      }
    } else if (arg === '--output') {
      options.output = args[++i];
    }
  }

  return options;
}

/**
 * Print usage help
 */
function printHelp() {
  console.log(`
Usage: node scripts/generate-template-manifest.js [options]

Generate a JSON manifest file for Boards templates with checksums,
file sizes, and metadata.

Options:
  --version <version>      Version string (e.g., "0.8.0") (required)
  --templates <list>       Comma-separated list or glob pattern of template files (required)
  --output <path>          Output file path (default: stdout)
  --help, -h               Show this help message

Examples:
  # Generate manifest for specific templates
  node scripts/generate-template-manifest.js \\
    --version 0.8.0 \\
    --templates "dist/template-baseboards-v0.8.0.tar.gz,dist/template-basic-v0.8.0.tar.gz" \\
    --output dist/template-manifest.json

  # Use glob pattern
  node scripts/generate-template-manifest.js \\
    --version 0.8.0 \\
    --templates "dist/template-*.tar.gz" \\
    --output dist/template-manifest.json

  # Output to stdout
  node scripts/generate-template-manifest.js \\
    --version 0.8.0 \\
    --templates "dist/template-*.tar.gz"

Template Filename Format:
  template-<name>-v<version>.tar.gz
  Example: template-baseboards-v0.8.0.tar.gz

Supported Templates:
  - baseboards: Full-featured Boards application (recommended)
  - basic: Minimal Next.js starter with @weirdfingers/boards
`);
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

    if (options.templates.length === 0) {
      console.error('Error: --templates flag is required');
      printHelp();
      process.exit(1);
    }

    // Process all templates
    const templates = options.templates.map((filePath) => {
      console.error(`Processing: ${filePath}`);
      return processTemplate(filePath);
    });

    // Create manifest
    const manifest = {
      version: options.version,
      templates: templates,
    };

    // Validate manifest schema
    const validationErrors = validateManifest(manifest);
    if (validationErrors.length > 0) {
      console.error('Manifest validation failed:');
      validationErrors.forEach((error) => console.error(`  - ${error}`));
      process.exit(1);
    }

    // Generate JSON output
    const jsonOutput = JSON.stringify(manifest, null, 2);

    // Write output
    if (options.output) {
      const outputDir = path.dirname(options.output);
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
      }
      fs.writeFileSync(options.output, jsonOutput);
      console.error(`✅ Manifest written to: ${options.output}`);
    } else {
      console.log(jsonOutput);
    }

    process.exit(0);
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

// Run main function
main();
