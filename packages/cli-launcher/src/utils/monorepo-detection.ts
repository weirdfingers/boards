/**
 * Monorepo detection utility
 *
 * Detects if the CLI is running from within the Boards monorepo.
 * This is required for the --dev-packages feature.
 */

import fs from "fs-extra";
import path from "path";
import { fileURLToPath } from "url";

/**
 * Detect if CLI is running from within the Boards monorepo.
 * Returns monorepo root path if found, null otherwise.
 *
 * Walks up the directory tree from CLI package location looking for:
 * 1. pnpm-workspace.yaml (monorepo marker)
 * 2. packages/frontend/package.json (Boards structure)
 * 3. Package name === '@weirdfingers/boards' (correct repo)
 *
 * @returns Absolute path to monorepo root, or null if not in monorepo
 */
export async function detectMonorepoRoot(): Promise<string | null> {
  // Start from the CLI package location
  // __dirname is not available in ESM, so we need to derive it from import.meta.url
  const currentFile = fileURLToPath(import.meta.url);
  const cliPackageDir = path.resolve(path.dirname(currentFile), "../..");

  let currentDir = cliPackageDir;
  const maxDepth = 5;

  for (let depth = 0; depth < maxDepth; depth++) {
    try {
      // Check for pnpm-workspace.yaml
      const workspaceFile = path.join(currentDir, "pnpm-workspace.yaml");
      if (!(await fs.pathExists(workspaceFile))) {
        // Move up one level
        const parentDir = path.dirname(currentDir);
        if (parentDir === currentDir) {
          // Reached filesystem root
          break;
        }
        currentDir = parentDir;
        continue;
      }

      // Found pnpm-workspace.yaml - validate Boards structure
      const frontendPackageJson = path.join(
        currentDir,
        "packages/frontend/package.json"
      );

      if (!(await fs.pathExists(frontendPackageJson))) {
        // Not the Boards monorepo
        const parentDir = path.dirname(currentDir);
        if (parentDir === currentDir) {
          break;
        }
        currentDir = parentDir;
        continue;
      }

      // Validate package name
      const packageData = await fs.readJSON(frontendPackageJson);
      if (packageData.name !== "@weirdfingers/boards") {
        // Wrong monorepo
        const parentDir = path.dirname(currentDir);
        if (parentDir === currentDir) {
          break;
        }
        currentDir = parentDir;
        continue;
      }

      // All checks passed - this is the Boards monorepo root
      return currentDir;
    } catch (error) {
      // Handle filesystem errors gracefully
      // Continue searching up the tree
      const parentDir = path.dirname(currentDir);
      if (parentDir === currentDir) {
        // Reached filesystem root
        break;
      }
      currentDir = parentDir;
      continue;
    }
  }

  // No monorepo found
  return null;
}
