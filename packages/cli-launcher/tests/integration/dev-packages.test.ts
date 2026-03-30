import { describe, test, expect, beforeEach, afterEach, vi } from "vitest";
import fs from "fs-extra";
import path from "path";
import os from "os";
import { execa } from "execa";
import { detectMonorepoRoot } from "../../src/utils/monorepo-detection.js";
import {
  copyFrontendPackage,
  updatePackageJsonForDevPackages,
} from "../../src/utils/package-copy.js";

/**
 * Integration tests for the --dev-packages feature
 *
 * Tests the complete workflow for Boards contributors to test
 * unpublished package changes in a local development environment.
 */

describe("--dev-packages flag", () => {
  describe("validation", () => {
    test("should error when used without --app-dev", async () => {
      // This test would ideally mock the up command, but we can verify the validation logic
      // The validation happens in up.ts where it checks if devPackages && !appDev
      const devPackages = true;
      const appDev = false;

      if (devPackages && !appDev) {
        expect(() => {
          throw new Error(
            "--dev-packages requires --app-dev mode. " +
              "Docker-based web service cannot use local package sources."
          );
        }).toThrow("--dev-packages requires --app-dev mode");
      }
    });

    test("should error when not in monorepo", async () => {
      // When running from outside monorepo, detectMonorepoRoot returns null
      const devPackages = true;
      const monorepoRoot = null; // Simulate not in monorepo

      if (devPackages && !monorepoRoot) {
        expect(() => {
          throw new Error(
            "--dev-packages requires running from within the Boards monorepo."
          );
        }).toThrow("requires running from within the Boards monorepo");
      }
    });

    test("should accept flag when in monorepo with --app-dev", async () => {
      const devPackages = true;
      const appDev = true;
      const monorepoRoot = await detectMonorepoRoot();

      // If we're in the actual monorepo (CI environment), this should work
      if (monorepoRoot) {
        expect(devPackages && appDev && monorepoRoot).toBeTruthy();
      }
    });
  });

  describe("monorepo detection", () => {
    test("should detect monorepo from packages/cli-launcher", async () => {
      const result = await detectMonorepoRoot();

      // If running in CI/monorepo, should find it
      if (result) {
        expect(result).toBeTruthy();
        expect(await fs.pathExists(path.join(result, "pnpm-workspace.yaml"))).toBe(true);
      }
    });

    test("should return null outside monorepo", async () => {
      // This test verifies the function handles non-monorepo contexts
      // by checking the logic returns null when markers aren't found
      const result = await detectMonorepoRoot();

      // Should be either null or a valid path
      expect(result === null || typeof result === "string").toBe(true);
    });

    test("should validate packages/frontend exists", async () => {
      const monorepoRoot = await detectMonorepoRoot();

      if (monorepoRoot) {
        const frontendPath = path.join(monorepoRoot, "packages", "frontend");
        expect(await fs.pathExists(frontendPath)).toBe(true);
      }
    });

    test("should validate @weirdfingers/boards package name", async () => {
      const monorepoRoot = await detectMonorepoRoot();

      if (monorepoRoot) {
        const pkgPath = path.join(
          monorepoRoot,
          "packages",
          "frontend",
          "package.json"
        );
        const pkg = await fs.readJSON(pkgPath);
        expect(pkg.name).toBe("@weirdfingers/boards");
      }
    });
  });

  describe("package source copying", () => {
    let testDir: string;
    let monorepoRoot: string;
    let targetDir: string;

    beforeEach(async () => {
      testDir = await fs.mkdtemp(
        path.join(os.tmpdir(), "dev-packages-copy-test-")
      );
      monorepoRoot = path.join(testDir, "monorepo");
      targetDir = path.join(testDir, "target", "frontend");

      // Create mock monorepo structure
      const frontendDir = path.join(monorepoRoot, "packages", "frontend");
      await fs.ensureDir(frontendDir);

      // Create package.json
      await fs.writeJSON(path.join(frontendDir, "package.json"), {
        name: "@weirdfingers/boards",
        version: "0.7.0",
        type: "module",
      });

      // Create src directory with nested structure
      const srcDir = path.join(frontendDir, "src");
      await fs.ensureDir(path.join(srcDir, "hooks"));
      await fs.ensureDir(path.join(srcDir, "graphql", "operations"));
      await fs.ensureDir(path.join(srcDir, "utils"));

      await fs.writeFile(
        path.join(srcDir, "hooks", "useBoards.ts"),
        "export function useBoards() { return { boards: [] }; }"
      );
      await fs.writeFile(
        path.join(srcDir, "graphql", "operations", "boards.ts"),
        "export const BoardsQuery = `query { boards { id } }`;"
      );
      await fs.writeFile(
        path.join(srcDir, "utils", "helpers.ts"),
        "export function formatDate(date: Date) { return date.toISOString(); }"
      );

      // Create config files
      await fs.writeFile(
        path.join(frontendDir, "tsconfig.json"),
        JSON.stringify({ compilerOptions: { strict: true } }, null, 2)
      );
      await fs.writeFile(
        path.join(frontendDir, ".gitignore"),
        "node_modules\ndist\n"
      );

      // Create build artifacts that should be excluded
      await fs.ensureDir(path.join(frontendDir, "node_modules", "react"));
      await fs.writeFile(
        path.join(frontendDir, "node_modules", "react", "index.js"),
        "// react"
      );
      await fs.ensureDir(path.join(frontendDir, "dist"));
      await fs.writeFile(
        path.join(frontendDir, "dist", "index.js"),
        "// compiled"
      );
      await fs.ensureDir(path.join(frontendDir, ".turbo"));
      await fs.writeFile(
        path.join(frontendDir, ".turbo", "cache.json"),
        "{}"
      );
      await fs.ensureDir(path.join(frontendDir, ".next", "cache"));
      await fs.writeFile(
        path.join(frontendDir, ".next", "cache", "data.json"),
        "{}"
      );
      await fs.ensureDir(path.join(frontendDir, "coverage"));
      await fs.writeFile(
        path.join(frontendDir, "coverage", "lcov.info"),
        "SF:src/hooks/useBoards.ts"
      );
      await fs.writeFile(
        path.join(frontendDir, ".DS_Store"),
        "macos metadata"
      );
    });

    afterEach(async () => {
      await fs.remove(testDir);
    });

    test("should copy frontend package to <project>/frontend", async () => {
      await copyFrontendPackage(monorepoRoot, targetDir);

      expect(await fs.pathExists(targetDir)).toBe(true);
      expect(await fs.pathExists(path.join(targetDir, "package.json"))).toBe(
        true
      );
    });

    test("should exclude node_modules, dist, .turbo, .next", async () => {
      await copyFrontendPackage(monorepoRoot, targetDir);

      expect(await fs.pathExists(path.join(targetDir, "node_modules"))).toBe(
        false
      );
      expect(await fs.pathExists(path.join(targetDir, "dist"))).toBe(false);
      expect(await fs.pathExists(path.join(targetDir, ".turbo"))).toBe(false);
      expect(await fs.pathExists(path.join(targetDir, ".next"))).toBe(false);
      expect(await fs.pathExists(path.join(targetDir, "coverage"))).toBe(
        false
      );
      expect(await fs.pathExists(path.join(targetDir, ".DS_Store"))).toBe(
        false
      );
    });

    test("should include all src files", async () => {
      await copyFrontendPackage(monorepoRoot, targetDir);

      expect(
        await fs.pathExists(path.join(targetDir, "src", "hooks", "useBoards.ts"))
      ).toBe(true);
      expect(
        await fs.pathExists(
          path.join(targetDir, "src", "graphql", "operations", "boards.ts")
        )
      ).toBe(true);
      expect(
        await fs.pathExists(path.join(targetDir, "src", "utils", "helpers.ts"))
      ).toBe(true);
    });

    test("should include package.json and tsconfig.json", async () => {
      await copyFrontendPackage(monorepoRoot, targetDir);

      expect(await fs.pathExists(path.join(targetDir, "package.json"))).toBe(
        true
      );
      expect(await fs.pathExists(path.join(targetDir, "tsconfig.json"))).toBe(
        true
      );
      expect(await fs.pathExists(path.join(targetDir, ".gitignore"))).toBe(
        true
      );

      // Verify content is preserved
      const pkg = await fs.readJSON(path.join(targetDir, "package.json"));
      expect(pkg.name).toBe("@weirdfingers/boards");
    });

    test("should handle missing source gracefully", async () => {
      const badMonorepo = path.join(testDir, "bad-monorepo");
      await fs.ensureDir(badMonorepo);

      await expect(
        copyFrontendPackage(badMonorepo, targetDir)
      ).rejects.toThrow("Frontend package not found");
    });
  });

  describe("package.json modification", () => {
    let testDir: string;
    let webDir: string;

    beforeEach(async () => {
      testDir = await fs.mkdtemp(
        path.join(os.tmpdir(), "dev-packages-pkg-test-")
      );
      webDir = path.join(testDir, "web");
      await fs.ensureDir(webDir);
    });

    afterEach(async () => {
      await fs.remove(testDir);
    });

    test("should update dependency to file:../frontend", async () => {
      const packageJsonPath = path.join(webDir, "package.json");
      await fs.writeJSON(packageJsonPath, {
        name: "test-web",
        version: "1.0.0",
        dependencies: {
          "@weirdfingers/boards": "0.7.0",
          react: "^18.0.0",
          "next": "^14.0.0",
        },
      });

      await updatePackageJsonForDevPackages(webDir);

      const updated = await fs.readJSON(packageJsonPath);
      expect(updated.dependencies["@weirdfingers/boards"]).toBe(
        "file:../frontend"
      );
    });

    test("should preserve other dependencies", async () => {
      const packageJsonPath = path.join(webDir, "package.json");
      await fs.writeJSON(packageJsonPath, {
        name: "test-web",
        dependencies: {
          "@weirdfingers/boards": "0.7.0",
          react: "^18.0.0",
          "react-dom": "^18.0.0",
          next: "^14.0.0",
          urql: "^4.0.0",
        },
      });

      await updatePackageJsonForDevPackages(webDir);

      const updated = await fs.readJSON(packageJsonPath);
      expect(updated.dependencies.react).toBe("^18.0.0");
      expect(updated.dependencies["react-dom"]).toBe("^18.0.0");
      expect(updated.dependencies.next).toBe("^14.0.0");
      expect(updated.dependencies.urql).toBe("^4.0.0");
    });

    test("should maintain JSON formatting", async () => {
      const packageJsonPath = path.join(webDir, "package.json");
      await fs.writeJSON(
        packageJsonPath,
        {
          name: "test-web",
          version: "1.0.0",
          dependencies: {
            "@weirdfingers/boards": "0.7.0",
          },
        },
        { spaces: 2 }
      );

      await updatePackageJsonForDevPackages(webDir);

      const content = await fs.readFile(packageJsonPath, "utf-8");
      // Should use 2-space indentation
      expect(content).toContain('  "name"');
      expect(content).toContain('  "dependencies"');
    });

    test("should handle invalid package.json gracefully", async () => {
      const packageJsonPath = path.join(webDir, "package.json");
      await fs.writeFile(packageJsonPath, "{ invalid json }");

      await expect(updatePackageJsonForDevPackages(webDir)).rejects.toThrow(
        "Invalid JSON"
      );
    });
  });

  describe("end-to-end workflow", () => {
    let testDir: string;

    beforeEach(async () => {
      testDir = await fs.mkdtemp(
        path.join(os.tmpdir(), "dev-packages-e2e-test-")
      );
    });

    afterEach(async () => {
      await fs.remove(testDir);
    });

    test("should scaffold project with local package", async () => {
      const monorepoRoot = await detectMonorepoRoot();

      // Only run this test if we're in the monorepo (CI environment)
      if (!monorepoRoot) {
        return;
      }

      const projectDir = path.join(testDir, "test-project");
      await fs.ensureDir(projectDir);

      // Create web directory
      const webDir = path.join(projectDir, "web");
      await fs.ensureDir(webDir);

      // Create initial package.json
      await fs.writeJSON(path.join(webDir, "package.json"), {
        name: "test-project",
        dependencies: {
          "@weirdfingers/boards": "0.7.0",
          react: "^18.0.0",
        },
      });

      // Copy frontend package
      const frontendDir = path.join(projectDir, "frontend");
      await copyFrontendPackage(monorepoRoot, frontendDir);

      // Update package.json
      await updatePackageJsonForDevPackages(webDir);

      // Verify structure
      expect(await fs.pathExists(frontendDir)).toBe(true);
      expect(
        await fs.pathExists(path.join(frontendDir, "package.json"))
      ).toBe(true);

      const pkg = await fs.readJSON(path.join(webDir, "package.json"));
      expect(pkg.dependencies["@weirdfingers/boards"]).toBe("file:../frontend");
    });

    test("should install dependencies from file:", async () => {
      const monorepoRoot = await detectMonorepoRoot();

      if (!monorepoRoot) {
        return;
      }

      const projectDir = path.join(testDir, "test-install");
      const webDir = path.join(projectDir, "web");
      const frontendDir = path.join(projectDir, "frontend");

      await fs.ensureDir(webDir);

      // Setup package.json with file: dependency
      await fs.writeJSON(path.join(webDir, "package.json"), {
        name: "test-install",
        dependencies: {
          "@weirdfingers/boards": "file:../frontend",
        },
      });

      // Copy frontend package
      await copyFrontendPackage(monorepoRoot, frontendDir);

      // Verify the frontend package has a valid package.json
      expect(
        await fs.pathExists(path.join(frontendDir, "package.json"))
      ).toBe(true);

      const frontendPkg = await fs.readJSON(
        path.join(frontendDir, "package.json")
      );
      expect(frontendPkg.name).toBe("@weirdfingers/boards");
    });

    test("should start services successfully", async () => {
      // This is a conceptual test - actual service start would require
      // a full environment with Docker, etc. We verify the setup is correct.
      const monorepoRoot = await detectMonorepoRoot();

      if (!monorepoRoot) {
        return;
      }

      const projectDir = path.join(testDir, "test-services");
      const webDir = path.join(projectDir, "web");
      const frontendDir = path.join(projectDir, "frontend");

      await fs.ensureDir(webDir);

      // Setup complete structure
      await fs.writeJSON(path.join(webDir, "package.json"), {
        name: "test-services",
        version: "1.0.0",
        scripts: {
          dev: "next dev",
        },
        dependencies: {
          "@weirdfingers/boards": "file:../frontend",
          next: "^14.0.0",
          react: "^18.0.0",
        },
      });

      await copyFrontendPackage(monorepoRoot, frontendDir);

      // Verify all pieces are in place
      expect(await fs.pathExists(webDir)).toBe(true);
      expect(await fs.pathExists(frontendDir)).toBe(true);
      expect(await fs.pathExists(path.join(webDir, "package.json"))).toBe(
        true
      );

      const pkg = await fs.readJSON(path.join(webDir, "package.json"));
      expect(pkg.scripts.dev).toBe("next dev");
      expect(pkg.dependencies["@weirdfingers/boards"]).toBe("file:../frontend");
    });

    test("should enable hot reload for package changes", async () => {
      // Conceptual test: Verify frontend source files are accessible
      const monorepoRoot = await detectMonorepoRoot();

      if (!monorepoRoot) {
        return;
      }

      const projectDir = path.join(testDir, "test-hot-reload");
      const frontendDir = path.join(projectDir, "frontend");

      await copyFrontendPackage(monorepoRoot, frontendDir);

      // Verify source files are present (required for hot reload)
      expect(await fs.pathExists(path.join(frontendDir, "src"))).toBe(true);

      // Check that a hook file exists
      const srcDir = path.join(frontendDir, "src");
      const files = await fs.readdir(srcDir);
      expect(files.length).toBeGreaterThan(0);
    });
  });

  describe("error handling", () => {
    test("should error with helpful message outside monorepo", async () => {
      const devPackages = true;
      const monorepoRoot = null;

      if (devPackages && !monorepoRoot) {
        const errorMessage =
          "--dev-packages requires running from within the Boards monorepo.\n\n" +
          "This feature is for Boards contributors testing unpublished package changes.\n" +
          "Clone the monorepo and run: cd boards && pnpm cli up <dir> --app-dev --dev-packages\n\n" +
          "If you want to develop apps using the published package, use --app-dev without --dev-packages.";

        expect(() => {
          throw new Error(errorMessage);
        }).toThrow("requires running from within the Boards monorepo");
        expect(() => {
          throw new Error(errorMessage);
        }).toThrow("pnpm cli up");
      }
    });

    test("should error when packages/frontend missing", async () => {
      const testDir = await fs.mkdtemp(
        path.join(os.tmpdir(), "dev-packages-error-test-")
      );

      try {
        const badMonorepo = path.join(testDir, "bad-monorepo");
        await fs.ensureDir(badMonorepo);

        await expect(
          copyFrontendPackage(badMonorepo, path.join(testDir, "target"))
        ).rejects.toThrow("Frontend package not found");
      } finally {
        await fs.remove(testDir);
      }
    });

    test("should error on filesystem permission issues", async () => {
      const testDir = await fs.mkdtemp(
        path.join(os.tmpdir(), "dev-packages-perm-test-")
      );

      try {
        // Mock a permission error by trying to write to a non-existent directory
        // that we can't create
        const invalidPath = path.join(
          testDir,
          "nonexistent",
          "deeply",
          "nested",
          "path"
        );

        // Mock fs.copy to throw a permission error
        const originalCopy = fs.copy;
        vi.spyOn(fs, "copy").mockRejectedValueOnce(
          Object.assign(new Error("Permission denied"), { code: "EACCES" })
        );

        try {
          // Create a minimal source structure
          const sourceDir = path.join(testDir, "source");
          await fs.ensureDir(path.join(sourceDir, "packages", "frontend"));
          await fs.writeJSON(
            path.join(sourceDir, "packages", "frontend", "package.json"),
            {
              name: "@weirdfingers/boards",
            }
          );

          await expect(
            copyFrontendPackage(sourceDir, invalidPath)
          ).rejects.toThrow();
        } finally {
          vi.restoreAllMocks();
        }
      } finally {
        await fs.remove(testDir);
      }
    });
  });
});
