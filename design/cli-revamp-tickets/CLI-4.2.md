# Implement Package Manager Selection

## Description

Create an interactive prompt that asks users to select their preferred package manager (pnpm, npm, yarn, or bun) when using `--app-dev` mode. The selected package manager will be used to install dependencies and will be shown in the success instructions.

This utility will be used by CLI-4.4 (dependency installation) and CLI-4.5 (success message instructions).

## Dependencies

None (can be done in parallel with CLI-4.1)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/utils.ts`

## Testing

### Interactive Prompt Test
```typescript
import { promptPackageManager } from "./utils";

// Run interactively
const pm = await promptPackageManager();
console.log(`Selected: ${pm}`);
// User selects from menu, function returns: "pnpm" | "npm" | "yarn" | "bun"
```

### All Options Test
```bash
# Test each option can be selected
# Manual testing required - run and select each option
node -e "require('./dist/utils.js').promptPackageManager().then(console.log)"

# Try each: pnpm, npm, yarn, bun
```

### Cancel Handling Test
```bash
# Test Ctrl+C during selection
node -e "require('./dist/utils.js').promptPackageManager().then(console.log)"
# Press Ctrl+C

# Should: Exit gracefully or throw catchable error
```

### Return Type Test
```typescript
// Verify return type is correct
const pm: PackageManager = await promptPackageManager();
// TypeScript should be happy

type PackageManager = "pnpm" | "npm" | "yarn" | "bun";
```

## Acceptance Criteria

### Type Definition

- [ ] Define PackageManager type:
  ```typescript
  type PackageManager = "pnpm" | "npm" | "yarn" | "bun";
  ```

### Function Implementation

- [ ] Function created in utils.ts:
  ```typescript
  export async function promptPackageManager(): Promise<PackageManager> {
    // Implementation
  }
  ```

- [ ] Uses prompts library (already a dependency):
  ```typescript
  import prompts from "prompts";
  ```

- [ ] Creates interactive select prompt:
  ```typescript
  const { packageManager } = await prompts({
    type: "select",
    name: "packageManager",
    message: "Select your package manager:",
    choices: [
      { title: "pnpm", value: "pnpm" },
      { title: "npm", value: "npm" },
      { title: "yarn", value: "yarn" },
      { title: "bun", value: "bun" },
    ],
    initial: 0, // Default to pnpm
  });
  ```

- [ ] Returns selected package manager
- [ ] Handles cancellation (Ctrl+C):
  ```typescript
  if (!packageManager) {
    console.log("\nPackage manager selection cancelled");
    process.exit(0);
  }
  ```

### User Experience

- [ ] Prompt message clear and concise
- [ ] Options displayed in sensible order (pnpm first as recommendation)
- [ ] Arrow keys work for navigation
- [ ] Enter key confirms selection
- [ ] Ctrl+C cancels gracefully

### Integration Points

- [ ] Export both type and function:
  ```typescript
  export type PackageManager = "pnpm" | "npm" | "yarn" | "bun";
  export async function promptPackageManager(): Promise<PackageManager>;
  ```

- [ ] Function documented with JSDoc:
  ```typescript
  /**
   * Prompts user to select their preferred package manager.
   * @returns Selected package manager: pnpm, npm, yarn, or bun
   * @throws Exits process if user cancels
   */
  ```

### Quality

- [ ] TypeScript types are strict (no `any`)
- [ ] Follows existing utils.ts code style
- [ ] Consistent with other prompt functions in codebase
- [ ] No console warnings or errors
- [ ] Handles edge cases gracefully

### Testing

- [ ] Function compiles without errors
- [ ] Can be called from up.ts (import works)
- [ ] Return value has correct type
- [ ] Manual testing confirms all options selectable

### Future Usage

- [ ] Will be called in CLI-4.4 when --app-dev flag is set
- [ ] Return value will be used to run install command
- [ ] Return value will be shown in success message (CLI-4.5)
