/**
 * update command - Update Baseboards to latest version
 */

import path from 'path';
import chalk from 'chalk';
import type { UpdateOptions } from '../types.js';
import { isScaffolded } from '../utils.js';

export async function update(
  directory: string,
  options: UpdateOptions
): Promise<void> {
  const dir = path.resolve(process.cwd(), directory);

  if (!isScaffolded(dir)) {
    console.error(chalk.red('\n❌ Error: Not a Baseboards project'));
    console.log(chalk.gray('   Run'), chalk.cyan('baseboards up'), chalk.gray('to scaffold a project first.'));
    process.exit(1);
  }

  console.log(chalk.blue.bold('\n🔄 Update Command\n'));
  console.log(chalk.yellow('⚠️  This feature is coming soon!'));
  console.log(chalk.gray('\nFor now, to update:'));
  console.log(chalk.gray('1. Update the CLI:'), chalk.cyan('npm install -g @weirdfingers/baseboards@latest'));
  console.log(chalk.gray('2. Pull new images:'), chalk.cyan('docker compose pull'));
  console.log(chalk.gray('3. Restart:'), chalk.cyan('baseboards down && baseboards up'));
  console.log();

  // TODO: Implement update logic:
  // 1. Check for new version on npm
  // 2. Scan for modified source files (git diff or timestamp check)
  // 3. If no modifications:
  //    - Copy new templates (preserving config)
  //    - Pull new Docker images
  //    - Update package.json versions
  // 4. If modifications detected:
  //    - Warn user
  //    - Offer git-based merge if repo detected
  //    - Create backup otherwise
  // 5. Preserve:
  //    - All .env files
  //    - config/*.yaml files
  //    - data/storage/ directory
}
