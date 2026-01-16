# Update Up Command to Use Template Downloader

## Description

Refactor the `up` command to use the template downloader instead of bundled templates. This is the integration point that switches from the old bundled template system to the new download-based system.

The changes involve:
- Remove dependency on bundled templates directory
- Use `downloadTemplate()` to fetch templates on demand
- Update scaffolding logic to work with downloaded templates
- Add progress indicators for template downloads
- Handle download errors gracefully with helpful messages
- Maintain backward compatibility where possible

This ticket completes Phase 2 by making the new template system the default for scaffolding.

## Dependencies

- CLI-2.5 (Template downloader)
- CLI-2.6 (Template cache)
- CLI-2.7 (Templates command, for consistency)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/commands/up.ts`

## Testing

### Basic Scaffold Test
```bash
# Fresh scaffold with template download
baseboards up test-project

# Should:
# 1. Prompt for template (or use --template flag)
# 2. Download template (or use cache)
# 3. Extract to test-project/
# 4. Continue with normal scaffolding flow
```

### Cache Hit Test
```bash
# First scaffold (downloads)
baseboards up project1

# Second scaffold (uses cache)
baseboards up project2

# Second should be much faster (no download)
```

### Error Handling Test
```bash
# Test with invalid template
baseboards up test --template nonexistent

# Expected: Clear error message
# "Template 'nonexistent' not found. Available templates: baseboards, basic"

# Test with no internet and no cache
# (disable network)
baseboards up test

# Expected: Helpful error message
# "Failed to download template. Check your internet connection or use --help"
```

### Progress Indicator Test
```bash
# Should show progress during download
baseboards up large-project

# Expected output:
# Downloading template baseboards...
# ████████████████████░░ 80% (9.6 MB / 12 MB)
# Template downloaded successfully
```

### Template Flag Test
```bash
# Specify template explicitly
baseboards up test --template basic

# Should skip interactive prompt and download basic template
```

### Integration Test
Full end-to-end test:
```bash
# Scaffold with new system
baseboards up e2e-test --template baseboards

# Verify all files present
ls e2e-test/
# Should show: web/ config/ docker/ compose.yaml README.md

# Start services
cd e2e-test
baseboards status
# Should work identically to old system
```

## Acceptance Criteria

### Core Changes

- [ ] Remove import/usage of `getTemplatesDir()` from utils
- [ ] Import and use `downloadTemplate()` from template-downloader
- [ ] Import and use `fetchTemplateManifest()` for template validation

### Scaffolding Logic

- [ ] `scaffoldProject()` function updated:
  - [ ] Accept template name as parameter
  - [ ] Call `downloadTemplate(templateName, version, projectDir)`
  - [ ] Remove file copying logic (handled by downloadTemplate)
  - [ ] Keep post-scaffold logic (env file generation, etc.)

### Template Selection

- [ ] Default template: baseboards (if no --template flag)
- [ ] Template validation before download:
  ```typescript
  const manifest = await fetchTemplateManifest(cliVersion);
  const templateNames = manifest.templates.map(t => t.name);

  if (!templateNames.includes(selectedTemplate)) {
    throw new Error(`Template not found. Available: ${templateNames.join(", ")}`);
  }
  ```

### User Experience

- [ ] Progress indicator shown during download
- [ ] Success message after download: "Template downloaded successfully"
- [ ] Cache hit shows faster completion (no "Downloading..." message)
- [ ] First-time download shows estimated size

### Error Handling

- [ ] Network errors caught and reported with helpful message
- [ ] Invalid template name shows available templates
- [ ] Checksum mismatch triggers re-download (via cache logic)
- [ ] Download interruption handled (cleanup partial files)
- [ ] Graceful fallback messages

### Backward Compatibility

- [ ] Existing flags still work (--attach, --ports, --fresh)
- [ ] Environment variable generation unchanged
- [ ] API key prompting unchanged
- [ ] Docker compose workflow unchanged
- [ ] Migration workflow unchanged

### Quality

- [ ] No hardcoded template paths
- [ ] Uses CLI version from package.json for template version
- [ ] TypeScript compiles without errors
- [ ] Existing tests still pass (or updated appropriately)
- [ ] New behavior covered by tests

### Cleanup

- [ ] Old template bundling logic removed (if any remains)
- [ ] Dead code removed
- [ ] Comments updated to reflect new system
- [ ] No references to old template paths

### Documentation

- [ ] Function JSDoc comments updated
- [ ] Help text mentions template download
- [ ] Error messages are user-friendly
