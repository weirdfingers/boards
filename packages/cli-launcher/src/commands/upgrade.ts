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

  console.log(chalk.blue(`\n📦 Upgrade: v${currentVersion} → v${targetVersion}\n`));

  // 5. Check compatibility
  const compatCheck = await checkCompatibility(currentVersion, targetVersion);

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

  // 6. Dry run mode - stop here
  if (options.dryRun) {
    console.log(chalk.blue('🔍 Dry run mode - no changes made\n'));
    return;
  }

  // 7. Prompt for confirmation (unless --force)
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

  // 8. Detect project mode
  const mode = await detectProjectMode(dir);

  // 9. Route to appropriate upgrade flow
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
