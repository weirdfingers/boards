# Add --template Flag

## Description

Add a `--template` command-line flag to the `up` command that allows users to explicitly specify which template to use for scaffolding. This provides a non-interactive way to select templates, useful for scripting and CI/CD environments.

When the flag is provided, skip the interactive template selection prompt. When not provided, the interactive selector (CLI-5.2) will be used.

## Dependencies

None (foundational for Phase 5)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/types.ts`
- Modify `/packages/cli-launcher/src/commands/up.ts`

## Testing

### Flag Recognition Test
```bash
# Test flag is recognized
baseboards up test --template basic

# Should not error
# Should use basic template
```

### Template Validation Test
```bash
# Test with valid template
baseboards up test1 --template baseboards
baseboards up test2 --template basic

# Both should work

# Test with invalid template
baseboards up test3 --template nonexistent

# Expected error:
# "Template 'nonexistent' not found. Available templates: baseboards, basic"
```

### Help Text Test
```bash
baseboards up --help

# Should show:
# --template <name>    Frontend template to use (baseboards, basic)
```

### Combined Flags Test
```bash
# Test with other flags
baseboards up test --template basic --app-dev --attach

# Should work without conflicts
```

## Acceptance Criteria

### types.ts Changes

- [ ] Add `template` field to ProjectContext:
  ```typescript
  interface ProjectContext {
    dir: string;
    name: string;
    version: string;
    ports: { /*...*/ };
    appDev: boolean;
    packageManager?: PackageManager;
    template: string; // NEW FIELD
  }
  ```

### up.ts Changes

- [ ] Add option to command:
  ```typescript
  .option("--template <name>", "Frontend template to use (baseboards, basic)")
  ```

- [ ] Parse and validate flag:
  ```typescript
  const templateName = options.template; // Can be undefined if not provided

  // Validation will happen later in the flow
  ```

- [ ] Add template validation function:
  ```typescript
  async function validateTemplate(
    templateName: string,
    version: string
  ): Promise<void> {
    const manifest = await fetchTemplateManifest(version);
    const availableTemplates = manifest.templates.map(t => t.name);

    if (!availableTemplates.includes(templateName)) {
      throw new Error(
        `Template '${templateName}' not found. Available templates: ${availableTemplates.join(", ")}`
      );
    }
  }
  ```

### Validation Timing

- [ ] Validate early in the flow (before scaffolding):
  ```typescript
  if (options.template) {
    await validateTemplate(options.template, cliVersion);
  }
  ```

### Template Selection Flow

- [ ] If --template provided, use it directly:
  ```typescript
  let selectedTemplate: string;

  if (options.template) {
    await validateTemplate(options.template, cliVersion);
    selectedTemplate = options.template;
  } else {
    // TODO: Interactive selection (CLI-5.2)
    selectedTemplate = "baseboards"; // Default for now
  }
  ```

- [ ] Add to context:
  ```typescript
  const ctx: ProjectContext = {
    // ... existing fields
    template: selectedTemplate,
  };
  ```

### Error Handling

- [ ] Invalid template shows clear error message
- [ ] Lists available templates in error
- [ ] Network error fetching manifest handled gracefully
- [ ] Empty/whitespace template name rejected

### Help Text

- [ ] Flag appears in `baseboards up --help` output
- [ ] Description mentions available templates
- [ ] Format: `--template <name>`

### Default Behavior

- [ ] No flag = interactive selection (to be implemented in CLI-5.2)
- [ ] For now: defaults to "baseboards" with a TODO comment
- [ ] Flag provided = use specified template

### Quality

- [ ] TypeScript compiles without errors
- [ ] Validation uses template downloader utilities (CLI-2.5)
- [ ] Error messages consistent with CLI style
- [ ] No hardcoded template names (fetch from manifest)

### Documentation

- [ ] JSDoc comment on template field:
  ```typescript
  /**
   * Name of the frontend template to use for scaffolding.
   * Examples: "baseboards", "basic"
   */
  template: string;
  ```

### Future Integration

- [ ] Will be used by interactive selector (CLI-5.2)
- [ ] Will be used by template downloader (already in CLI-2.8)
- [ ] Validation logic reusable in interactive flow
