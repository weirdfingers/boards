import { describe, test, expect, beforeEach, afterEach } from "vitest";
import fs from "fs-extra";
import path from "path";
import os from "os";
import {
  copyFrontendPackage,
  updatePackageJsonForDevPackages,
} from "../package-copy.js";

describe("copyFrontendPackage", () => {
  let testDir: string;
  let monorepoRoot: string;
  let targetDir: string;

  beforeEach(async () => {
    // Create a temporary test directory
    testDir = await fs.mkdtemp(path.join(os.tmpdir(), "package-copy-test-"));
    monorepoRoot = path.join(testDir, "monorepo");
    targetDir = path.join(testDir, "target");

    // Create mock monorepo structure
    const frontendDir = path.join(monorepoRoot, "packages", "frontend");
    await fs.ensureDir(frontendDir);

    // Create package.json
    await fs.writeJSON(path.join(frontendDir, "package.json"), {
      name: "@weirdfingers/boards",
      version: "0.7.0",
    });

    // Create src directory with some files
    const srcDir = path.join(frontendDir, "src");
    await fs.ensureDir(path.join(srcDir, "hooks"));
    await fs.ensureDir(path.join(srcDir, "graphql"));
    await fs.writeFile(
      path.join(srcDir, "hooks", "useBoards.ts"),
      "export function useBoards() {}"
    );
    await fs.writeFile(
      path.join(srcDir, "graphql", "operations.ts"),
      "export const BoardsQuery = {}"
    );

    // Create config files
    await fs.writeFile(
      path.join(frontendDir, "tsconfig.json"),
      JSON.stringify({ compilerOptions: {} })
    );

    // Create build artifacts that should be excluded
    await fs.ensureDir(path.join(frontendDir, "node_modules", "lodash"));
    await fs.writeFile(
      path.join(frontendDir, "node_modules", "lodash", "index.js"),
      "// lodash"
    );
    await fs.ensureDir(path.join(frontendDir, "dist"));
    await fs.writeFile(
      path.join(frontendDir, "dist", "index.js"),
      "// compiled"
    );
    await fs.ensureDir(path.join(frontendDir, ".turbo"));
    await fs.writeFile(path.join(frontendDir, ".turbo", "cache"), "cache");
    await fs.ensureDir(path.join(frontendDir, ".next"));
    await fs.writeFile(path.join(frontendDir, ".next", "build"), "build");
    await fs.ensureDir(path.join(frontendDir, "coverage"));
    await fs.writeFile(
      path.join(frontendDir, "coverage", "lcov.info"),
      "coverage"
    );
    await fs.writeFile(path.join(frontendDir, ".DS_Store"), "macos metadata");
  });

  afterEach(async () => {
    // Clean up test directory
    await fs.remove(testDir);
  });

  test("should copy all source files", async () => {
    await copyFrontendPackage(monorepoRoot, targetDir);

    // Verify key files exist
    expect(await fs.pathExists(path.join(targetDir, "package.json"))).toBe(
      true
    );
    expect(await fs.pathExists(path.join(targetDir, "src", "hooks"))).toBe(
      true
    );
    expect(
      await fs.pathExists(path.join(targetDir, "src", "hooks", "useBoards.ts"))
    ).toBe(true);
    expect(await fs.pathExists(path.join(targetDir, "src", "graphql"))).toBe(
      true
    );
    expect(
      await fs.pathExists(
        path.join(targetDir, "src", "graphql", "operations.ts")
      )
    ).toBe(true);
    expect(await fs.pathExists(path.join(targetDir, "tsconfig.json"))).toBe(
      true
    );
  });

  test("should exclude build artifacts", async () => {
    await copyFrontendPackage(monorepoRoot, targetDir);

    // Verify exclusions
    expect(await fs.pathExists(path.join(targetDir, "node_modules"))).toBe(
      false
    );
    expect(await fs.pathExists(path.join(targetDir, "dist"))).toBe(false);
    expect(await fs.pathExists(path.join(targetDir, ".turbo"))).toBe(false);
    expect(await fs.pathExists(path.join(targetDir, ".next"))).toBe(false);
    expect(await fs.pathExists(path.join(targetDir, "coverage"))).toBe(false);
    expect(await fs.pathExists(path.join(targetDir, ".DS_Store"))).toBe(false);
  });

  test("should throw error if source directory does not exist", async () => {
    const nonExistentMonorepo = path.join(testDir, "nonexistent");

    await expect(
      copyFrontendPackage(nonExistentMonorepo, targetDir)
    ).rejects.toThrow("Frontend package not found");
  });

  test("should provide clear error on source directory missing", async () => {
    // Test error message when frontend package doesn't exist
    const badMonorepo = path.join(testDir, "bad-monorepo");
    await fs.ensureDir(badMonorepo);

    await expect(
      copyFrontendPackage(badMonorepo, targetDir)
    ).rejects.toThrow("Frontend package not found");
  });

  test("should overwrite existing files", async () => {
    // Create target with old content
    await fs.ensureDir(targetDir);
    await fs.writeFile(
      path.join(targetDir, "package.json"),
      JSON.stringify({ name: "old" })
    );

    await copyFrontendPackage(monorepoRoot, targetDir);

    // Verify new content
    const packageJson = await fs.readJSON(path.join(targetDir, "package.json"));
    expect(packageJson.name).toBe("@weirdfingers/boards");
  });
});

