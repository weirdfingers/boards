#!/usr/bin/env node

/**
 * Template Preparation Script
 *
 * This script runs before CLI build to copy source code from the monorepo
 * into the templates directory that gets bundled with the npm package.
 *
 * Flow:
 * 1. Clean existing templates directory
 * 2. Copy apps/baseboards → templates/web (excluding build artifacts)
 * 3. Copy packages/backend → templates/api (excluding Python artifacts)
 * 4. Copy baseline-config → templates/api/config
 * 5. Copy template-sources/ files → templates/
 * 6. Transform workspace:* dependencies to published versions
 * 7. Update storage_config.yaml paths to be project-relative
 * 8. Update next.config.js for standalone builds
 */

import fs from "fs-extra";
import path from "path";
import { fileURLToPath } from "url";
import yaml from "yaml";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths
const MONOREPO_ROOT = path.resolve(__dirname, "../../..");
const CLI_PACKAGE_ROOT = path.resolve(__dirname, "..");
const TEMPLATES_DIR = path.join(CLI_PACKAGE_ROOT, "templates");
const TEMPLATE_SOURCES_DIR = path.join(CLI_PACKAGE_ROOT, "template-sources");

// Get frontend package version (this is what @weirdfingers/boards uses)
const frontendPackageJson = JSON.parse(
  fs.readFileSync(
    path.join(MONOREPO_ROOT, "packages/frontend/package.json"),
    "utf8"
  )
);
const VERSION = frontendPackageJson.version;

console.log("🔧 Preparing templates for @weirdfingers/boards v" + VERSION);
console.log("📁 Monorepo root:", MONOREPO_ROOT);
console.log("📦 Templates dir:", TEMPLATES_DIR);

// Clean templates directory
console.log("\n🧹 Cleaning templates directory...");
fs.removeSync(TEMPLATES_DIR);
fs.ensureDirSync(TEMPLATES_DIR);

// File/folder exclusion patterns
const WEB_EXCLUDE = [
  ".next",
  "node_modules",
  ".turbo",
  ".env",
  ".env.local",
  "dist",
  ".cache",
];
const API_EXCLUDE = [
  ".venv",
  "__pycache__",
  "*.pyc",
  ".pytest_cache",
  ".ruff_cache",
  ".env",
  "build",
  "dist",
  "*.egg-info",
  "uv.lock",
  "tests",
  "test_logging.py",
  "pytest.ini",
  "MANIFEST.in",
  "pyrightconfig.json",
  "baseline-config",
  "examples",
];

/**
 * Filter function for fs.copySync
 */
function createFilter(excludePatterns) {
  return (src) => {
    const baseName = path.basename(src);

    // Check exact matches
    if (excludePatterns.includes(baseName)) {
      return false;
    }

    // Check patterns (*.pyc, etc.)
    for (const pattern of excludePatterns) {
      if (pattern.includes("*")) {
        const regex = new RegExp("^" + pattern.replace("*", ".*") + "$");
        if (regex.test(baseName)) {
          return false;
        }
      }
    }

    return true;
  };
}

// Step 1: Copy web app
console.log("\n📦 Copying apps/baseboards → templates/web...");
const webSource = path.join(MONOREPO_ROOT, "apps/baseboards");
const webDest = path.join(TEMPLATES_DIR, "web");

if (!fs.existsSync(webSource)) {
  console.error("❌ Error: apps/baseboards not found at", webSource);
  process.exit(1);
}

fs.copySync(webSource, webDest, {
  filter: createFilter(WEB_EXCLUDE),
});
console.log("   ✅ Copied web app");

