# Add App-Dev Mode Integration Tests

## Description

Create automated integration tests for the app-dev mode functionality to verify that the CLI correctly handles local frontend development. Tests should cover compose file loading, package manager selection, dependency installation, and success messages.

These tests ensure app-dev mode works reliably and catch regressions.

## Dependencies

- CLI-4.5 (App-dev mode implementation complete)

## Files to Create/Modify

- Create `/packages/cli-launcher/tests/app-dev.test.ts`

## Testing

### Run Tests
```bash
cd packages/cli-launcher
pnpm test app-dev.test.ts

# Should: All tests pass
# Should: Coverage >80% for app-dev logic
```

### Test in CI
```bash
# Tests should run in CI pipeline
# Should pass consistently
```

## Acceptance Criteria

### Test Setup

- [ ] Test file created at correct path
- [ ] Uses testing framework (Jest, Vitest, or existing)
- [ ] Mock Docker commands (no real containers)
- [ ] Mock package manager commands (no real installs)
- [ ] Mock filesystem operations where appropriate
- [ ] Setup and teardown functions

### Compose File Loading Tests

- [ ] **Default mode** (no --app-dev):
  ```typescript
  describe("compose file loading - default mode", () => {
    it("should load both base and web compose files", () => {
      const ctx = createTestContext({ appDev: false });
      const files = getComposeFiles(ctx);

      expect(files).toContain("compose.yaml");
      expect(files).toContain("compose.web.yaml");
      expect(files).toHaveLength(2);
    });

    it("should start web service", async () => {
      // Mock docker compose up
      await upCommand({ appDev: false });

      // Assert docker compose called with both files
      expect(mockDockerCompose).toHaveBeenCalledWith(
        expect.arrayContaining(["-f", "compose.yaml", "-f", "compose.web.yaml"])
      );
    });
  });
  ```

- [ ] **App-dev mode** (with --app-dev):
  ```typescript
  describe("compose file loading - app-dev mode", () => {
    it("should load only base compose file", () => {
      const ctx = createTestContext({ appDev: true });
      const files = getComposeFiles(ctx);

      expect(files).toContain("compose.yaml");
      expect(files).not.toContain("compose.web.yaml");
      expect(files).toHaveLength(1);
    });

    it("should not start web service", async () => {
      // Mock docker compose up
      await upCommand({ appDev: true });

      // Assert docker compose called with only base file
      expect(mockDockerCompose).toHaveBeenCalledWith(
        expect.arrayContaining(["-f", "compose.yaml"])
      );
      expect(mockDockerCompose).not.toHaveBeenCalledWith(
        expect.stringContaining("compose.web.yaml")
      );
    });
  });
  ```

### Service Count Tests

- [ ] **Verify service count**:
  ```typescript
  it("should start 5 services in default mode", async () => {
    // Mock docker compose ps output
    const services = await getRunningServices(defaultCtx);

    expect(services).toHaveLength(5);
    expect(services).toContain("db");
    expect(services).toContain("cache");
    expect(services).toContain("api");
    expect(services).toContain("worker");
    expect(services).toContain("web");
  });

  it("should start 4 services in app-dev mode", async () => {
    // Mock docker compose ps output
    const services = await getRunningServices(appDevCtx);

    expect(services).toHaveLength(4);
    expect(services).toContain("db");
    expect(services).toContain("cache");
    expect(services).toContain("api");
    expect(services).toContain("worker");
    expect(services).not.toContain("web");
  });
  ```

### Package Manager Selection Tests

- [ ] **Prompt behavior**:
  ```typescript
  describe("package manager selection", () => {
    it("should not prompt in default mode", async () => {
      await upCommand({ appDev: false });

      expect(mockPrompt).not.toHaveBeenCalled();
    });

    it("should prompt in app-dev mode", async () => {
      mockPrompt.mockResolvedValue({ packageManager: "pnpm" });

      await upCommand({ appDev: true });

      expect(mockPrompt).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "select",
          message: expect.stringContaining("package manager"),
        })
      );
    });

    it("should support all package managers", async () => {
      const packageManagers = ["pnpm", "npm", "yarn", "bun"];

      for (const pm of packageManagers) {
        mockPrompt.mockResolvedValue({ packageManager: pm });

        const ctx = await upCommand({ appDev: true });

        expect(ctx.packageManager).toBe(pm);
      }
    });
  });
  ```

### Dependency Installation Tests

