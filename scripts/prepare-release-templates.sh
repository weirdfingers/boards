#!/bin/bash

###############################################################################
# Prepare Release Templates
#
# This script prepares Boards templates for release by:
# 1. Copying template source files to dist/templates/
# 2. Transforming workspace:* dependencies to published versions
# 3. Creating versioned tarballs
# 4. Generating the template manifest with checksums
#
# Usage:
#   ./scripts/prepare-release-templates.sh <VERSION>
#
# Example:
#   ./scripts/prepare-release-templates.sh 0.8.0
#
###############################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Print usage help
print_usage() {
    cat << EOF
Usage: $(basename "$0") <VERSION>

Prepare Boards templates for release by packaging them as tarballs
and generating the template manifest.

Arguments:
  VERSION    Version string (e.g., "0.8.0" or "0.8.0-test")

Examples:
  $(basename "$0") 0.8.0
  $(basename "$0") 0.8.0-test

Output:
  dist/template-baseboards-v\$VERSION.tar.gz
  dist/template-basic-v\$VERSION.tar.gz
  dist/template-manifest.json

EOF
}

# Check if help flag is passed
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    print_usage
    exit 0
fi

# Validate arguments
if [[ $# -ne 1 ]]; then
    log_error "Missing required argument: VERSION"
    print_usage
    exit 1
fi

VERSION="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
TEMPLATES_DIR="$DIST_DIR/templates"
STORAGE_BASE_PATH="/app/data/storage"

log_info "Preparing release templates for version: $VERSION"
log_info "Project root: $PROJECT_ROOT"

# Clean and create dist directories
log_info "Setting up dist directories..."
rm -rf "$DIST_DIR"
mkdir -p "$TEMPLATES_DIR"

###############################################################################
# Helper function: Transform package.json workspace dependencies
###############################################################################
transform_package_json() {
    local package_json="$1"
    local version="$2"

    if [[ ! -f "$package_json" ]]; then
        log_error "package.json not found: $package_json"
        return 1
    fi

    log_info "  Transforming dependencies in $(basename "$(dirname "$package_json")")/package.json"

    # Use Node.js to parse and transform the package.json
    node -e "
        const fs = require('fs');
        const packageJson = JSON.parse(fs.readFileSync('$package_json', 'utf8'));

        // Update version
        packageJson.version = '$version';

        // Transform workspace:* dependencies to actual versions
        if (packageJson.dependencies) {
            for (const [name, version] of Object.entries(packageJson.dependencies)) {
                if (version === 'workspace:*') {
                    packageJson.dependencies[name] = '^$version';
                }
            }
        }

        if (packageJson.devDependencies) {
            for (const [name, version] of Object.entries(packageJson.devDependencies)) {
                if (version === 'workspace:*') {
                    packageJson.devDependencies[name] = '^$version';
                }
            }
        }

        fs.writeFileSync('$package_json', JSON.stringify(packageJson, null, 2) + '\n');
    "
}

###############################################################################
# Helper function: Copy template files
###############################################################################
copy_template_structure() {
    local src="$1"
    local dest="$2"
    local template_name="$3"
    local type="${4:-web}"  # Default to 'web', can be 'api' or 'web'

    log_info "Copying $template_name template from $src"

    # Create destination directory
    mkdir -p "$dest"

    # Base exclusions (common to all types)
    local base_excludes=(
        --exclude='.DS_Store'
        --exclude='._*'
        --exclude='.env'
        --exclude='.env.local'
    )

    # Type-specific exclusions
    if [[ "$type" == "api" ]]; then
        # Python/backend exclusions
        local excludes=(
            "${base_excludes[@]}"
            --exclude='.venv'
            --exclude='__pycache__'
            --exclude='*.pyc'
            --exclude='.pytest_cache'
            --exclude='.ruff_cache'
            --exclude='build'
            --exclude='dist'
            --exclude='*.egg-info'
            --exclude='uv.lock'
            --exclude='tests'
            --exclude='test_*.py'
            --exclude='pytest.ini'
            --exclude='MANIFEST.in'
            --exclude='pyrightconfig.json'
            --exclude='baseline-config'
            --exclude='example-config'
            --exclude='examples'
        )
    else
        # Node.js/frontend exclusions
        local excludes=(
            "${base_excludes[@]}"
            --exclude='.next'
            --exclude='node_modules'
            --exclude='dist'
            --exclude='build'
            --exclude='.turbo'
            --exclude='*.tsbuildinfo'
        )
    fi

    # Copy all files with appropriate exclusions
    rsync -a "${excludes[@]}" "$src/" "$dest/"

    log_success "  Copied $template_name template structure"
}

###############################################################################
# Prepare Baseboards Template
###############################################################################
prepare_baseboards_template() {
    log_info "Preparing baseboards template..."

    local template_dir="$TEMPLATES_DIR/baseboards"
    local web_dir="$template_dir/web"

    # Copy baseboards app to web/ directory
    copy_template_structure "$PROJECT_ROOT/apps/baseboards" "$web_dir" "baseboards"

    # Copy web environment file
    if [[ -f "$PROJECT_ROOT/packages/cli-launcher/template-sources/web-env.example" ]]; then
        cp "$PROJECT_ROOT/packages/cli-launcher/template-sources/web-env.example" "$web_dir/.env.example"
        log_success "  Copied web/.env.example"
    fi

    # Transform workspace dependencies
    transform_package_json "$web_dir/package.json" "$VERSION"

    # Create minimal API directory (just config files, no source code)
    # The backend runs from pre-built Docker images, so source code is not needed
    log_info "  Creating minimal API directory..."
    local api_dir="$template_dir/api"
    mkdir -p "$api_dir"

    # Copy API environment file
    if [[ -f "$PROJECT_ROOT/packages/cli-launcher/template-sources/api-env.example" ]]; then
        cp "$PROJECT_ROOT/packages/cli-launcher/template-sources/api-env.example" "$api_dir/.env.example"
        log_success "  Copied api/.env.example"
    else
        log_error "api-env.example not found"
        exit 1
    fi

    # Copy Dockerfile (optional, for users who want to build from source)
    if [[ -f "$PROJECT_ROOT/packages/cli-launcher/template-sources/Dockerfile.api" ]]; then
        cp "$PROJECT_ROOT/packages/cli-launcher/template-sources/Dockerfile.api" "$api_dir/Dockerfile"
        log_success "  Copied api/Dockerfile"
    fi

    # Create a README explaining the setup
    cat > "$api_dir/README.md" << 'EOF'
# Backend API Directory

This directory contains environment configuration for the Boards backend services.

## Pre-built Docker Images

By default, Baseboards uses pre-built Docker images from GitHub Container Registry:
- `ghcr.io/weirdfingers/boards-backend:latest`

This means:
- **No build time** - services start immediately
- **Verified releases** - you get the tested, published backend version
- **Automatic updates** - pull the latest image to get updates

## Configuration

Edit `api/.env` to configure:
- API keys for image generation providers (Replicate, Fal, OpenAI, etc.)
- JWT secrets for authentication
- Other environment variables

See `.env.example` for all available options.

## Building from Source (Advanced)

If you need to customize the backend Python code:

1. Get the source code from: https://github.com/weirdfingers/boards/tree/main/packages/backend
2. Update `compose.yaml` to build from source instead of using pre-built images
3. Place the backend source code in this directory

This is **not recommended** for most users. The pre-built images are the supported path.
EOF
    log_success "  Created api/README.md"

    # Copy shared template files from template-sources
    log_info "  Copying shared template files..."
    cp "$PROJECT_ROOT/packages/cli-launcher/template-sources/compose.yaml" "$template_dir/"
    cp "$PROJECT_ROOT/packages/cli-launcher/template-sources/compose.web.yaml" "$template_dir/"
    cp "$PROJECT_ROOT/packages/cli-launcher/template-sources/Dockerfile.web" "$template_dir/"
    cp "$PROJECT_ROOT/packages/cli-launcher/template-sources/README.md" "$template_dir/"

    # Copy config directory
    mkdir -p "$template_dir/config"
    cp -r "$PROJECT_ROOT/packages/cli-launcher/basic-template/config/"* "$template_dir/config/"

    # Copy docker directory
    if [[ -d "$PROJECT_ROOT/packages/cli-launcher/basic-template/docker" ]]; then
        cp -r "$PROJECT_ROOT/packages/cli-launcher/basic-template/docker" "$template_dir/"
    fi

    # Create extensions directories with README files
    log_info "  Creating extensions directories..."
    mkdir -p "$template_dir/extensions/generators"
    mkdir -p "$template_dir/extensions/plugins"

    if [[ -f "$PROJECT_ROOT/packages/cli-launcher/basic-template/extensions/generators/README.md" ]]; then
        cp "$PROJECT_ROOT/packages/cli-launcher/basic-template/extensions/generators/README.md" "$template_dir/extensions/generators/"
    fi

    if [[ -f "$PROJECT_ROOT/packages/cli-launcher/basic-template/extensions/plugins/README.md" ]]; then
        cp "$PROJECT_ROOT/packages/cli-launcher/basic-template/extensions/plugins/README.md" "$template_dir/extensions/plugins/"
    fi

    # Create data/storage directory with .gitkeep
    log_info "  Creating data/storage directory..."
    mkdir -p "$template_dir/data/storage"
    touch "$template_dir/data/storage/.gitkeep"

    # Create .gitignore if it doesn't exist
    if [[ ! -f "$template_dir/.gitignore" ]]; then
        log_info "  Creating .gitignore..."
        cat > "$template_dir/.gitignore" << 'EOF'
# Dependencies
node_modules/
__pycache__/
*.pyc
pnpm-lock.yaml
package-lock.json
yarn.lock

# Python virtual environments
.venv/
venv/
*.egg-info/

# Build outputs
.next/
dist/
build/
.turbo/
*.tsbuildinfo

# Environment files
.env
.env.local

# Storage (keep directory structure, ignore uploaded files)
data/storage/*
!data/storage/.gitkeep

# Testing & caching
.pytest_cache/
.ruff_cache/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db
EOF
    else
        # Append storage pattern if not present
        if ! grep -q "data/storage/\*" "$template_dir/.gitignore"; then
            log_info "  Updating .gitignore with storage pattern..."
            cat >> "$template_dir/.gitignore" << 'EOF'

# Storage
data/storage/*
!data/storage/.gitkeep
EOF
        fi
    fi

    # Verify storage_config.yaml has correct path
    local storage_config="$template_dir/config/storage_config.yaml"
    if [[ -f "$storage_config" ]]; then
        if grep -q "base_path: \"$STORAGE_BASE_PATH\"" "$storage_config"; then
            log_success "  storage_config.yaml has correct base_path"
        else
            log_warning "  storage_config.yaml may need manual review for base_path"
        fi
    fi

    log_success "Baseboards template prepared at $template_dir"
}

###############################################################################
# Prepare Basic Template
###############################################################################
prepare_basic_template() {
    log_info "Preparing basic template..."

    local template_dir="$TEMPLATES_DIR/basic"

    # Copy basic template (already has proper structure from CLI-2.1)
    copy_template_structure "$PROJECT_ROOT/packages/cli-launcher/basic-template" "$template_dir" "basic"

    # Update version in package.json
    transform_package_json "$template_dir/web/package.json" "$VERSION"

    # Create minimal API directory (required by compose.yaml)
    log_info "  Creating minimal API directory..."
    local api_dir="$template_dir/api"
    mkdir -p "$api_dir"

    # Copy API environment file
    if [[ -f "$PROJECT_ROOT/packages/cli-launcher/template-sources/api-env.example" ]]; then
        cp "$PROJECT_ROOT/packages/cli-launcher/template-sources/api-env.example" "$api_dir/.env.example"
        log_success "  Copied api/.env.example"
    else
        log_error "api-env.example not found"
        exit 1
    fi

    # Copy Dockerfile (optional, for users who want to build from source)
    if [[ -f "$PROJECT_ROOT/packages/cli-launcher/template-sources/Dockerfile.api" ]]; then
        cp "$PROJECT_ROOT/packages/cli-launcher/template-sources/Dockerfile.api" "$api_dir/Dockerfile"
        log_success "  Copied api/Dockerfile"
    fi

    # Create a README explaining the setup
    cat > "$api_dir/README.md" << 'EOF'
# Backend API Directory

This directory contains environment configuration for the Boards backend services.

## Pre-built Docker Images

By default, Baseboards uses pre-built Docker images from GitHub Container Registry:
- `ghcr.io/weirdfingers/boards-backend:latest`

This means:
- **No build time** - services start immediately
- **Verified releases** - you get the tested, published backend version
- **Automatic updates** - pull the latest image to get updates

## Configuration

Edit `api/.env` to configure:
- API keys for image generation providers (Replicate, Fal, OpenAI, etc.)
- JWT secrets for authentication
- Other environment variables

See `.env.example` for all available options.

## Building from Source (Advanced)

If you need to customize the backend Python code:

1. Get the source code from: https://github.com/weirdfingers/boards/tree/main/packages/backend
2. Update `compose.yaml` to build from source instead of using pre-built images
3. Place the backend source code in this directory

This is **not recommended** for most users. The pre-built images are the supported path.
EOF
    log_success "  Created api/README.md"

    # Verify extensions directories exist
    if [[ ! -d "$template_dir/extensions/generators" ]]; then
        log_warning "  extensions/generators directory missing, creating..."
        mkdir -p "$template_dir/extensions/generators"
    fi

    if [[ ! -d "$template_dir/extensions/plugins" ]]; then
        log_warning "  extensions/plugins directory missing, creating..."
        mkdir -p "$template_dir/extensions/plugins"
    fi

    # Verify data/storage exists
    if [[ ! -d "$template_dir/data/storage" ]]; then
        log_warning "  data/storage directory missing, creating..."
        mkdir -p "$template_dir/data/storage"
        touch "$template_dir/data/storage/.gitkeep"
    fi

    # Verify storage_config.yaml path
    local storage_config="$template_dir/config/storage_config.yaml"
    if [[ -f "$storage_config" ]]; then
        if grep -q "base_path: \"$STORAGE_BASE_PATH\"" "$storage_config"; then
            log_success "  storage_config.yaml has correct base_path"
        else
            log_warning "  storage_config.yaml may need manual review for base_path"
        fi
    fi

    log_success "Basic template prepared at $template_dir"
}

###############################################################################
# Create Tarballs
###############################################################################
create_tarballs() {
    log_info "Creating tarballs..."

    cd "$TEMPLATES_DIR"

    # Set COPYFILE_DISABLE to prevent macOS from including ._* (AppleDouble) files
    export COPYFILE_DISABLE=1

    # Create baseboards tarball
    log_info "  Creating template-baseboards-v${VERSION}.tar.gz..."
    tar -czf "$DIST_DIR/template-baseboards-v${VERSION}.tar.gz" baseboards/
    log_success "  Created template-baseboards-v${VERSION}.tar.gz"

    # Create basic tarball
    log_info "  Creating template-basic-v${VERSION}.tar.gz..."
    tar -czf "$DIST_DIR/template-basic-v${VERSION}.tar.gz" basic/
    log_success "  Created template-basic-v${VERSION}.tar.gz"

    unset COPYFILE_DISABLE
    cd "$PROJECT_ROOT"
}

###############################################################################
# Generate Manifest
###############################################################################
generate_manifest() {
    log_info "Generating template manifest..."

    node "$SCRIPT_DIR/generate-template-manifest.js" \
        --version "$VERSION" \
        --templates "$DIST_DIR/template-*.tar.gz" \
        --output "$DIST_DIR/template-manifest.json"

    log_success "Template manifest generated at $DIST_DIR/template-manifest.json"
}

###############################################################################
# Main Execution
###############################################################################

# Execute preparation steps
prepare_baseboards_template
echo ""

prepare_basic_template
echo ""

create_tarballs
echo ""

generate_manifest
echo ""

# Final summary
log_success "✨ Release templates prepared successfully!"
echo ""
log_info "Output files:"
echo "  - $DIST_DIR/template-baseboards-v${VERSION}.tar.gz"
echo "  - $DIST_DIR/template-basic-v${VERSION}.tar.gz"
echo "  - $DIST_DIR/template-manifest.json"
echo ""
log_info "Next steps:"
echo "  1. Test the templates by extracting and verifying them"
echo "  2. Upload tarballs and manifest to your release distribution"
echo ""
