/**
 * Upgrade flow for app-dev mode projects
 *
 * Handles upgrading projects running in app-dev mode (frontend running locally).
 * This involves updating backend Docker images and providing manual frontend upgrade instructions.
 */

import path from 'path';
import fs from 'fs-extra';
import chalk from 'chalk';
import { execa } from 'execa';
import ora from 'ora';
import { execAsync, waitFor, detectPackageManager } from '../utils.js';

/**
 * Upgrade an app-dev mode project (frontend running locally).
 * This function:
 * 1. Stops backend services (no web container)
 * 2. Pulls new backend Docker images
 * 3. Updates docker/.env with new BACKEND_VERSION
 * 4. Starts backend services (db, cache, api, worker only)
 * 5. Waits for backend services to be healthy
 * 6. Prints manual frontend upgrade instructions
 */
export async function upgradeAppDevMode(
  projectDir: string,
  currentVersion: string,
  targetVersion: string
): Promise<void> {
  console.log(chalk.blue(`\n📦 Upgrading backend from v${currentVersion} to v${targetVersion}\n`));

  try {
    // 1. Stop backend services
    console.log(chalk.gray('⏸️  Stopping backend services...'));
    await execAsync('docker compose --env-file docker/.env down', { cwd: projectDir });

    // 2. Pull new backend images (api and worker only)
    console.log(chalk.gray('⬇️  Pulling new backend images...'));
    await execAsync('docker compose --env-file docker/.env pull api worker', { cwd: projectDir });

    // 3. Update docker/.env with new BACKEND_VERSION
    console.log(chalk.gray('⚙️  Updating configuration...'));
    await updateEnvVersion(projectDir, targetVersion);

    // 4. Start backend services (no web)
    console.log(chalk.gray('🚀 Starting backend services...'));
    await execAsync('docker compose --env-file docker/.env up -d db cache api worker', { cwd: projectDir });

    // 5. Wait for backend health
    console.log(chalk.gray('🏥 Waiting for backend to be healthy...'));
    await waitForHealth(projectDir, ['db', 'cache', 'api', 'worker']);

    console.log(chalk.green(`\n✅ Backend upgraded to v${targetVersion}!\n`));

    // 6. Print manual frontend upgrade instructions
    await printAppDevUpgradeInstructions(projectDir, currentVersion, targetVersion);

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(chalk.red(`\n❌ Upgrade failed: ${errorMessage}\n`));
    console.log(chalk.yellow('To rollback:'));
    console.log(chalk.gray(`  1. Edit docker/.env and set BACKEND_VERSION=${currentVersion}`));
    console.log(chalk.gray('  2. Run: docker compose --env-file docker/.env pull'));
    console.log(chalk.gray('  3. Run: docker compose --env-file docker/.env up -d db cache api worker\n'));
    throw error;
  }
}

/**
 * Update docker/.env BACKEND_VERSION field
 */
async function updateEnvVersion(projectDir: string, version: string): Promise<void> {
  const envPath = path.join(projectDir, 'docker', '.env');
  let content = await fs.readFile(envPath, 'utf-8');

  // Replace BACKEND_VERSION line
  content = content.replace(
    /^BACKEND_VERSION=.*/m,
    `BACKEND_VERSION=${version}`
  );

  await fs.writeFile(envPath, content, 'utf-8');
}

/**
 * Print manual frontend upgrade instructions for app-dev mode
 */
async function printAppDevUpgradeInstructions(
  projectDir: string,
  oldVersion: string,
  newVersion: string
): Promise<void> {
  // Detect package manager from web/package-lock.json, pnpm-lock.yaml, etc.
  const webDir = path.join(projectDir, 'web');
  const packageManager = await detectPackageManager(webDir);

  const updateCommand = packageManager === 'npm'
    ? `npm install @weirdfingers/boards@${newVersion}`
    : packageManager === 'yarn'
    ? `yarn upgrade @weirdfingers/boards@${newVersion}`
    : packageManager === 'bun'
    ? `bun update @weirdfingers/boards@${newVersion}`
    : `pnpm update @weirdfingers/boards@${newVersion}`;

  console.log(chalk.yellow('⚠️  Frontend requires manual upgrade:\n'));
  console.log(chalk.gray('   1. Stop your dev server (Ctrl+C if running)\n'));
  console.log(chalk.gray('   2. Update the frontend package:\n'));
  console.log(chalk.cyan(`      cd ${path.basename(projectDir)}/web`));
  console.log(chalk.cyan(`      ${updateCommand}\n`));
  console.log(chalk.gray('   3. Check for breaking changes:\n'));
  console.log(chalk.gray(`      https://github.com/weirdfingers/boards/releases/tag/v${newVersion}\n`));
  console.log(chalk.gray('   4. Restart your dev server:\n'));
  console.log(chalk.cyan(`      ${packageManager} dev\n`));

  // Check if there are uncommitted changes
  try {
    const { stdout } = await execAsync('git status --porcelain', { cwd: webDir });
    if (stdout.trim()) {
      console.log(chalk.yellow('⚠️  You have uncommitted changes in web/'));
      console.log(chalk.gray('   Consider committing before updating dependencies.\n'));
    }
  } catch {
    // Not a git repo or git not available, skip warning
  }
}

/**
 * Wait for Docker Compose services to be healthy
 */
async function waitForHealth(projectDir: string, services: string[]): Promise<void> {
  const spinner = ora("Waiting for services to be healthy...").start();
  const maxWaitMs = 120_000; // 2 minutes

  type ComposePsEntry = {
    Service?: string;
    Health?: string;
    State?: string;
  };

  const checkHealth = async (): Promise<boolean> => {
    try {
      const { stdout } = await execa(
        "docker",
        ["compose", "--env-file", "docker/.env", "ps", "--format", "json"],
        {
          cwd: projectDir,
        }
      );

      const containers = stdout
        .split("\n")
        .filter(Boolean)
        .map((line) => JSON.parse(line) as ComposePsEntry);

      const allHealthy = services.every((service) => {
        const container = containers.find((c) => c.Service === service);
        return (
          container &&
          (container.Health === "healthy" || container.State === "running")
        );
      });

      return allHealthy;
    } catch {
      return false;
    }
  };

  const success = await waitFor(checkHealth, {
    timeoutMs: maxWaitMs,
    intervalMs: 2000,
    onProgress: (elapsed) => {
      const seconds = Math.floor(elapsed / 1000);
      spinner.text = `Waiting for services to be healthy... (${seconds}s)`;
    },
  });

  if (success) {
    spinner.succeed("All services healthy");
  } else {
    spinner.warn("Services taking longer than expected...");
    console.log(
      chalk.yellow(
        "\n⚠️  Health check timeout. Services may still be starting."
      )
    );
    console.log(
      chalk.gray("   Run"),
      chalk.cyan("baseboards logs"),
      chalk.gray("to check progress.")
    );
  }
}
