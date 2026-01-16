# Create Template Manifest Schema

## Description

Define the JSON schema for the template manifest file that will be published to GitHub Releases alongside template tarballs. This manifest provides metadata about available templates, including descriptions, checksums, sizes, and features.

The manifest will be consumed by the CLI to:
- List available templates (`baseboards templates` command)
- Validate downloaded templates
- Display template information during interactive selection
- Verify integrity of downloaded files

Create a Node.js script that generates the manifest from template tarballs, calculating SHA-256 checksums and extracting metadata.

## Dependencies

None (can be done in parallel with CLI-2.1)

## Files to Create/Modify

- Create `/scripts/generate-template-manifest.js`

## Testing

### Schema Validation Test
```bash
# Run the script with test tarballs
node scripts/generate-template-manifest.js \
  --version 0.8.0 \
  --templates "dist/template-baseboards-v0.8.0.tar.gz,dist/template-basic-v0.8.0.tar.gz" \
  --output dist/template-manifest.json

# Verify output is valid JSON
cat dist/template-manifest.json | jq .
```

### Checksum Test
```bash
# Verify checksums are correct
EXPECTED=$(sha256sum dist/template-baseboards-v0.8.0.tar.gz | awk '{print $1}')
MANIFEST=$(cat dist/template-manifest.json | jq -r '.templates[] | select(.name=="baseboards") | .checksum')

echo "Expected: sha256:$EXPECTED"
echo "Manifest: $MANIFEST"

# Should match
```

### File Size Test
```bash
# Verify file sizes are accurate
EXPECTED=$(stat -f%z dist/template-baseboards-v0.8.0.tar.gz)
MANIFEST=$(cat dist/template-manifest.json | jq -r '.templates[] | select(.name=="baseboards") | .size')

echo "Expected: $EXPECTED"
echo "Manifest: $MANIFEST"

# Should match
```

### Multiple Templates Test
```bash
# Verify multiple templates are handled
node scripts/generate-template-manifest.js \
  --version 0.8.0 \
  --templates "dist/template-*.tar.gz" \
  --output dist/test-manifest.json

# Should include both baseboards and basic
cat dist/test-manifest.json | jq '.templates | length'
# Should output: 2
```

## Acceptance Criteria

- [ ] Script file created at `/scripts/generate-template-manifest.js`
- [ ] Script accepts --version flag (e.g., "0.8.0")
- [ ] Script accepts --templates flag (comma-separated list or glob)
- [ ] Script accepts --output flag (default: stdout)
- [ ] Generated manifest includes version field
- [ ] Generated manifest includes templates array
- [ ] Each template entry includes:
  - `name` (e.g., "baseboards", "basic")
  - `description` (human-readable description)
  - `file` (filename of tarball)
  - `size` (file size in bytes)
  - `checksum` (sha256 hash with "sha256:" prefix)
  - `frameworks` (array of framework names, e.g., ["next.js"])
  - `features` (array of feature tags, e.g., ["auth", "generators"])
- [ ] SHA-256 checksums calculated correctly
- [ ] File sizes calculated correctly
- [ ] Output is valid JSON
- [ ] Script handles missing files gracefully with error message
- [ ] Script validates all required fields are present
- [ ] Generated manifest matches example schema from design doc
- [ ] Script includes usage help (--help flag)