- [ ] **Installation execution**:
  ```typescript
  describe("dependency installation", () => {
    it("should not install in default mode", async () => {
      await upCommand({ appDev: false });

      expect(mockExec).not.toHaveBeenCalledWith(
        expect.stringMatching(/pnpm|npm|yarn|bun/)
      );
    });

    it("should install with selected package manager", async () => {
      mockPrompt.mockResolvedValue({ packageManager: "pnpm" });

      await upCommand({ appDev: true });

      expect(mockExec).toHaveBeenCalledWith(
        "pnpm",
        ["install"],
        expect.objectContaining({ cwd: expect.stringContaining("web") })
      );
    });

    it("should handle installation errors", async () => {
      mockPrompt.mockResolvedValue({ packageManager: "npm" });
      mockExec.mockRejectedValue(new Error("Install failed"));

      await expect(upCommand({ appDev: true })).rejects.toThrow("Install failed");
    });
  });
  ```

### Success Message Tests

- [ ] **Message content**:
  ```typescript
  describe("success messages", () => {
    it("should show web URL in default mode", async () => {
      const output = await captureOutput(() => upCommand({ appDev: false }));

      expect(output).toContain("http://localhost:3300");
      expect(output).toContain("Web:");
      expect(output).not.toContain("cd");
      expect(output).not.toContain("pnpm dev");
    });

    it("should show local dev instructions in app-dev mode", async () => {
      mockPrompt.mockResolvedValue({ packageManager: "pnpm" });

      const output = await captureOutput(() => upCommand({ appDev: true }));

      expect(output).toContain("To start the frontend:");
      expect(output).toContain("cd");
      expect(output).toContain("web");
      expect(output).toContain("pnpm dev");
      expect(output).not.toContain("Web: http://localhost:3300");
    });

    it("should use correct package manager command", async () => {
      const commands = {
        pnpm: "pnpm dev",
        npm: "npm run dev",
        yarn: "yarn dev",
        bun: "bun dev",
      };

      for (const [pm, cmd] of Object.entries(commands)) {
        mockPrompt.mockResolvedValue({ packageManager: pm });

        const output = await captureOutput(() => upCommand({ appDev: true }));

        expect(output).toContain(cmd);
      }
    });
  });
  ```

### Context Updates Tests

- [ ] **Context state**:
  ```typescript
  describe("context updates", () => {
    it("should set appDev flag in context", async () => {
      const ctx = await upCommand({ appDev: true });

      expect(ctx.appDev).toBe(true);
    });

    it("should store package manager in context", async () => {
      mockPrompt.mockResolvedValue({ packageManager: "yarn" });

      const ctx = await upCommand({ appDev: true });

      expect(ctx.packageManager).toBe("yarn");
    });
  });
  ```

### Integration Tests

- [ ] **Full workflow test**:
  ```typescript
  it("should complete full app-dev workflow", async () => {
    mockPrompt.mockResolvedValue({ packageManager: "pnpm" });

    // Run up command
    await upCommand({
      dir: "test-project",
      template: "basic",
      appDev: true,
    });

    // Assert sequence:
    // 1. Compose files loaded (only base)
    // 2. Docker services started (4 services)
    // 3. Package manager prompted
    // 4. Dependencies installed
    // 5. Success message with instructions

    expect(mockGetComposeFiles).toHaveReturnedWith(["compose.yaml"]);
    expect(mockDockerCompose).toHaveBeenCalled();
    expect(mockPrompt).toHaveBeenCalled();
    expect(mockExec).toHaveBeenCalledWith("pnpm", ["install"], expect.any(Object));
    expect(mockConsoleLog).toHaveBeenCalledWith(expect.stringContaining("pnpm dev"));
  });
  ```

### Mock Strategy

- [ ] Mock utilities:
  ```typescript
  const mockDockerCompose = jest.fn();
  const mockExec = jest.fn();
  const mockPrompt = jest.fn();
  const mockConsoleLog = jest.fn();

  beforeEach(() => {
    jest.resetAllMocks();
    // Setup default mock behavior
  });
  ```

### Coverage

- [ ] getComposeFiles() covered
- [ ] promptPackageManager() covered
- [ ] installFrontendDependencies() covered
- [ ] printSuccessMessage() variants covered
- [ ] Error paths covered

### Quality

- [ ] Tests are deterministic
- [ ] Tests run quickly (< 5 seconds)
- [ ] Tests are independent
- [ ] Clear test descriptions
- [ ] No real Docker calls
- [ ] No real npm/pnpm/yarn/bun calls

### Documentation

- [ ] Test file header comment
- [ ] Complex mocks documented
- [ ] Test helpers explained
