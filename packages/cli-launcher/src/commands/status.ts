/**
 * status command - Show service status
 */

import { execa } from 'execa';
import path from 'path';
import chalk from 'chalk';
import { isScaffolded } from '../utils.js';

export async function status(directory: string): Promise<void> {
  const dir = path.resolve(process.cwd(), directory);

  if (!isScaffolded(dir)) {
    console.error(chalk.red('\n❌ Error: Not a Baseboards project'));
    console.log(chalk.gray('   Run'), chalk.cyan('baseboards up'), chalk.gray('to scaffold a project first.'));
    process.exit(1);
  }

  console.log(chalk.blue.bold('\n📊 Service Status\n'));

  try {
    await execa('docker', ['compose', 'ps'], {
      cwd: dir,
      stdio: 'inherit',
    });
  } catch (error: any) {
    console.error(chalk.red('\n❌ Failed to get status'));
    throw error;
  }
}
