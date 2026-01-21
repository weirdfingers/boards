/**
 * Root Package.json Utilities
 *
 * Provides utilities for generating and managing the root package.json
 * that provides ergonomic CLI commands for Baseboards projects.
 */

import fs from "fs-extra";
import path from "path";
import chalk from "chalk";
import { execa } from "execa";
import type { PackageManager } from "../utils.js";

/**
 * Root package.json structure for Baseboards projects.
 * Provides npm scripts for common CLI commands.
 */
interface RootPackageJson {
  name: string;
  private: boolean;
  description: string;
  scripts: Record<string, string>;
  devDependencies: Record<string, string>;
}

/**
 * Generate the root package.json content for a Baseboards project.
 *
 * @param projectName - Name of the project (used as package name)
 * @param cliVersion - Version of @weirdfingers/baseboards CLI
 * @returns Package.json content object
 */
export function createRootPackageJsonContent(
  projectName: string,
  cliVersion: string
): RootPackageJson {
  return {
    name: projectName,
    private: true,
    description: "Baseboards project - AI-powered creative toolkit",
    scripts: {
      dev: "baseboards dev",
      up: "baseboards up",
      "up:attach": "baseboards up --attach",
      down: "baseboards down",
      logs: "baseboards logs -f",
      status: "baseboards status",
      clean: "baseboards clean",
    },
    devDependencies: {
      "@weirdfingers/baseboards": `^${cliVersion}`,
    },
  };
}

/**
 * Generate and write the root package.json file for a Baseboards project.
 *
 * This creates a package.json at the project root with npm scripts that
 * wrap the Baseboards CLI commands, providing a more ergonomic developer
 * experience (e.g., `npm run dev` instead of `npx @weirdfingers/baseboards dev`).
 *
 * @param projectDir - Path to the project directory
 * @param projectName - Name of the project
 * @param cliVersion - Version of @weirdfingers/baseboards CLI
 */
export async function generateRootPackageJson(
  projectDir: string,
  projectName: string,
  cliVersion: string
): Promise<void> {
  const packageJsonPath = path.join(projectDir, "package.json");

  // Don't overwrite existing package.json
  if (await fs.pathExists(packageJsonPath)) {
    return;
  }

  const content = createRootPackageJsonContent(projectName, cliVersion);

  await fs.writeJson(packageJsonPath, content, { spaces: 2 });
}

/**
 * Install dependencies from the root package.json.
 *
 * This runs the package manager's install command at the project root,
 * which installs @weirdfingers/baseboards as a local devDependency.
 * This enables shorter commands like `npx baseboards up` and allows
 * npm scripts to reference `baseboards` directly.
 *
 * @param projectDir - Path to the project directory
 * @param packageManager - Package manager to use (npm, pnpm, yarn, bun)
 * @throws Error if installation fails
 */
export async function installRootDependencies(
  projectDir: string,
  packageManager: PackageManager
): Promise<void> {
  const packageJsonPath = path.join(projectDir, "package.json");

  // Check if package.json exists
  if (!(await fs.pathExists(packageJsonPath))) {
    console.log(
      chalk.yellow(
        "\n⚠️  No package.json found at project root, skipping dependency installation"
      )
    );
    return;
  }

  console.log(
    chalk.cyan(
      `\n📦 Installing project dependencies with ${packageManager}...`
    )
  );

  try {
    await execa(packageManager, ["install"], {
      cwd: projectDir,
      stdio: "inherit",
    });
    console.log(chalk.green("✅ Project dependencies installed successfully"));
    console.log(
      chalk.gray("   You can now use: ") +
        chalk.cyan("npm run up") +
        chalk.gray(", ") +
        chalk.cyan("npm run logs") +
        chalk.gray(", etc.")
    );
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(
      chalk.red(`\n❌ Failed to install dependencies: ${errorMessage}`)
    );

    console.log(chalk.yellow("\nTroubleshooting:"));
    console.log(
      chalk.gray("  • Check that package.json is valid:"),
      chalk.cyan(`${projectDir}/package.json`)
    );
    console.log(
      chalk.gray(`  • Ensure ${packageManager} is installed:`),
      chalk.cyan(`${packageManager} --version`)
    );
    console.log(
      chalk.gray("  • Try running the install manually:"),
      chalk.cyan(`cd ${projectDir} && ${packageManager} install`)
    );

    throw error;
  }
}
