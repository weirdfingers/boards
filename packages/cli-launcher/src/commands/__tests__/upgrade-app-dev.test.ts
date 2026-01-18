import { describe, test, expect, beforeEach, afterEach, vi } from "vitest";
import fs from "fs-extra";
import path from "path";
import os from "os";
import { upgradeAppDevMode } from "../upgrade-app-dev.js";
import { execa } from "execa";

// Mock execa to avoid running real Docker commands
vi.mock("execa");

describe("App-Dev Mode Upgrade", () => {
  let testDir: string;
  let projectDir: string;

  beforeEach(async () => {
    // Create a temporary test directory
    testDir = await fs.mkdtemp(
      path.join(os.tmpdir(), "upgrade-app-dev-test-")
    );
    projectDir = path.join(testDir, "test-project");

    // Create test project structure for app-dev mode
    await createTestProject(projectDir, "0.7.0");

    // Mock execa to simulate successful Docker commands
    // @ts-expect-error - Mocking execa with simplified return type
    vi.mocked(execa).mockImplementation(async (cmd: string | URL, args?: any) => {
      // For docker compose ps, return healthy services (no web)
      if (
        Array.isArray(args) &&
        args.includes("ps") &&
        args.includes("--format")
      ) {
        return {
          stdout: [
            '{"Service":"db","Health":"healthy","State":"running"}',
            '{"Service":"cache","Health":"healthy","State":"running"}',
            '{"Service":"api","Health":"healthy","State":"running"}',
            '{"Service":"worker","Health":"healthy","State":"running"}',
          ].join("\n"),
          stderr: "",
        };
      }
      // For other commands, return empty success
      return { stdout: "", stderr: "" };
    });
  });

  afterEach(async () => {
    // Clean up test directory
    await fs.remove(testDir);
    vi.clearAllMocks();
  });

  test("upgrades backend successfully", async () => {
    await upgradeAppDevMode(projectDir, "0.7.0", "0.8.0");

    // Verify docker/.env has new version
    const envContent = await fs.readFile(
      path.join(projectDir, "docker", ".env"),
      "utf-8"
    );
    expect(envContent).toContain("BACKEND_VERSION=0.8.0");

    // Verify web/package.json is unchanged (user must update manually)
    const packageJson = await fs.readJson(
      path.join(projectDir, "web", "package.json")
    );
    expect(packageJson.dependencies["@weirdfingers/boards"]).toBe("0.7.0");

    // Verify Docker commands were called in correct order
    const execaMock = vi.mocked(execa);
    const calls = execaMock.mock.calls;

    // Check that down was called
    expect(calls.some(([cmd, args]) =>
      cmd === "docker" && Array.isArray(args) && args.includes("down")
    )).toBe(true);

    // Check that pull was called for backend services only
    expect(calls.some(([cmd, args]) =>
      cmd === "docker" &&
      Array.isArray(args) &&
      args.includes("pull") &&
      args.includes("api") &&
      args.includes("worker")
    )).toBe(true);

    // Check that up was called with backend services only (no web)
    expect(calls.some(([cmd, args]) =>
      cmd === "docker" &&
      Array.isArray(args) &&
      args.includes("up") &&
      args.includes("-d") &&
      args.includes("db") &&
      args.includes("cache") &&
      args.includes("api") &&
      args.includes("worker") &&
      !args.includes("web")
    )).toBe(true);

    // Check that ps (health check) was called
    expect(calls.some(([cmd, args]) =>
      cmd === "docker" && Array.isArray(args) && args.includes("ps")
    )).toBe(true);
  });

  test("does not modify web/package.json", async () => {
    const originalPackageJson = await fs.readJson(
      path.join(projectDir, "web", "package.json")
    );

    await upgradeAppDevMode(projectDir, "0.7.0", "0.8.0");

    const packageJson = await fs.readJson(
      path.join(projectDir, "web", "package.json")
    );

    // Frontend version should remain unchanged
    expect(packageJson).toEqual(originalPackageJson);
    expect(packageJson.dependencies["@weirdfingers/boards"]).toBe("0.7.0");
  });

  test("detects package manager and prints correct update command (pnpm)", async () => {
    // Create pnpm-lock.yaml to indicate pnpm is used
    await fs.writeFile(
      path.join(projectDir, "web", "pnpm-lock.yaml"),
      "lockfileVersion: '6.0'"
    );

    // Capture console output
    const consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    await upgradeAppDevMode(projectDir, "0.7.0", "0.8.0");

    // Verify pnpm update command was printed
    const logOutput = consoleLogSpy.mock.calls
      .map((call) => call.join(" "))
      .join("\n");

    expect(logOutput).toContain("pnpm update @weirdfingers/boards@0.8.0");
    expect(logOutput).toContain("pnpm dev");

    consoleLogSpy.mockRestore();
  });

  test("detects package manager and prints correct update command (npm)", async () => {
    // Create package-lock.json to indicate npm is used
    await fs.writeJson(
      path.join(projectDir, "web", "package-lock.json"),
      { lockfileVersion: 3 }
    );

    // Capture console output
    const consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    await upgradeAppDevMode(projectDir, "0.7.0", "0.8.0");

    // Verify npm install command was printed
    const logOutput = consoleLogSpy.mock.calls
      .map((call) => call.join(" "))
      .join("\n");

    expect(logOutput).toContain("npm install @weirdfingers/boards@0.8.0");
    expect(logOutput).toContain("npm dev");

    consoleLogSpy.mockRestore();
  });

  test("detects package manager and prints correct update command (yarn)", async () => {
    // Create yarn.lock to indicate yarn is used
    await fs.writeFile(
      path.join(projectDir, "web", "yarn.lock"),
      "# This is a yarn lockfile"
    );

    // Capture console output
    const consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    await upgradeAppDevMode(projectDir, "0.7.0", "0.8.0");

    // Verify yarn upgrade command was printed
    const logOutput = consoleLogSpy.mock.calls
      .map((call) => call.join(" "))
      .join("\n");

    expect(logOutput).toContain("yarn upgrade @weirdfingers/boards@0.8.0");
    expect(logOutput).toContain("yarn dev");

    consoleLogSpy.mockRestore();
  });

  test("detects package manager and prints correct update command (bun)", async () => {
    // Create bun.lockb to indicate bun is used
    await fs.writeFile(
      path.join(projectDir, "web", "bun.lockb"),
      ""
    );

    // Capture console output
    const consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    await upgradeAppDevMode(projectDir, "0.7.0", "0.8.0");

    // Verify bun update command was printed
    const logOutput = consoleLogSpy.mock.calls
      .map((call) => call.join(" "))
      .join("\n");

    expect(logOutput).toContain("bun update @weirdfingers/boards@0.8.0");
    expect(logOutput).toContain("bun dev");

    consoleLogSpy.mockRestore();
  });

  test("warns about uncommitted changes in git repo", async () => {
    // Mock git status to return uncommitted changes
    // @ts-expect-error - Mocking execa with simplified return type
    vi.mocked(execa).mockImplementation(async (cmd: string | URL, args?: any) => {
      // Mock git status --porcelain to return uncommitted changes
      if (cmd === "git" && Array.isArray(args) && args.includes("status")) {
        return {
          stdout: " M web/src/App.tsx\n ?? web/src/newfile.ts",
          stderr: "",
        };
      }
      // For docker compose ps, return healthy services
      if (
        Array.isArray(args) &&
        args.includes("ps") &&
        args.includes("--format")
      ) {
        return {
          stdout: [
            '{"Service":"db","Health":"healthy","State":"running"}',
            '{"Service":"cache","Health":"healthy","State":"running"}',
            '{"Service":"api","Health":"healthy","State":"running"}',
            '{"Service":"worker","Health":"healthy","State":"running"}',
          ].join("\n"),
          stderr: "",
        };
      }
      return { stdout: "", stderr: "" };
    });

    // Capture console output
    const consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    await upgradeAppDevMode(projectDir, "0.7.0", "0.8.0");

    // Verify warning about uncommitted changes was printed
    const logOutput = consoleLogSpy.mock.calls
      .map((call) => call.join(" "))
      .join("\n");

    expect(logOutput).toContain("You have uncommitted changes in web/");
    expect(logOutput).toContain("Consider committing before updating dependencies");

    consoleLogSpy.mockRestore();
  });

  test("preserves BACKEND_VERSION format in docker/.env", async () => {
    await upgradeAppDevMode(projectDir, "0.7.0", "0.8.0");

    const envContent = await fs.readFile(
      path.join(projectDir, "docker", ".env"),
      "utf-8"
    );

    // Check that only BACKEND_VERSION line was updated
    expect(envContent).toContain("BACKEND_VERSION=0.8.0");
    expect(envContent).toContain("PROJECT_NAME=test-project");
    expect(envContent).toContain("API_PORT=8000");

    // Ensure format is preserved (BACKEND_VERSION= with no extra spaces)
    const lines = envContent.split("\n");
    const backendVersionLine = lines.find((line) =>
      line.startsWith("BACKEND_VERSION=")
    );
    expect(backendVersionLine).toBe("BACKEND_VERSION=0.8.0");
  });

  test("throws error and provides rollback instructions on failure", async () => {
    // Mock execa to fail on pull command
    // @ts-expect-error - Mocking execa with simplified return type
    vi.mocked(execa).mockImplementation(async (cmd: string | URL, args?: any) => {
      if (
        Array.isArray(args) &&
        args.includes("pull")
      ) {
        throw new Error("Docker pull failed");
      }
      return { stdout: "", stderr: "" };
    });

    // Capture console output
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    await expect(
      upgradeAppDevMode(projectDir, "0.7.0", "0.8.0")
    ).rejects.toThrow("Docker pull failed");

    // Verify rollback instructions were printed
    const errorOutput = consoleErrorSpy.mock.calls
      .map((call) => call.join(" "))
      .join("\n");
    const logOutput = consoleLogSpy.mock.calls
      .map((call) => call.join(" "))
      .join("\n");

    expect(errorOutput).toContain("Upgrade failed");
    expect(logOutput).toContain("To rollback:");
    expect(logOutput).toContain("BACKEND_VERSION=0.7.0");
    expect(logOutput).toContain("docker compose --env-file docker/.env");

    consoleErrorSpy.mockRestore();
    consoleLogSpy.mockRestore();
  });

  test("prints release notes link", async () => {
    // Capture console output
    const consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    await upgradeAppDevMode(projectDir, "0.7.0", "0.8.0");

    // Verify release notes link was printed
    const logOutput = consoleLogSpy.mock.calls
      .map((call) => call.join(" "))
      .join("\n");

    expect(logOutput).toContain("https://github.com/weirdfingers/boards/releases/tag/v0.8.0");
    expect(logOutput).toContain("Check for breaking changes");

    consoleLogSpy.mockRestore();
  });
});

/**
 * Create a test project for app-dev mode with specified version
 */
async function createTestProject(
  projectDir: string,
  version: string
): Promise<void> {
  // Create directories
  await fs.ensureDir(path.join(projectDir, "web"));
  await fs.ensureDir(path.join(projectDir, "docker"));

  // Create web/package.json
  await fs.writeJson(
    path.join(projectDir, "web", "package.json"),
    {
      name: "test-app",
      version: "1.0.0",
      dependencies: {
        "@weirdfingers/boards": version,
        react: "^18.2.0",
        next: "14.0.0",
      },
    },
    { spaces: 2 }
  );

  // Create docker/.env
  await fs.writeFile(
    path.join(projectDir, "docker", ".env"),
    `# Test environment file
PROJECT_NAME=test-project
BACKEND_VERSION=${version}
API_PORT=8000
`
  );
}
