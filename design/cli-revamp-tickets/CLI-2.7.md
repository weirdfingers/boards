# Add Templates Command

## Description

Create a new CLI command `baseboards templates` that lists available templates with their metadata (description, size, features). This provides users with visibility into what templates are available before scaffolding.

The command should:
- Fetch the template manifest from GitHub Releases
- Display template information in a readable format
- Support a `--refresh` flag to clear cache and re-fetch
- Work with cached manifest for offline capability
- Show template descriptions, frameworks, and features

This gives users discoverability and helps them choose the right template for their needs.

## Dependencies

- CLI-2.5 (Template downloader with manifest fetching)

## Files to Create/Modify

- Create `/packages/cli-launcher/src/commands/templates.ts`
- Modify `/packages/cli-launcher/src/index.ts` (register command)

## Testing

### Basic Usage Test
```bash
baseboards templates

# Expected output:
# Available templates for v0.8.0:
#
# baseboards
#   Full-featured Boards application (recommended)
#   Frameworks: next.js
#   Features: auth, generators, boards, themes
#   Size: 12.0 MB
#
# basic
#   Minimal Next.js starter with @weirdfingers/boards
#   Frameworks: next.js
#   Features: minimal
#   Size: 45.0 KB
```

### Refresh Flag Test
```bash
# First call (downloads manifest)
baseboards templates

# Corrupt cached manifest to test refresh
echo "invalid" > ~/.baseboards/templates/manifest-v0.8.0.json

# Refresh (should re-download)
baseboards templates --refresh

# Should display correct templates (manifest re-fetched)
```

### Version Flag Test
```bash
# List templates for specific version
baseboards templates --version 0.7.0

# Should show templates available in that version
```

### Error Handling Test
```bash
# Test with no internet connection
# (disconnect network)
baseboards templates

# Should fall back to cached manifest if available
# Or show helpful error message if not cached
```

### Help Text Test
```bash
baseboards templates --help

# Expected output:
# Usage: baseboards templates [options]
#
# List available templates
#
# Options:
#   --refresh     Clear cache and re-fetch templates
#   --version <v> Show templates for specific version
#   -h, --help    display help for command
```

## Acceptance Criteria

### Command Implementation

- [ ] File created at `/packages/cli-launcher/src/commands/templates.ts`
- [ ] Command registered in `/packages/cli-launcher/src/index.ts`:
  ```typescript
  program
    .command("templates")
    .description("List available templates")
    .option("--refresh", "Clear cache and re-fetch templates")
    .option("--version <version>", "Show templates for specific version")
    .action(templates);
  ```

### Functionality

- [ ] Fetches template manifest using `fetchTemplateManifest()` from CLI-2.5
- [ ] Uses CLI version by default (from package.json)
- [ ] Respects `--version` flag if provided
- [ ] Displays each template with:
  - [ ] Name (bold or highlighted)
  - [ ] Description
  - [ ] Frameworks list
  - [ ] Features list
  - [ ] Size (human-readable: KB, MB)
- [ ] `--refresh` flag clears cache before fetching
- [ ] Uses cached manifest if available (no network call)
- [ ] Falls back to network if cache miss

### Output Format

- [ ] Clean, readable output (not raw JSON)
- [ ] Aligned columns or clear sections
- [ ] Size displayed in human-readable format (45 KB, 12 MB)
- [ ] Recommended template highlighted or marked
- [ ] Version number shown in header

### Error Handling

- [ ] Network error shows helpful message
- [ ] Invalid version shows error: "Version X.Y.Z not found"
- [ ] No templates available shows appropriate message
- [ ] Graceful degradation if manifest format unexpected

### Help Text

- [ ] Help flag works: `baseboards templates --help`
- [ ] Description clear and concise
- [ ] Options documented

### Quality

- [ ] Follows CLI package code style
- [ ] Uses existing utilities (cli.log, colors from utils)
- [ ] TypeScript types properly defined
- [ ] Error handling consistent with other commands

### Integration

- [ ] Command appears in main help: `baseboards --help`
- [ ] No breaking changes to existing commands
- [ ] Works in CI/CD environments (handles missing internet gracefully)