// Update next.config.js to add standalone output for Docker
const nextConfigPath = path.join(webDest, "next.config.js");
if (fs.existsSync(nextConfigPath)) {
  let nextConfig = fs.readFileSync(nextConfigPath, "utf-8");
  // Add output: "standalone" if not present
  if (!nextConfig.includes("output:")) {
    nextConfig = nextConfig.replace(
      /const nextConfig = \{/,
      `const nextConfig = {\n  output: "standalone",`
    );
    fs.writeFileSync(nextConfigPath, nextConfig);
    console.log("   ✅ Updated next.config.js for Docker standalone build");
  }

  // Update image remote patterns port from 8088 to 8800
  nextConfig = fs.readFileSync(nextConfigPath, "utf-8");
  if (nextConfig.includes('port: "8088"')) {
    nextConfig = nextConfig.replace('port: "8088"', 'port: "8800"');
    fs.writeFileSync(nextConfigPath, nextConfig);
    console.log("   ✅ Updated next.config.js images port to 8800");
  }

  // Add 'api' hostname for internal Docker network (server-side image fetching)
  nextConfig = fs.readFileSync(nextConfigPath, "utf-8");
  if (!nextConfig.includes('hostname: "api"')) {
    // Add api hostname pattern after the localhost pattern
    nextConfig = nextConfig.replace(
      /(hostname: "localhost",[\s\S]*?},)/,
      `$1
      {
        protocol: "http",
        hostname: "api",
        port: "8800",
        pathname: "/api/storage/**",
      },`
    );
    fs.writeFileSync(nextConfigPath, nextConfig);
    console.log("   ✅ Added internal Docker hostname to next.config.js");
  }

  // Add unoptimized: true for Docker compatibility
  nextConfig = fs.readFileSync(nextConfigPath, "utf-8");
  if (!nextConfig.includes("unoptimized:")) {
    nextConfig = nextConfig.replace(
      /images: \{/,
      `images: {
    unoptimized: true, // Disable server-side optimization for Docker compatibility`
    );
    fs.writeFileSync(nextConfigPath, nextConfig);
    console.log("   ✅ Added unoptimized images for Docker compatibility");
  }
}

// Step 2: Copy backend
console.log("\n📦 Copying packages/backend → templates/api...");
const apiSource = path.join(MONOREPO_ROOT, "packages/backend");
const apiDest = path.join(TEMPLATES_DIR, "api");

if (!fs.existsSync(apiSource)) {
  console.error("❌ Error: packages/backend not found at", apiSource);
  process.exit(1);
}

fs.copySync(apiSource, apiDest, {
  filter: createFilter(API_EXCLUDE),
});
console.log("   ✅ Copied backend");

// Step 3: Copy baseline-config → api/config
console.log("\n📦 Copying baseline-config → templates/api/config...");
const baselineConfigSource = path.join(apiSource, "baseline-config");
const configDest = path.join(apiDest, "config");

if (fs.existsSync(baselineConfigSource)) {
  fs.copySync(baselineConfigSource, configDest);
  console.log("   ✅ Copied config files");
} else {
  console.warn("   ⚠️  baseline-config not found, skipping");
}

// Step 4: Copy template source files
console.log("\n📦 Copying template source files...");
fs.copySync(
  path.join(TEMPLATE_SOURCES_DIR, "compose.yaml"),
  path.join(TEMPLATES_DIR, "compose.yaml")
);
console.log("   ✅ compose.yaml");

fs.copySync(
  path.join(TEMPLATE_SOURCES_DIR, "compose.dev.yaml"),
  path.join(TEMPLATES_DIR, "compose.dev.yaml")
);
console.log("   ✅ compose.dev.yaml");

fs.copySync(
  path.join(TEMPLATE_SOURCES_DIR, ".gitignore"),
  path.join(TEMPLATES_DIR, ".gitignore")
);
console.log("   ✅ .gitignore");

fs.copySync(
  path.join(TEMPLATE_SOURCES_DIR, "README.md"),
  path.join(TEMPLATES_DIR, "README.md")
);
console.log("   ✅ README.md");

// Copy .env examples
fs.copySync(
  path.join(TEMPLATE_SOURCES_DIR, "web-env.example"),
  path.join(webDest, ".env.example")
);
console.log("   ✅ web/.env.example");

fs.copySync(
  path.join(TEMPLATE_SOURCES_DIR, "api-env.example"),
  path.join(apiDest, ".env.example")
);
console.log("   ✅ api/.env.example");

// Copy Dockerfiles
fs.copySync(
  path.join(TEMPLATE_SOURCES_DIR, "Dockerfile.web"),
  path.join(webDest, "Dockerfile")
);
console.log("   ✅ web/Dockerfile");

fs.copySync(
  path.join(TEMPLATE_SOURCES_DIR, "Dockerfile.api"),
  path.join(apiDest, "Dockerfile")
);
console.log("   ✅ api/Dockerfile");

// Copy docker env.example
fs.ensureDirSync(path.join(TEMPLATES_DIR, "docker"));
fs.copySync(
  path.join(TEMPLATE_SOURCES_DIR, "docker-env.example"),
  path.join(TEMPLATES_DIR, "docker/env.example")
);
console.log("   ✅ docker/env.example");

// Step 5: Transform package.json dependencies
console.log("\n🔄 Transforming workspace dependencies...");
const webPkgPath = path.join(webDest, "package.json");
if (fs.existsSync(webPkgPath)) {
  const webPkg = JSON.parse(fs.readFileSync(webPkgPath, "utf8"));

  // Transform workspace:* to ^VERSION (requires publishing to npm)
  ["dependencies", "devDependencies"].forEach((depType) => {
    if (webPkg[depType]) {
      Object.keys(webPkg[depType]).forEach((pkgName) => {
        const version = webPkg[depType][pkgName];
        if (version.startsWith("workspace:")) {
          webPkg[depType][pkgName] = `^${VERSION}`;
          console.log(`   ✓ ${pkgName}: workspace:* → ^${VERSION}`);
        }
      });
    }
  });

  fs.writeFileSync(webPkgPath, JSON.stringify(webPkg, null, 2) + "\n");
  console.log("   ✅ Transformed web package.json");
}

// Step 6: Update storage_config.yaml path
console.log("\n🔄 Updating storage_config.yaml paths...");
const storageConfigPath = path.join(configDest, "storage_config.yaml");
if (fs.existsSync(storageConfigPath)) {
  let storageConfig = fs.readFileSync(storageConfigPath, "utf8");
  const storageYaml = yaml.parse(storageConfig);

  // Update local storage path
  if (storageYaml.storage?.providers?.local?.config?.base_path) {
    const oldPath = storageYaml.storage.providers.local.config.base_path;
    storageYaml.storage.providers.local.config.base_path = "./data/storage";
    console.log(`   ✓ Updated local storage path: ${oldPath} → ./data/storage`);
  }

  // Update public_url_base to use correct port
  if (storageYaml.storage?.providers?.local?.config?.public_url_base) {
    storageYaml.storage.providers.local.config.public_url_base =
      "http://localhost:8800/api/storage";
  }

  fs.writeFileSync(storageConfigPath, yaml.stringify(storageYaml));
  console.log("   ✅ Updated storage_config.yaml");
}

console.log("\n✨ Template preparation complete!");
console.log("📦 Templates ready in:", TEMPLATES_DIR);
console.log("🏗️  Ready to build CLI package");
