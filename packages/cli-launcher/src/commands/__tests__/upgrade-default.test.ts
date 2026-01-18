import { describe, test, expect, beforeEach, afterEach, vi } from "vitest";
import fs from "fs-extra";
import path from "path";
import os from "os";
import { upgradeDefaultMode } from "../upgrade-default.js";
import { execa } from "execa";

// Mock execa to avoid running real Docker commands
vi.mock("execa");

describe("Default Mode Upgrade", () => {
  let testDir: string;
  let projectDir: string;

  beforeEach(async () => {
    // Create a temporary test directory
    testDir = await fs.mkdtemp(
      path.join(os.tmpdir(), "upgrade-default-test-")
    );
    projectDir = path.join(testDir, "test-project");

    // Create test project structure
    await createTestProject(projectDir, "0.7.0");

    // Mock execa to simulate successful Docker commands
    // @ts-expect-error - Mocking execa with simplified return type
    vi.mocked(execa).mockImplementation(async (cmd: string | URL, args?: any) => {
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
            '{"Service":"web","Health":"healthy","State":"running"}',
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

  test("upgrades successfully from 0.7.0 to 0.8.0", async () => {
    await upgradeDefaultMode(projectDir, "0.7.0", "0.8.0");

    // Verify web/package.json has new version
    const packageJson = await fs.readJson(
      path.join(projectDir, "web", "package.json")
    );
    expect(packageJson.dependencies["@weirdfingers/boards"]).toBe("0.8.0");

    // Verify docker/.env has new version
    const envContent = await fs.readFile(
      path.join(projectDir, "docker", ".env"),
      "utf-8"
    );
    expect(envContent).toContain("BACKEND_VERSION=0.8.0");

    // Verify Docker commands were called in correct order
    const execaMock = vi.mocked(execa);
    const calls = execaMock.mock.calls;

    // Check that down was called
    expect(calls.some(([cmd, args]) =>
      cmd === "docker" && Array.isArray(args) && args.includes("down")
    )).toBe(true);

    // Check that pull was called
    expect(calls.some(([cmd, args]) =>
      cmd === "docker" && Array.isArray(args) && args.includes("pull")
    )).toBe(true);

    // Check that build was called
    expect(calls.some(([cmd, args]) =>
      cmd === "docker" && Array.isArray(args) && args.includes("build")
    )).toBe(true);

    // Check that up was called
    expect(calls.some(([cmd, args]) =>
      cmd === "docker" && Array.isArray(args) && args.includes("up") && args.includes("-d")
    )).toBe(true);

    // Check that ps (health check) was called
    expect(calls.some(([cmd, args]) =>
      cmd === "docker" && Array.isArray(args) && args.includes("ps")
    )).toBe(true);
  });

  test("updates only @weirdfingers/boards dependency", async () => {
    await upgradeDefaultMode(projectDir, "0.7.0", "0.8.0");

    const packageJson = await fs.readJson(
      path.join(projectDir, "web", "package.json")
    );

    // Check that @weirdfingers/boards was updated
    expect(packageJson.dependencies["@weirdfingers/boards"]).toBe("0.8.0");

    // Check that other dependencies remain unchanged
    expect(packageJson.dependencies["react"]).toBe("^18.2.0");
    expect(packageJson.dependencies["next"]).toBe("14.0.0");
  });

  test("preserves BACKEND_VERSION format in docker/.env", async () => {
    await upgradeDefaultMode(projectDir, "0.7.0", "0.8.0");

    const envContent = await fs.readFile(
      path.join(projectDir, "docker", ".env"),
      "utf-8"
    );

    // Check that only BACKEND_VERSION line was updated
    expect(envContent).toContain("BACKEND_VERSION=0.8.0");
    expect(envContent).toContain("PROJECT_NAME=test-project");
    expect(envContent).toContain("WEB_PORT=3000");

    // Ensure format is preserved (BACKEND_VERSION= with no extra spaces)
    const lines = envContent.split("\n");
    const backendVersionLine = lines.find((line) =>
      line.startsWith("BACKEND_VERSION=")
    );
    expect(backendVersionLine).toBe("BACKEND_VERSION=0.8.0");
  });

  test("throws error and provides rollback instructions on failure", async () => {
    // Mock execa to fail on build command
    // @ts-expect-error - Mocking execa with simplified return type
    vi.mocked(execa).mockImplementation(async (cmd: string | URL, args?: any) => {
      if (
        Array.isArray(args) &&
        args.includes("build")
      ) {
        throw new Error("Docker build failed");
      }
      return { stdout: "", stderr: "" };
    });

    // Capture console output
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    await expect(
      upgradeDefaultMode(projectDir, "0.7.0", "0.8.0")
    ).rejects.toThrow("Docker build failed");

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

    consoleErrorSpy.mockRestore();
    consoleLogSpy.mockRestore();
  });
});

/**
 * Create a test project with specified version
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
WEB_PORT=3000
API_PORT=8000
`
  );
}
