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
 * 5. Transform workspace:* dependencies to published versions
 * 6. Update storage_config.yaml paths to be project-relative
 * 7. Generate .env.example files
 * 8. Copy compose files and other scaffolding
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

// Get CLI version from package.json
const cliPackageJson = JSON.parse(
  fs.readFileSync(path.join(CLI_PACKAGE_ROOT, "package.json"), "utf8")
);
const VERSION = cliPackageJson.version;

console.log("🔧 Preparing templates for CLI v" + VERSION);
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

// Step 4: Transform package.json dependencies
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

// Step 5: Update storage_config.yaml path
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

// Step 6: Generate .env.example files
console.log("\n📝 Generating .env.example files...");

// Web .env.example
const webEnvExample = `# Frontend Environment Variables

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8800
NEXT_PUBLIC_GRAPHQL_URL=http://localhost:8800/graphql

# Auth Provider
# For local development, 'none' allows unauthenticated access
NEXT_PUBLIC_AUTH_PROVIDER=none

# Clerk
# NEXT_PUBLIC_AUTH_PROVIDER=clerk
# NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...

# Supabase
# NEXT_PUBLIC_AUTH_PROVIDER=supabase
# NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
# NEXT_PUBLIC_SUPABASE_ANON_KEY=...

# Auth0
# NEXT_PUBLIC_AUTH_PROVIDER=auth0
# NEXT_PUBLIC_AUTH0_DOMAIN=...
# NEXT_PUBLIC_AUTH0_CLIENT_ID=...
`;

fs.writeFileSync(path.join(webDest, ".env.example"), webEnvExample);
console.log("   ✅ Created web/.env.example");

// API .env.example
const apiEnvExample = `# Backend Environment Variables

# Database (set by docker-compose)
DATABASE_URL=postgresql://baseboards:password@db:5432/baseboards

# Redis (set by docker-compose)
REDIS_URL=redis://cache:6379/0

# JWT Secret (will be generated by CLI)
JWT_SECRET=

# ============================================
# PROVIDER API KEYS (ADD AT LEAST ONE!)
# ============================================

# Replicate - https://replicate.com/account/api-tokens
REPLICATE_API_KEY=

# FAL - https://fal.ai/dashboard/keys
FAL_KEY=

# OpenAI - https://platform.openai.com/api-keys
OPENAI_API_KEY=

# Google AI - https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=

# ============================================
# AUTH PROVIDER
# ============================================
# For local development, 'none' allows unauthenticated access
# For production, configure a proper provider (clerk, supabase, auth0, jwt)
AUTH_PROVIDER=none

# Clerk
# AUTH_PROVIDER=clerk
# CLERK_SECRET_KEY=sk_test_...

# Supabase
# AUTH_PROVIDER=supabase
# SUPABASE_URL=https://xxx.supabase.co
# SUPABASE_SERVICE_KEY=...

# Auth0
# AUTH_PROVIDER=auth0
# AUTH0_DOMAIN=...
# AUTH0_CLIENT_ID=...
# AUTH0_CLIENT_SECRET=...

# ============================================
# CONFIGURATION
# ============================================

# Config file paths
STORAGE_CONFIG_PATH=./config/storage_config.yaml
GENERATORS_CONFIG_PATH=./config/generators.yaml

# Storage (if using cloud storage)
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# GCP_SERVICE_ACCOUNT_JSON=
`;

fs.writeFileSync(path.join(apiDest, ".env.example"), apiEnvExample);
console.log("   ✅ Created api/.env.example");

// Step 7: Create docker/.env.example
console.log("\n📝 Generating docker/.env.example...");
fs.ensureDirSync(path.join(TEMPLATES_DIR, "docker"));

