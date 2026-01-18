/**
 * Package source copying utilities for --dev-packages mode
 *
 * Copies @weirdfingers/boards package source from monorepo to scaffolded project
 * and configures file: dependency for local development.
 */

import fs from "fs-extra";
import path from "path";

/**
 * Determine if a file should be copied based on exclusion rules.
 * Excludes build artifacts, dependencies, and system files.
 *
 * @param filePath - Absolute file path to check
 * @returns true if file should be copied, false if excluded
 */
function shouldCopyFile(filePath: string): boolean {
  const excluded = [
    "node_modules",
    "dist",
    ".turbo",
    ".next",
    "coverage",
    ".DS_Store",
  ];

  return !excluded.some((ex) => filePath.includes(ex));
}

/**
 * Copy @weirdfingers/boards package source from monorepo to target directory.
 * Excludes build artifacts and dependencies.
 *
 * @param monorepoRoot - Root of Boards monorepo
 * @param targetDir - Destination directory for package source
 */
export async function copyFrontendPackage(
  monorepoRoot: string,
  targetDir: string
): Promise<void> {
  const sourceFrontendDir = path.join(monorepoRoot, "packages/frontend");

  // Validate source directory exists
  if (!(await fs.pathExists(sourceFrontendDir))) {
    throw new Error(
      `Frontend package not found at: ${sourceFrontendDir}\n` +
        "The monorepo structure may be corrupted."
    );
  }

  // Ensure target directory exists
  await fs.ensureDir(targetDir);

  try {
    // Copy with filter to exclude build artifacts and dependencies
    await fs.copy(sourceFrontendDir, targetDir, {
      filter: (src) => shouldCopyFile(src),
      overwrite: true,
      errorOnExist: false,
    });
  } catch (error) {
    // Clean up partial copy on failure
    try {
      await fs.remove(targetDir);
    } catch {
      // Ignore cleanup errors
    }

    const errorMessage =
      error instanceof Error ? error.message : String(error);

    if (errorMessage.includes("EACCES") || errorMessage.includes("EPERM")) {
      throw new Error(
        `Permission denied while copying package source.\n` +
          `Check file permissions for: ${sourceFrontendDir}\n` +
          `Error: ${errorMessage}`
      );
    }

    throw new Error(
      `Failed to copy frontend package from monorepo.\n` +
        `Source: ${sourceFrontendDir}\n` +
        `Target: ${targetDir}\n` +
        `Error: ${errorMessage}`
    );
  }
}

/**
 * Modify web/package.json to use file:../frontend dependency.
 *
 * @param webDir - Path to web directory
 */
export async function updatePackageJsonForDevPackages(
  webDir: string
): Promise<void> {
  const packageJsonPath = path.join(webDir, "package.json");

  // Validate package.json exists
  if (!(await fs.pathExists(packageJsonPath))) {
    throw new Error(
      `package.json not found at: ${packageJsonPath}\n` +
        "The web directory may not be properly scaffolded."
    );
  }

  try {
    // Read existing package.json
    const packageData = await fs.readJSON(packageJsonPath);

    // Update @weirdfingers/boards dependency to use file: protocol
    if (packageData.dependencies && packageData.dependencies["@weirdfingers/boards"]) {
      packageData.dependencies["@weirdfingers/boards"] = "file:../frontend";
    } else if (packageData.devDependencies && packageData.devDependencies["@weirdfingers/boards"]) {
      packageData.devDependencies["@weirdfingers/boards"] = "file:../frontend";
    } else {
      throw new Error(
        `@weirdfingers/boards dependency not found in ${packageJsonPath}\n` +
          "The package may not be installed or the package.json structure is unexpected."
      );
    }

    // Write back with proper formatting (2-space indent)
    await fs.writeJSON(packageJsonPath, packageData, { spaces: 2 });
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : String(error);

    if (errorMessage.includes("EACCES") || errorMessage.includes("EPERM")) {
      throw new Error(
        `Permission denied while updating package.json.\n` +
          `Check file permissions for: ${packageJsonPath}\n` +
          `Error: ${errorMessage}`
      );
    }

    if (errorMessage.includes("JSON")) {
      throw new Error(
        `Invalid JSON in package.json: ${packageJsonPath}\n` +
          `Error: ${errorMessage}`
      );
    }

    // Re-throw if already a formatted error from this function
    if (errorMessage.includes("@weirdfingers/boards dependency not found")) {
      throw error;
    }

    throw new Error(
      `Failed to update package.json for dev-packages mode.\n` +
        `File: ${packageJsonPath}\n` +
        `Error: ${errorMessage}`
    );
  }
}
