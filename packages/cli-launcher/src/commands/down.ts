/**
 * down command - Stop Baseboards
 */

import { execa } from 'execa';
import path from 'path';
import chalk from 'chalk';
import ora from 'ora';
import type { DownOptions } from '../types.js';
import { isScaffolded } from '../utils.js';
import { getComposeBaseArgs } from '../utils/compose.js';

export async function down(directory: string, options: DownOptions): Promise<void> {
  const dir = path.resolve(process.cwd(), directory);

  if (!isScaffolded(dir)) {
    console.error(chalk.red('\n❌ Error: Not a Baseboards project'));
    console.log(chalk.gray('   Run'), chalk.cyan('baseboards up'), chalk.gray('to scaffold a project first.'));
    process.exit(1);
  }

  const spinner = ora('Stopping services...').start();

  const args = [...getComposeBaseArgs(dir), 'down'];
  if (options.volumes) {
    args.push('--volumes');
  }

  try {
    await execa('docker', args, {
      cwd: dir,
    });

    spinner.succeed('Services stopped');

    if (options.volumes) {
      console.log(chalk.yellow('⚠️  Volumes removed (database data deleted)'));
    }
  } catch (error: any) {
    spinner.fail('Failed to stop services');
    throw error;
  }
}