const dockerEnvExample = `# Docker Compose Environment Variables
# Generated by CLI - DO NOT EDIT MANUALLY

# Project configuration
PROJECT_NAME=baseboards

# Service ports
WEB_PORT=3300
API_PORT=8800

# PostgreSQL configuration
POSTGRES_USER=baseboards
POSTGRES_PASSWORD=REPLACE_WITH_GENERATED_PASSWORD
POSTGRES_DB=baseboards

# Database URL (for API container)
DB_URL=postgresql://baseboards:REPLACE_WITH_GENERATED_PASSWORD@db:5432/baseboards

# Redis URL (for API container)
REDIS_URL=redis://cache:6379/0

# Image version (matches CLI version)
VERSION=latest
`;

fs.writeFileSync(
  path.join(TEMPLATES_DIR, "docker/env.example"),
  dockerEnvExample
);
console.log("   ✅ Created docker/.env.example");

// Step 8: Create compose files (placeholders for now)
console.log("\n📝 Creating compose file placeholders...");

const composeYaml = `# Docker Compose Configuration for Baseboards
name: \${PROJECT_NAME:-baseboards}

services:
  db:
    image: postgres:16
    env_file: docker/.env
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]
      interval: 5s
      timeout: 5s
      retries: 20
    networks:
      - internal

  cache:
    image: redis:7
    command: ["redis-server", "--appendonly", "yes"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20
    networks:
      - internal

  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    image: baseboards-api:local
    env_file: docker/.env
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    ports:
      - "\${API_PORT:-8800}:8800"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8800/health"]
      interval: 5s
      timeout: 3s
      retries: 50
    networks:
      - internal

  web:
    build:
      context: ./web
      dockerfile: Dockerfile
      args:
        - NEXT_PUBLIC_API_URL=http://localhost:\${API_PORT:-8800}
        - NEXT_PUBLIC_GRAPHQL_URL=http://localhost:\${API_PORT:-8800}/graphql
    image: baseboards-web:local
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:\${API_PORT:-8800}
      - NEXT_PUBLIC_GRAPHQL_URL=http://localhost:\${API_PORT:-8800}/graphql
    depends_on:
      api:
        condition: service_healthy
    ports:
      - "\${WEB_PORT:-3300}:3000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/"]
      interval: 5s
      timeout: 3s
      retries: 50
    networks:
      - internal

networks:
  internal:
    driver: bridge

volumes:
  db-data:
`;

fs.writeFileSync(path.join(TEMPLATES_DIR, "compose.yaml"), composeYaml);
console.log("   ✅ Created compose.yaml");

const composeDevYaml = `# Development overrides for Docker Compose
# Enables hot reload by mounting source code

services:
  api:
    volumes:
      - ./api:/app
      - ./data/storage:/app/data/storage
    environment:
      - PYTHONUNBUFFERED=1
      - RELOAD=true

  web:
    volumes:
      - ./web:/app
      - /app/node_modules
      - /app/.next
`;

fs.writeFileSync(path.join(TEMPLATES_DIR, "compose.dev.yaml"), composeDevYaml);
console.log("   ✅ Created compose.dev.yaml");

// Step 8.5: Create Dockerfiles
console.log("\n📝 Creating Dockerfiles...");

// Web Dockerfile (Next.js)
const webDockerfile = `FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN corepack enable pnpm && pnpm install

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Accept build args for Next.js public env vars
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_GRAPHQL_URL
ENV NEXT_PUBLIC_API_URL=\${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_GRAPHQL_URL=\${NEXT_PUBLIC_GRAPHQL_URL}

RUN corepack enable pnpm && pnpm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
`;

fs.writeFileSync(path.join(webDest, "Dockerfile"), webDockerfile);
console.log("   ✅ Created web/Dockerfile");

// API Dockerfile (FastAPI/Python)
const apiDockerfile = `FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy application code first (needed for version detection in pyproject.toml)
COPY . .

# Install Python dependencies
RUN uv pip install --system --no-cache-dir .

# Create non-root user
RUN useradd -m -u 1001 apiuser && chown -R apiuser:apiuser /app
USER apiuser

# Expose port
EXPOSE 8800

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \\
  CMD curl -f http://localhost:8800/health || exit 1

# Start the application
CMD ["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800"]
`;

