# Implement Interactive Template Selector

## Description

Create an interactive prompt that displays available templates with their descriptions and allows users to select one when the `--template` flag is not provided. This provides a user-friendly way to discover and choose templates.

The selector should:
- Fetch available templates from the manifest
- Display template names, descriptions, and features
- Default to "baseboards" (recommended)
- Allow arrow key navigation
- Support cancellation (Ctrl+C)

## Dependencies

- CLI-2.7 (Templates command for consistency)
- CLI-5.1 (--template flag for integration)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/commands/up.ts`

## Testing

### Interactive Selection Test
```bash
# Run without --template flag
baseboards up test

# Expected:
# ? Select a frontend template: (Use arrow keys)
# ❯ baseboards    Full-featured Boards application (recommended)
#   basic         Minimal Next.js starter with @weirdfingers/boards

# User selects with arrow keys and Enter
```

### Default Selection Test
```bash
# Run and immediately press Enter (accept default)
baseboards up test

# Should select "baseboards" (first option)
```

### Description Display Test
```bash
# Verify descriptions are shown
baseboards up test

# Each option should show:
# - Template name
# - Description from manifest
# - "(recommended)" tag on baseboards
```

### Cancel Test
```bash
# Press Ctrl+C during selection
baseboards up test
# (Ctrl+C)

# Expected:
# "Template selection cancelled"
# Process exits gracefully
```

### Skip When Flag Provided Test
```bash
# Should NOT prompt when --template provided
baseboards up test --template basic

# Should go directly to scaffolding
# No prompt shown
```

## Acceptance Criteria

### Function Implementation

- [ ] Create template selector function:
  ```typescript
  async function promptTemplateSelection(
    version: string
  ): Promise<string> {
    // Fetch manifest
    const manifest = await fetchTemplateManifest(version);

    // Build choices
    const choices = manifest.templates.map((template, index) => ({
      title: template.name === "baseboards"
        ? `${template.name}    ${template.description} (recommended)`
        : `${template.name}         ${template.description}`,
      value: template.name,
    }));

    // Prompt user
    const { selectedTemplate } = await prompts({
      type: "select",
      name: "selectedTemplate",
      message: "Select a frontend template:",
      choices: choices,
      initial: 0, // Default to first (baseboards)
    });

    // Handle cancellation
    if (!selectedTemplate) {
      console.log("\nTemplate selection cancelled");
      process.exit(0);
    }

    return selectedTemplate;
  }
  ```

### Integration with up Command

- [ ] Update template selection flow:
  ```typescript
  let selectedTemplate: string;

  if (options.template) {
    // Explicit flag provided
    await validateTemplate(options.template, cliVersion);
    selectedTemplate = options.template;
  } else {
    // Interactive selection
    selectedTemplate = await promptTemplateSelection(cliVersion);
  }

  const ctx: ProjectContext = {
    // ...
    template: selectedTemplate,
  };
  ```

### User Experience

- [ ] Prompt message clear and concise
- [ ] Template names displayed prominently
- [ ] Descriptions shown inline
- [ ] "recommended" tag on baseboards
- [ ] Arrow keys navigate options
- [ ] Enter confirms selection
- [ ] Ctrl+C cancels gracefully

### Display Formatting

- [ ] Consistent spacing and alignment
- [ ] Descriptions fit on one line (or truncate gracefully)
- [ ] Recommended template stands out visually
- [ ] Uses prompts library styling

### Error Handling

- [ ] Network error fetching manifest handled:
  ```typescript
  try {
    const manifest = await fetchTemplateManifest(version);
  } catch (error) {
    console.error("Failed to fetch template list. Check your internet connection.");
    console.log("Falling back to default template: baseboards");
    return "baseboards"; // Graceful fallback
  }
  ```

- [ ] Empty manifest handled (show error, don't crash)
- [ ] Cancellation exits process cleanly

### Caching Integration

- [ ] Uses cached manifest if available (from CLI-2.6)
- [ ] Falls back to network if cache miss
- [ ] Quick response when cached

### Quality

- [ ] Uses existing `prompts` library
- [ ] Consistent with other interactive prompts (package manager selection)
- [ ] TypeScript types strict
- [ ] No hardcoded template names

### Documentation

- [ ] Function documented with JSDoc:
  ```typescript
  /**
   * Prompts user to select a frontend template from available options.
   * Fetches template manifest and displays interactive selection.
   * @param version CLI version to fetch templates for
   * @returns Selected template name
   */
  ```

### Future Extensibility

- [ ] Easy to add more templates (just update manifest)
- [ ] Template metadata (features, frameworks) available but not shown yet
- [ ] Could be enhanced with more details in future (CLI-5.3)

### Testing

- [ ] Interactive selection works
- [ ] Default selection works (press Enter immediately)
- [ ] Cancellation works (Ctrl+C)
- [ ] All templates selectable
- [ ] Integrates with --template flag properly (no prompt when flag provided)
- [ ] Network errors handled gracefully
