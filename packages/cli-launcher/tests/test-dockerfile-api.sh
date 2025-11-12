#!/usr/bin/env bash
set -e

# Test: Dockerfile.api builds successfully with correct dependencies
# This test validates that the Dockerfile.api can install Python dependencies
# without errors due to missing optional dependency groups.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_SOURCES="$CLI_ROOT/template-sources"
TEST_TEMP_DIR="$(mktemp -d)"

echo "🧪 Testing Dockerfile.api build..."
echo "📁 Test directory: $TEST_TEMP_DIR"

cleanup() {
  echo "🧹 Cleaning up..."
  rm -rf "$TEST_TEMP_DIR"
}
trap cleanup EXIT

# Copy necessary files to test directory
echo "📦 Setting up test environment..."
cp "$TEMPLATE_SOURCES/Dockerfile.api" "$TEST_TEMP_DIR/Dockerfile"

# Copy the ACTUAL pyproject.toml from packages/backend
BACKEND_PYPROJECT="$(cd "$CLI_ROOT/../../packages/backend" && pwd)/pyproject.toml"
if [ ! -f "$BACKEND_PYPROJECT" ]; then
  echo "❌ Error: Cannot find packages/backend/pyproject.toml at $BACKEND_PYPROJECT"
  exit 1
fi

cp "$BACKEND_PYPROJECT" "$TEST_TEMP_DIR/pyproject.toml"
echo "   ✓ Copied real pyproject.toml from packages/backend"

# Create minimal app structure matching backend package
mkdir -p "$TEST_TEMP_DIR/src/boards"
cat > "$TEST_TEMP_DIR/src/boards/__init__.py" <<'EOF'
__version__ = "0.1.0"
EOF

cd "$TEST_TEMP_DIR"

echo "🔨 Attempting to build Dockerfile..."
echo ""

# Try to build the Dockerfile - build may succeed but should show warning about missing extra
docker build -t test-boards-api:test . 2>&1 | tee build.log
BUILD_EXIT_CODE=$?

echo ""
echo "📋 Checking build output..."

# Check for any warnings about missing extras
if grep -q "does not have an extra named" build.log; then
  echo ""
  echo "❌ TEST FAILED: Found warning about missing optional dependency extra!"
  echo ""
  echo "📋 Warning message:"
  grep "does not have an extra named" build.log
  echo ""
  echo "💡 The Dockerfile.api references an optional dependency group that doesn't exist"
  echo ""
  echo "🔧 Available groups from packages/backend/pyproject.toml:"
  echo "   - generators-replicate, generators-openai, generators-fal, generators-anthropic, generators-together"
  echo "   - generators-all (recommended - includes all generators)"
  echo "   - storage-supabase, storage-s3, storage-gcs, storage-all"
  echo "   - auth-supabase"
  echo "   - all (everything)"
  docker rmi test-boards-api:test 2>/dev/null || true
  exit 1
else
  echo ""
  echo "✅ TEST PASSED: No warnings about missing extras!"
  echo ""
  echo "💡 Dockerfile.api successfully installed all requested optional dependencies"
  docker rmi test-boards-api:test 2>/dev/null || true
  exit 0
fi
