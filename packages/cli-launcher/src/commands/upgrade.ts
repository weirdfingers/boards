/**
 * upgrade command - Upgrade Baseboards to a specific or latest version
 *
 * Replaces the old 'update' command with a more robust upgrade workflow that:
 * - Validates the project directory
 * - Determines current and target versions
 * - Checks compatibility and displays warnings
 * - Detects project mode (default vs app-dev)
 * - Routes to appropriate upgrade flow
 */

import path from 'path';
import chalk from 'chalk';
import prompts from 'prompts';
import { isScaffolded, getCurrentVersion, execAsync } from '../utils.js';
import { detectProjectMode } from '../utils/mode-detection.js';
import { checkCompatibility } from '../utils/compatibility-checker.js';
import { upgradeDefaultMode } from './upgrade-default.js';
import { upgradeAppDevMode } from './upgrade-app-dev.js';
import type { UpgradeOptions } from '../types.js';

export async function upgrade(
  directory: string,
  options: UpgradeOptions
): Promise<void> {
  const dir = path.resolve(process.cwd(), directory);

  // 1. Validate project directory
  if (!isScaffolded(dir)) {
    console.error(chalk.red('\n❌ Error: Not a Baseboards project'));
    console.log(chalk.gray('   Run'), chalk.cyan('baseboards up'), chalk.gray('to scaffold a project first.'));
    process.exit(1);
  }

  // 2. Determine current version
  const currentVersion = await getCurrentVersion(dir);
  if (!currentVersion) {
    console.error(chalk.red('\n❌ Error: Could not determine current version'));
    console.log(chalk.gray('   Check docker/.env for VERSION field'));
    process.exit(1);
  }

  // 3. Determine target version
  const targetVersion = options.version || await getLatestVersion();

  // 4. Check if already at target version
  if (currentVersion === targetVersion) {
    console.log(chalk.green(`\n✅ Already at v${targetVersion}`));
    return;
  }

  // 5. Check compatibility
  const compatCheck = await checkCompatibility(currentVersion, targetVersion);

  // 6. Detect project mode (needed for upgrade plan)
  const mode = await detectProjectMode(dir);

  // 7. Display upgrade plan
  console.log(chalk.blue('📋 Upgrade Plan:\n'));
  console.log(chalk.gray(`   Current version: ${currentVersion}`));
  console.log(chalk.gray(`   Target version:  ${targetVersion}`));
  console.log(chalk.gray(`   Project mode:    ${mode}`));
  console.log('');

  // Display what would be upgraded
  if (mode === 'default') {
    console.log(chalk.gray('   Steps:'));
    console.log(chalk.gray('   1. Stop all services'));
    console.log(chalk.gray('   2. Pull new backend images'));
    console.log(chalk.gray('   3. Update web/package.json'));
    console.log(chalk.gray('   4. Rebuild frontend Docker image'));
    console.log(chalk.gray('   5. Update docker/.env'));
    console.log(chalk.gray('   6. Start services'));
    console.log(chalk.gray('   7. Wait for health checks'));
  } else {
    console.log(chalk.gray('   Steps:'));
    console.log(chalk.gray('   1. Stop backend services'));
    console.log(chalk.gray('   2. Pull new backend images'));
    console.log(chalk.gray('   3. Update docker/.env'));
    console.log(chalk.gray('   4. Start backend services'));
    console.log(chalk.gray('   5. Print manual frontend update instructions'));
  }
  console.log('');

  // Display warnings
  if (compatCheck.warnings.length > 0) {
    console.log(compatCheck.warnings.join('\n'));
    console.log('');
  }

  if (compatCheck.requiredActions.length > 0) {
    console.log(chalk.yellow('⚠️  Required manual actions:'));
    compatCheck.requiredActions.forEach((action) => {
      console.log(chalk.gray(`   • ${action}`));
    });
    console.log('');
  }

  // 8. Dry run mode - stop here
  if (options.dryRun) {
    console.log(chalk.blue('🔍 Dry run complete - no changes made\n'));
    return;
  }

  // 9. Force flag warning when skipping breaking change confirmation
  if (options.force && compatCheck.breaking) {
    console.log(chalk.yellow('⚠️  --force flag used: skipping confirmation despite breaking changes\n'));
  }

  // 10. Prompt for confirmation (unless --force)
  if (!options.force && compatCheck.breaking) {
    const { proceed } = await prompts({
      type: 'confirm',
      name: 'proceed',
      message: 'Continue with upgrade?',
      initial: false,
    });

    if (!proceed) {
      console.log(chalk.gray('\nUpgrade cancelled\n'));
      return;
    }
  }

  // 11. Route to appropriate upgrade flow
  if (mode === 'app-dev') {
    await upgradeAppDevMode(dir, currentVersion, targetVersion);
  } else {
    await upgradeDefaultMode(dir, currentVersion, targetVersion);
  }
}

/**
 * Get latest version from npm registry
 */
async function getLatestVersion(): Promise<string> {
  try {
    const result = await execAsync('npm view @weirdfingers/baseboards version');
    return result.stdout.trim();
  } catch (error) {
    throw new Error('Failed to fetch latest version from npm');
  }
}
