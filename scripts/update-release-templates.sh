#!/bin/bash

###############################################################################
# Update Release Templates
#
# This script uploads template tarballs and manifest to an existing GitHub
# release, replacing any existing assets with the same names.
#
# Prerequisites:
#   - gh CLI installed and authenticated
#   - Template files already built via ./scripts/prepare-release-templates.sh
#
# Usage:
#   ./scripts/update-release-templates.sh <VERSION>
#
# Example:
#   ./scripts/update-release-templates.sh 0.9.5
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

Upload template tarballs and manifest to an existing GitHub release,
replacing any existing assets with the same names.

Arguments:
  VERSION    Version string (e.g., "0.9.5")

Prerequisites:
  - gh CLI installed and authenticated
  - Template files built via ./scripts/prepare-release-templates.sh

Examples:
  $(basename "$0") 0.9.5

Files uploaded:
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

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    log_error "gh CLI is not installed"
    echo "  Install from: https://cli.github.com/"
    exit 1
fi

# Check if gh is authenticated
if ! gh auth status &> /dev/null; then
    log_error "gh CLI is not authenticated"
    echo "  Run: gh auth login"
    exit 1
fi

# Define expected files
BASEBOARDS_TARBALL="$DIST_DIR/template-baseboards-v${VERSION}.tar.gz"
BASIC_TARBALL="$DIST_DIR/template-basic-v${VERSION}.tar.gz"
MANIFEST="$DIST_DIR/template-manifest.json"

# Check if template files exist
log_info "Checking for template files..."

missing_files=()
if [[ ! -f "$BASEBOARDS_TARBALL" ]]; then
    missing_files+=("template-baseboards-v${VERSION}.tar.gz")
fi
if [[ ! -f "$BASIC_TARBALL" ]]; then
    missing_files+=("template-basic-v${VERSION}.tar.gz")
fi
if [[ ! -f "$MANIFEST" ]]; then
    missing_files+=("template-manifest.json")
fi

if [[ ${#missing_files[@]} -gt 0 ]]; then
    log_error "Missing template files in dist/:"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done
    echo ""
    log_info "Run first: ./scripts/prepare-release-templates.sh $VERSION"
    exit 1
fi

log_success "All template files found"

# Check if release exists
log_info "Checking for release v${VERSION}..."

if ! gh release view "v${VERSION}" &> /dev/null; then
    log_error "Release v${VERSION} does not exist"
    echo ""
    log_info "Available releases:"
    gh release list --limit 5
    exit 1
fi

log_success "Release v${VERSION} found"

# Upload files
log_info "Uploading template files to release v${VERSION}..."

gh release upload "v${VERSION}" \
    "$BASEBOARDS_TARBALL" \
    "$BASIC_TARBALL" \
    "$MANIFEST" \
    --clobber

log_success "Template files uploaded successfully!"

echo ""
log_info "Uploaded files:"
echo "  - template-baseboards-v${VERSION}.tar.gz"
echo "  - template-basic-v${VERSION}.tar.gz"
echo "  - template-manifest.json"

echo ""
log_info "View release: gh release view v${VERSION}"
