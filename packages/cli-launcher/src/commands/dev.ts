/**
 * dev command - Start the frontend development server
 *
 * This command is for app-dev mode projects where the frontend runs locally
 * instead of in Docker. It detects the package manager and runs the dev
 * server in the web/ subdirectory.
 */

import { execa } from 'execa';
import path from 'path';
import chalk from 'chalk';
import fs from 'fs-extra';
import { isScaffolded, detectPackageManager } from '../utils.js';
import { detectProjectMode } from '../utils/mode-detection.js';
import type { PackageManager } from '../utils.js';

/**
 * Get the dev command for the selected package manager.
 * @param pm Package manager (pnpm, npm, yarn, or bun)
 * @returns The command and arguments to start the dev server
 */
function getDevCommand(pm: PackageManager): { cmd: string; args: string[] } {
  switch (pm) {
    case 'pnpm':
      return { cmd: 'pnpm', args: ['dev'] };
    case 'yarn':
      return { cmd: 'yarn', args: ['dev'] };
    case 'bun':
      return { cmd: 'bun', args: ['dev'] };
    case 'npm':
    default:
      return { cmd: 'npm', args: ['run', 'dev'] };
  }
}

export async function dev(directory: string): Promise<void> {
  const dir = path.resolve(process.cwd(), directory);
  const webDir = path.join(dir, 'web');

  // Check if this is a Baseboards project
  if (!isScaffolded(dir)) {
    console.error(chalk.red('\n❌ Error: Not a Baseboards project'));
    console.log(
      chalk.gray('   Run'),
      chalk.cyan('baseboards up'),
      chalk.gray('to scaffold a project first.')
    );
    process.exit(1);
  }

  // Check if web directory exists
  if (!await fs.pathExists(webDir)) {
    console.error(chalk.red('\n❌ Error: No web/ directory found'));
    console.log(
      chalk.gray('   This project may not have a frontend component.')
    );
    process.exit(1);
  }

  // Detect project mode
  const mode = await detectProjectMode(dir);

  if (mode !== 'app-dev') {
    console.error(chalk.red('\n❌ Error: This project is running in default mode'));
    console.log(
      chalk.gray('\n   The frontend is running inside Docker.')
    );
    console.log(
      chalk.gray('   To use'),
      chalk.cyan('baseboards dev'),
      chalk.gray(', scaffold with'),
      chalk.cyan('--app-dev'),
      chalk.gray(':')
    );
    console.log(
      chalk.cyan('\n   baseboards up --app-dev')
    );
    console.log(
      chalk.gray('\n   Or access the running frontend at the URL shown by'),
      chalk.cyan('baseboards status')
    );
    process.exit(1);
  }

  // Check if node_modules exists in web directory
  const nodeModulesDir = path.join(webDir, 'node_modules');
  if (!await fs.pathExists(nodeModulesDir)) {
    console.error(chalk.yellow('\n⚠️  Dependencies not installed'));
    console.log(
      chalk.gray('   Run the following to install dependencies:')
    );

    const pm = await detectPackageManager(webDir);
    console.log(chalk.cyan(`\n   cd ${webDir} && ${pm} install\n`));
    process.exit(1);
  }

  // Detect package manager from web directory
  const packageManager = await detectPackageManager(webDir);
  const { cmd, args } = getDevCommand(packageManager);

  // Use port 3300 to match CORS configuration (same as Docker mode)
  const port = '3300';

  console.log(chalk.blue.bold('\n🚀 Starting frontend development server...\n'));
  console.log(
    chalk.gray('   Package manager:'),
    chalk.cyan(packageManager)
  );
  console.log(
    chalk.gray('   Directory:'),
    chalk.cyan(webDir)
  );
  console.log(
    chalk.gray('   Port:'),
    chalk.cyan(port)
  );
  console.log();

  try {
    // Run the dev server with inherited stdio so user sees output
    // Set PORT=3300 to match CORS configuration in api/.env
    await execa(cmd, args, {
      cwd: webDir,
      stdio: 'inherit',
      env: { ...process.env, PORT: port },
    });
  } catch (error: unknown) {
    // Check if it was a user interrupt (Ctrl+C)
    const exitError = error as { exitCode?: number; signal?: string };
    if (exitError.signal === 'SIGINT' || exitError.exitCode === 130) {
      console.log(chalk.gray('\n\n👋 Development server stopped.'));
      process.exit(0);
    }

    console.error(chalk.red('\n❌ Failed to start development server'));

    const err = error as { message?: string };
    if (err.message) {
      console.error(chalk.gray('   Error:'), err.message);
    }

    console.log(chalk.yellow('\nTroubleshooting:'));
    console.log(
      chalk.gray('  • Ensure dependencies are installed:'),
      chalk.cyan(`cd ${webDir} && ${packageManager} install`)
    );
    console.log(
      chalk.gray('  • Check package.json has a "dev" script')
    );
    console.log(
      chalk.gray('  • Try running manually:'),
      chalk.cyan(`cd ${webDir} && ${cmd} ${args.join(' ')}`)
    );

    process.exit(1);
  }
}