describe("updatePackageJsonForDevPackages", () => {
  let testDir: string;
  let webDir: string;

  beforeEach(async () => {
    // Create a temporary test directory
    testDir = await fs.mkdtemp(
      path.join(os.tmpdir(), "package-json-update-test-")
    );
    webDir = path.join(testDir, "web");
    await fs.ensureDir(webDir);
  });

  afterEach(async () => {
    // Clean up test directory
    await fs.remove(testDir);
  });

  test("should modify dependency to file:../frontend", async () => {
    const packageJsonPath = path.join(webDir, "package.json");
    await fs.writeJSON(packageJsonPath, {
      name: "test-web",
      dependencies: {
        "@weirdfingers/boards": "0.7.0",
        react: "^18.0.0",
      },
    });

    await updatePackageJsonForDevPackages(webDir);

    const updated = await fs.readJSON(packageJsonPath);
    expect(updated.dependencies["@weirdfingers/boards"]).toBe("file:../frontend");
    expect(updated.dependencies.react).toBe("^18.0.0");
  });

  test("should handle devDependencies", async () => {
    const packageJsonPath = path.join(webDir, "package.json");
    await fs.writeJSON(packageJsonPath, {
      name: "test-web",
      devDependencies: {
        "@weirdfingers/boards": "0.7.0",
      },
    });

    await updatePackageJsonForDevPackages(webDir);

    const updated = await fs.readJSON(packageJsonPath);
    expect(updated.devDependencies["@weirdfingers/boards"]).toBe(
      "file:../frontend"
    );
  });

  test("should preserve all other fields", async () => {
    const packageJsonPath = path.join(webDir, "package.json");
    await fs.writeJSON(packageJsonPath, {
      name: "test-web",
      version: "1.0.0",
      description: "Test web app",
      scripts: {
        dev: "next dev",
      },
      dependencies: {
        "@weirdfingers/boards": "0.7.0",
        react: "^18.0.0",
      },
    });

    await updatePackageJsonForDevPackages(webDir);

    const updated = await fs.readJSON(packageJsonPath);
    expect(updated.name).toBe("test-web");
    expect(updated.version).toBe("1.0.0");
    expect(updated.description).toBe("Test web app");
    expect(updated.scripts.dev).toBe("next dev");
    expect(updated.dependencies.react).toBe("^18.0.0");
  });

  test("should format with 2-space indent", async () => {
    const packageJsonPath = path.join(webDir, "package.json");
    await fs.writeJSON(packageJsonPath, {
      name: "test-web",
      dependencies: {
        "@weirdfingers/boards": "0.7.0",
      },
    });

    await updatePackageJsonForDevPackages(webDir);

    const content = await fs.readFile(packageJsonPath, "utf-8");
    // Check that it uses 2-space indentation
    expect(content).toContain('  "name"');
    expect(content).toContain('  "dependencies"');
  });

  test("should throw error if package.json does not exist", async () => {
    await expect(updatePackageJsonForDevPackages(webDir)).rejects.toThrow(
      "package.json not found"
    );
  });

  test("should throw error if @weirdfingers/boards is not in dependencies", async () => {
    const packageJsonPath = path.join(webDir, "package.json");
    await fs.writeJSON(packageJsonPath, {
      name: "test-web",
      dependencies: {
        react: "^18.0.0",
      },
    });

    await expect(updatePackageJsonForDevPackages(webDir)).rejects.toThrow(
      "@weirdfingers/boards dependency not found"
    );
  });

  test("should handle invalid JSON gracefully", async () => {
    const packageJsonPath = path.join(webDir, "package.json");
    await fs.writeFile(packageJsonPath, "{ invalid json");

    await expect(updatePackageJsonForDevPackages(webDir)).rejects.toThrow(
      "Invalid JSON"
    );
  });
});
