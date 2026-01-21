/**
 * clean command - Clean up Docker resources
 */

import { execa } from 'execa';
import path from 'path';
import chalk from 'chalk';
import ora from 'ora';
import prompts from 'prompts';
import type { CleanOptions } from '../types.js';
import { isScaffolded } from '../utils.js';
import { getComposeBaseArgs } from '../utils/compose.js';

export async function clean(
  directory: string,
  options: CleanOptions
): Promise<void> {
  const dir = path.resolve(process.cwd(), directory);

  if (!isScaffolded(dir)) {
    console.error(chalk.red('\n❌ Error: Not a Baseboards project'));
    console.log(chalk.gray('   Run'), chalk.cyan('baseboards up'), chalk.gray('to scaffold a project first.'));
    process.exit(1);
  }

  if (options.hard) {
    console.log(chalk.yellow('\n⚠️  WARNING: This will delete:'));
    console.log(chalk.yellow('   • All containers'));
    console.log(chalk.yellow('   • All volumes (database data will be lost)'));
    console.log(chalk.yellow('   • All images'));

    const response = await prompts({
      type: 'confirm',
      name: 'confirmed',
      message: 'Are you sure?',
      initial: false,
    });

    if (!response.confirmed) {
      console.log(chalk.gray('\nCancelled'));
      return;
    }
  }

  const spinner = ora('Cleaning up...').start();

  try {
    // Stop containers
    await execa('docker', [...getComposeBaseArgs(dir), 'down', '--volumes', '--remove-orphans'], {
      cwd: dir,
    });

    if (options.hard) {
      // Remove images
      try {
        const { stdout } = await execa('docker', [...getComposeBaseArgs(dir), 'images', '-q'], {
          cwd: dir,
        });

        const imageIds = stdout.split('\n').filter(Boolean);
        if (imageIds.length > 0) {
          await execa('docker', ['rmi', ...imageIds]);
        }
      } catch (e) {
        // Images might not exist or already removed
      }
    }

    spinner.succeed('Cleanup complete');

    if (options.hard) {
      console.log(chalk.green('\n✨ All Docker resources removed'));
      console.log(chalk.gray('   Run'), chalk.cyan('baseboards up'), chalk.gray('to start fresh.'));
    } else {
      console.log(chalk.green('\n✨ Containers and volumes removed'));
    }
  } catch (error: any) {
    spinner.fail('Cleanup failed');
    throw error;
  }
}
