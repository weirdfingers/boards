/**
 * logs command - View service logs
 */

import { execa } from 'execa';
import path from 'path';
import chalk from 'chalk';
import type { LogsOptions } from '../types.js';
import { isScaffolded } from '../utils.js';

export async function logs(
  directory: string,
  services: string[],
  options: LogsOptions
): Promise<void> {
  const dir = path.resolve(process.cwd(), directory);

  if (!isScaffolded(dir)) {
    console.error(chalk.red('\n❌ Error: Not a Baseboards project'));
    console.log(chalk.gray('   Run'), chalk.cyan('baseboards up'), chalk.gray('to scaffold a project first.'));
    process.exit(1);
  }

  const args = ['compose', 'logs'];

  if (options.follow) {
    args.push('--follow');
  }

  if (options.since) {
    args.push('--since', options.since);
  }

  if (options.tail) {
    args.push('--tail', options.tail);
  }

  // Add specific services if provided
  if (services.length > 0) {
    args.push(...services);
  }

  try {
    await execa('docker', args, {
      cwd: dir,
      stdio: 'inherit',
    });
  } catch (error: any) {
    // Ctrl+C is expected, don't treat as error
    if (error.signal !== 'SIGINT') {
      throw error;
    }
  }
}
