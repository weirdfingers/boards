/**
 * Upgrade flow for default mode projects
 *
 * Handles upgrading projects running in default mode (frontend in Docker).
 * This automates the entire upgrade process: stopping services, pulling new images,
 * updating configurations, rebuilding the frontend Docker image, and restarting services.
 */

import path from 'path';
import fs from 'fs-extra';
import chalk from 'chalk';
import { execa } from 'execa';
import ora from 'ora';
import { waitFor } from '../utils.js';

/**
 * Upgrade a default mode project (frontend in Docker).
 * This function:
 * 1. Stops all running services
 * 2. Pulls new backend Docker images
 * 3. Updates web/package.json with new @weirdfingers/boards version
 * 4. Rebuilds frontend Docker image
 * 5. Updates docker/.env with new BACKEND_VERSION
 * 6. Starts services (migrations run automatically)
 * 7. Waits for all services to be healthy
 */
export async function upgradeDefaultMode(
  projectDir: string,
  currentVersion: string,
  targetVersion: string
): Promise<void> {
  console.log(chalk.blue(`\n📦 Upgrading from v${currentVersion} to v${targetVersion}\n`));

  try {
    // 1. Stop services
    console.log(chalk.gray('⏸️  Stopping services...'));
    await execAsync('docker compose --env-file docker/.env down', { cwd: projectDir });

    // 2. Pull new backend images
    console.log(chalk.gray('⬇️  Pulling new backend images...'));
    await execAsync('docker compose --env-file docker/.env pull api worker', { cwd: projectDir });

    // 3. Update web/package.json
    console.log(chalk.gray('📝 Updating frontend dependencies...'));
    await updateWebPackageJson(projectDir, targetVersion);

    // 4. Rebuild frontend Docker image
    console.log(chalk.gray('🔨 Rebuilding frontend image (this may take a few minutes)...'));
    await execAsync('docker compose --env-file docker/.env build web', { cwd: projectDir });

    // 5. Update docker/.env with new version
    console.log(chalk.gray('⚙️  Updating configuration...'));
    await updateEnvVersion(projectDir, targetVersion);

    // 6. Start services
    console.log(chalk.gray('🚀 Starting services...'));
    await execAsync('docker compose --env-file docker/.env up -d', { cwd: projectDir });

    // 7. Wait for health checks
    console.log(chalk.gray('🏥 Waiting for services to be healthy...'));
    await waitForHealth(projectDir, ['db', 'cache', 'api', 'worker', 'web']);

    // Success!
    console.log(chalk.green(`\n✅ Successfully upgraded to v${targetVersion}!\n`));
    printUpgradeSuccess(projectDir, targetVersion);

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(chalk.red(`\n❌ Upgrade failed: ${errorMessage}\n`));
    console.log(chalk.yellow('To rollback:'));
    console.log(chalk.gray(`  1. Edit docker/.env and set BACKEND_VERSION=${currentVersion}`));
    console.log(chalk.gray('  2. Run: docker compose pull'));
    console.log(chalk.gray('  3. Run: docker compose build web'));
    console.log(chalk.gray('  4. Run: docker compose up -d\n'));
    throw error;
  }
}

/**
 * Update web/package.json with new @weirdfingers/boards version
 */
async function updateWebPackageJson(projectDir: string, version: string): Promise<void> {
  const packageJsonPath = path.join(projectDir, 'web', 'package.json');
  const packageJson = await fs.readJson(packageJsonPath);

  // Update @weirdfingers/boards version
  if (packageJson.dependencies && packageJson.dependencies['@weirdfingers/boards']) {
    packageJson.dependencies['@weirdfingers/boards'] = version;
  }

  await fs.writeJson(packageJsonPath, packageJson, { spaces: 2 });
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

/**
 * Print success message and next steps
 */
function printUpgradeSuccess(projectDir: string, version: string): void {
  console.log(chalk.gray('   Your Baseboards installation has been upgraded.'));
  console.log(chalk.gray('   All services are running and healthy.\n'));

  console.log(chalk.gray('Next steps:'));
  console.log(chalk.gray(`  • Check release notes: https://github.com/weirdfingers/boards/releases/tag/v${version}`));
  console.log(chalk.gray(`  • View logs: baseboards logs ${path.basename(projectDir)}`));
  console.log(chalk.gray(`  • Check status: baseboards status ${path.basename(projectDir)}\n`));
}

/**
 * Execute a command with execa
 */
async function execAsync(
  command: string,
  options?: { cwd?: string }
): Promise<{ stdout: string; stderr: string }> {
  const [cmd, ...args] = command.split(' ');
  return execa(cmd, args, options);
}