fs.writeFileSync(path.join(apiDest, "Dockerfile"), apiDockerfile);
console.log("   ✅ Created api/Dockerfile");

// Step 9: Create .gitignore
console.log("\n📝 Creating .gitignore...");

const gitignore = `# Environment files
.env
.env.local
.env.*.local
*.env

# Generated media
data/

# Dependencies
node_modules/
.pnpm-store/
.venv/
__pycache__/

# Build outputs
.next/
.turbo/
dist/
build/
*.pyc
*.pyo
*.egg-info/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Logs
*.log
logs/

# Testing
.pytest_cache/
coverage/
.coverage

# Docker
docker/.env
`;

fs.writeFileSync(path.join(TEMPLATES_DIR, ".gitignore"), gitignore);
console.log("   ✅ Created .gitignore");

// Step 10: Create README.md
console.log("\n📝 Creating README.md...");

const readme = `# Baseboards - Image Generation Platform

This is a self-hosted Baseboards installation, scaffolded by the Baseboards CLI.

## Quick Start

### Prerequisites

- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Node.js 20+

### First-Time Setup

1. **Configure API Keys** (Required)

   Edit \`packages/api/.env\` and add at least one provider API key:

   \`\`\`bash
   # Get your API keys from:
   # - Replicate: https://replicate.com/account/api-tokens
   # - FAL: https://fal.ai/dashboard/keys
   # - OpenAI: https://platform.openai.com/api-keys
   # - Google: https://makersuite.google.com/app/apikey

   REPLICATE_API_KEY=r8_...
   FAL_KEY=...
   OPENAI_API_KEY=sk-...
   GOOGLE_API_KEY=...
   \`\`\`

2. **Start the application**

   \`\`\`bash
   npx @weirdfingers/baseboards up
   \`\`\`

3. **Access the app**

   Open http://localhost:3300 in your browser

## Commands

\`\`\`bash
# Start the application
npx @weirdfingers/baseboards up

# Start in detached mode (background)
npx @weirdfingers/baseboards up --detached

# Stop the application
npx @weirdfingers/baseboards down

# View logs
npx @weirdfingers/baseboards logs

# View specific service logs
npx @weirdfingers/baseboards logs api

# Check status
npx @weirdfingers/baseboards status

# Update to latest version
npx @weirdfingers/baseboards update

# Clean up (removes volumes and containers)
npx @weirdfingers/baseboards clean --hard
\`\`\`

## Configuration

### Generators

Edit \`packages/api/config/generators.yaml\` to:
- Enable/disable specific image generation providers
- Add custom Replicate models
- Configure provider-specific settings

### Storage

Edit \`packages/api/config/storage_config.yaml\` to:
- Switch from local storage to S3/GCS/Cloudflare R2
- Configure CDN integration
- Set up routing rules for different file types

Generated media is stored in \`data/storage/\` by default.

## Development

### Hot Reload

The default development mode includes hot reload for both frontend and backend:

- Frontend: Next.js Fast Refresh
- Backend: uvicorn --reload

Changes to source code are reflected immediately.

### Custom Code

You can customize any part of the application:
- Frontend: \`packages/web/src/\`
- Backend: \`packages/api/src/\`

**Note:** When you run \`update\`, custom code changes will be overwritten.
Use git to track your modifications.

## Documentation

- Full documentation: https://baseboards.dev/docs
- Adding providers: https://baseboards.dev/docs/generators
- Storage configuration: https://baseboards.dev/docs/storage
- Auth setup: https://baseboards.dev/docs/auth

## Support

- GitHub Issues: https://github.com/weirdfingers/boards/issues
- Documentation: https://baseboards.dev
`;

fs.writeFileSync(path.join(TEMPLATES_DIR, "README.md"), readme);
console.log("   ✅ Created README.md");

console.log("\n✨ Template preparation complete!");
console.log("📦 Templates ready in:", TEMPLATES_DIR);
console.log("🏗️  Ready to build CLI package");
