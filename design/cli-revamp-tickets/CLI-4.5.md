# Update Success Message for App-Dev

## Description

Update the success message shown after `baseboards up` completes to provide appropriate instructions based on whether app-dev mode was used. In app-dev mode, show instructions for starting the frontend locally. In default mode, show the standard message with all service URLs.

This completes the app-dev user experience by guiding users on what to do next.

## Dependencies

- CLI-4.4 (Package manager must be selected and stored)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/commands/up.ts`

## Testing

### Default Mode Message Test
```bash
baseboards up test-default

# Expected output:
# ✅ Baseboards is running!
#
#    Web:      http://localhost:3300
#    API:      http://localhost:8800
#    GraphQL:  http://localhost:8800/graphql
#
# View logs: baseboards logs test-default -f
# Stop:      baseboards down test-default
```

### App-Dev Mode Message Test
```bash
baseboards up test-appdev --app-dev
# Select pnpm as package manager

# Expected output:
# ✅ Backend services are running!
#
#    API:      http://localhost:8800
#    GraphQL:  http://localhost:8800/graphql
#
# To start the frontend:
#
#    cd test-appdev/web
#    pnpm dev
#
# The frontend will be available at http://localhost:3000
#
# View logs: baseboards logs test-appdev -f
# Stop:      baseboards down test-appdev
```

### Package Manager Variation Test
```bash
# Test with npm
baseboards up test-npm --app-dev
# Select npm

# Should show: "npm run dev"

# Test with yarn
baseboards up test-yarn --app-dev
# Select yarn

# Should show: "yarn dev"

# Test with bun
baseboards up test-bun --app-dev
# Select bun

# Should show: "bun dev"
```

### Relative Path Test
```bash
# Test from different directory
mkdir /tmp/projects
cd /tmp/projects
baseboards up my-project --app-dev

# Should show: "cd my-project/web"
# NOT: "cd /tmp/projects/my-project/web"
```

## Acceptance Criteria

### Message Function Refactor

- [ ] Create separate functions for each message type:
  ```typescript
  function printDefaultSuccessMessage(ctx: ProjectContext): void {
    // Shows all services including web
  }

  function printAppDevSuccessMessage(ctx: ProjectContext): void {
    // Shows backend services + local dev instructions
  }
  ```

### Main Success Function

- [ ] Update success message dispatch:
  ```typescript
  function printSuccessMessage(ctx: ProjectContext): void {
    if (ctx.appDev) {
      printAppDevSuccessMessage(ctx);
    } else {
      printDefaultSuccessMessage(ctx);
    }
  }
  ```

### Default Mode Message

- [ ] Shows all service URLs:
  - [ ] Web: http://localhost:{WEB_PORT}
  - [ ] API: http://localhost:{API_PORT}
  - [ ] GraphQL: http://localhost:{API_PORT}/graphql

- [ ] Shows management commands:
  - [ ] View logs command
  - [ ] Stop command

### App-Dev Mode Message

- [ ] Shows only backend URLs:
  - [ ] API: http://localhost:{API_PORT}
  - [ ] GraphQL: http://localhost:{API_PORT}/graphql
  - [ ] NO web URL (will be local)

- [ ] Shows frontend startup instructions:
  - [ ] "To start the frontend:"
  - [ ] "cd {project-dir}/web"
  - [ ] "{packageManager} dev"
  - [ ] "The frontend will be available at http://localhost:3000"

- [ ] Shows management commands (same as default)

### Package Manager Detection

- [ ] Uses stored package manager from context:
  ```typescript
  const pmCommand = getDevCommand(ctx.packageManager || "pnpm");

  function getDevCommand(pm: PackageManager): string {
    const commands = {
      pnpm: "pnpm dev",
      npm: "npm run dev",
      yarn: "yarn dev",
      bun: "bun dev",
    };
    return commands[pm];
  }
  ```

### Path Handling

- [ ] Shows relative path to web directory:
  ```typescript
  const relativeWebPath = path.relative(process.cwd(), path.join(ctx.dir, "web"));
  console.log(`cd ${relativeWebPath}`);
  ```

- [ ] If project dir is current dir, shows:
  ```
  cd web
  ```

### Formatting

- [ ] Uses consistent formatting with existing message
- [ ] Proper spacing and alignment
- [ ] Uses colors/formatting utilities from codebase
- [ ] Checkmark emoji (✅) or styled "Success" indicator
- [ ] Clear sections and whitespace

### Quality

- [ ] No hardcoded values
- [ ] Uses ctx.ports for port numbers
- [ ] Uses ctx.name for project name
- [ ] Uses ctx.packageManager for dev command
- [ ] Consistent with CLI style guide

### Edge Cases

- [ ] Handles missing packageManager (default to pnpm with warning)
- [ ] Handles long project names (wrapping/truncation)
- [ ] Handles custom ports (shows actual, not default)

### Documentation

- [ ] Functions documented with JSDoc
- [ ] Comments explain app-dev vs default distinction
- [ ] Message text clear and helpful

### Testing

- [ ] Manual test: default mode shows correct URLs
- [ ] Manual test: app-dev mode shows correct instructions
- [ ] Manual test: each package manager shown correctly
- [ ] Manual test: relative paths correct from various directories
- [ ] Message formatting looks good in terminal
- [ ] All URLs and commands are copy-pasteable
