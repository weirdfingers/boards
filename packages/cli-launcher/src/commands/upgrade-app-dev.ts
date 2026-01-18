/**
 * Upgrade flow for app-dev mode projects
 *
 * Handles upgrading projects running in app-dev mode (frontend running locally).
 * This involves updating Docker images and potentially updating frontend dependencies.
 *
 * NOTE: This is a placeholder for CLI-7.5.
 * Full implementation is tracked in CLI-7.7.
 */

import chalk from 'chalk';

export async function upgradeAppDevMode(
  projectDir: string,
  currentVersion: string,
  targetVersion: string
): Promise<void> {
  console.log(chalk.blue(`\n📦 Upgrading app-dev mode project...\n`));
  console.log(chalk.gray(`   Current: v${currentVersion}`));
  console.log(chalk.gray(`   Target:  v${targetVersion}`));
  console.log();

  // TODO: Implement app-dev mode upgrade logic (CLI-7.7)
  // 1. Update docker/.env VERSION field
  // 2. Pull new Docker images
  // 3. Update web/package.json dependencies
  // 4. Run npm/pnpm/yarn install in web directory

  console.log(chalk.yellow('⚠️  App-dev mode upgrade not yet implemented (CLI-7.7)'));
  console.log(chalk.gray('\nFor now, manually:'));
  console.log(chalk.gray('   1. Update VERSION in docker/.env'));
  console.log(chalk.cyan('   2. docker compose pull'));
  console.log(chalk.cyan('   3. Update @weirdfingers/boards in web/package.json'));
  console.log(chalk.cyan('   4. npm install in web/'));
  console.log();
}
